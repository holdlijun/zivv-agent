import os
import json
import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import AgentState
from app.core.config import config
from app.services.alpha_detective import alpha_detective


# 初始化 LLM 客户端
def get_slm_llm():
    return ChatOpenAI(
        model=config.SLM_MODEL,
        openai_api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        # model_kwargs={"response_format": {"type": "json_object"}}, # Disable JSON mode for compatibility
        timeout=10,
    )

def get_deep_dive_llm():
    return ChatOpenAI(
        model=config.LLM_MODEL,
        openai_api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=30,
    )


def rule_filter_node(state: AgentState):
    """Layer 1: 规则清洗节点"""
    print(f"[*] [L1][Job:{state.get('job_id')}] 正在处理: {state['symbol']} ({state['contract']})")

    liq = float(state["data"].get("liquidity") or 0)
    if liq < config.MIN_LIQUIDITY:
        print(f"[-] [L1] 流动性过低({liq}), 已过滤")
        return {**state, "status": "filtered", "report": "Liquidity too low"}

    if config.REQUIRE_NOT_HONEYPOT:
        honeypot = state["data"].get("honeypot")
        if honeypot is True:
            print("[-] [L1] Honeypot 检测为真, 已过滤")
            return {**state, "status": "filtered", "report": "Honeypot detected"}

    buy_tax = state["data"].get("buy_tax")
    sell_tax = state["data"].get("sell_tax")
    try:
        if buy_tax is not None and float(buy_tax) > config.MAX_TAX:
            print(f"[-] [L1] Buy tax 过高({buy_tax}), 已过滤")
            return {**state, "status": "filtered", "report": "Buy tax too high"}
        if sell_tax is not None and float(sell_tax) > config.MAX_TAX:
            print(f"[-] [L1] Sell tax 过高({sell_tax}), 已过滤")
            return {**state, "status": "filtered", "report": "Sell tax too high"}
    except ValueError as e:
        return {**state, "status": "error", "error_msg": f"tax parse error: {e}"}

    return {**state, "status": "passed"}


# 辅助函数：清洗 LLM 返回的 JSON 字符串
def clean_json_output(content: str) -> dict:
    """剥离 markdown 标签并解析 JSON"""
    content = content.strip()
    if content.startswith("```"):
        # 移除 ```json 或 ``` 头部
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return json.loads(content)


def slm_tagger_node(state: AgentState):
    """Layer 2: SLM 快筛节点 (LangChain 版)"""
    print(f"[*] [L2][Job:{state.get('job_id')}] 正在分析标签: {state['symbol']}")

    if not config.LLM_API_KEY:
        print("[!] [L2] Missing LLM_API_KEY")
        return {**state, "tags": ["Meme"], "vibe_score": 50, "status": "passed"}

    try:
        token_info = state.get("data", {})
        input_data = {
            "symbol": state['symbol'],
            "name": state['name'],
            "pair_created_at": str(token_info.get('pair_created_at', 'Unknown')),
            "liquidity_usd": token_info.get('liquidity', '0'),
            "description": token_info.get('description', 'N/A'),
            "chain": token_info.get('chain', 'Unknown')
        }

        system_prompt = """Role: You are a Web3 Meme Coin Classifier. Your job is to extract narrative tags from basic token info.
Constraints:
1. Output MUST be valid JSON only. No markdown, no conversation.
2. Speed is key. Keep analysis shallow but accurate based on the name/bio.
3. If the bio mentions "Fan token" or "Not affiliated", tag it as "Community/Imitation"."""

        user_prompt = f"""Analyze the following Token Data:
{json.dumps(input_data, indent=2)}

Task:
1. Identify the "Narrative" (e.g., AI, Elon Musk, Dog, Cat, Frog, Politics, Trump).
2. Judge the "Vibe" (e.g., Official-looking, Degen, Low-effort).
3. Give a "Scam_Probability" (Low/Medium/High) based on the name (e.g. if it copies a famous coin name like 'PEPE2', it's 'Derivative').

Return JSON format:
{{
  "tags": ["String", "String"], 
  "vibe_score": 0-100, 
  "risk_level": "Low" | "Medium" | "High",
  "short_comment": "Max 10 words summary"
}}"""

        llm = get_slm_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        data = clean_json_output(response.content)
        
        return {
            **state,
            "tags": data.get("tags", []),
            "vibe_score": data.get("vibe_score", 50),
            "risk_level": data.get("risk_level", "Medium"),
            "short_comment": data.get("short_comment", ""),
            "status": "passed",
        }
    except Exception as e:
        print(f"[!] [L2] 报错: {e}")
        return {**state, "tags": ["Error"], "vibe_score": 0, "status": "error", "error_msg": str(e)}


def alpha_detective_node(state: AgentState):
    """Layer 2.5: 链上 Alpha 探测节点"""
    print(f"[*] [L2.5][Job:{state.get('job_id')}] 正在扫描链上 Alpha: {state['symbol']} ({state['contract']})")
    
    try:
        # 只针对 Solana 链进行 Alpha 分析 (目前 API 主要支持 SOL)
        if state.get("data", {}).get("chain") == "solana":
            alpha_res = alpha_detective.analyze_token(state["contract"])
            return {**state, "alpha_data": alpha_res}
        else:
            return {**state, "alpha_data": {"note": "Chain not supported for Alpha scan"}}
    except Exception as e:
        print(f"[!] [L2.5] Alpha scan failed: {e}")
        return {**state, "alpha_data": {"error": str(e)}}


def deep_dive_node(state: AgentState):
    """Layer 3: LLM 深度研报节点 (Zivv Agent 侦探版)"""
    print(f"[*] [L3][Job:{state.get('job_id')}] 正在生成深度研报 (侦探视角): {state['symbol']}")

    if not config.LLM_API_KEY:
        return {**state, "report": "Missing API Key", "status": "error", "error_msg": "Missing API Key"}

    try:
        token_info = state.get("data", {})
        
        # 1. 组装上下文数据 (Assembling Context)
        market_data = f"Symbol ${state['symbol']}, Liquidity: ${token_info.get('liquidity', '0')}, MC: ${token_info.get('market_cap', '0')}"
        security_data = f"Honeypot: {'Yes' if token_info.get('honeypot') else 'No'}, Buy Tax: {token_info.get('buy_tax', '0')}%, Sell Tax: {token_info.get('sell_tax', '0')}%"
        search_data = "No recent social signals found in local context. (Search capability pending)"
        
        # 注入 Alpha 数据
        alpha_info = state.get("alpha_data", {})
        alpha_context = ""
        if alpha_info and "smart_money_count" in alpha_info:
            alpha_context = f"""
[ON-CHAIN ALPHA]:
- Smart Money Count: {alpha_info.get('smart_money_count', 0)}
- Top Holders Avg PnL: ${alpha_info.get('avg_top_pnl', 0):.2f}
- Alpha Signal: {'DETECTED' if alpha_info.get('is_alpha') else 'Weak'}
"""

        assembled_context = f"""
[MARKET]: {market_data}
[SECURITY]: {security_data}
{alpha_context}
[SEARCH]: {search_data}
[DESCRIPTION]: {token_info.get('description', 'N/A')}
"""

        system_prompt = """Role: You are 'Zivv Agent', a senior DeFi analyst and on-chain detective. 
Tone: Professional, sharp, slightly skeptical (Degen style), but objective.
Goal: Synthesize multiple data sources to determine if a token is a "Gem" (Buy) or a "Trap" (Avoid)."""

        user_prompt = f"""Analyze the following Meme Coin based on the provided Context.

Context Data:
{assembled_context}

Instructions:
1. **Narrative Check:** detailedly explain WHY this coin is pumping. Is it related to a real-world event? Or is it just bot manipulation?
2. **Security Audit:** Look at the [SECURITY] data. Even if GoPlus says safe, verify if there are any suspicious patterns in the liquidity or tax.
3. **Verdict:** Give a final recommendation: "Ape in" (High conviction), "Degen Play" (Small bag), or "Stay Away".

Output format (Markdown):
## 🕵️ Zivv Analysis: ${state['symbol']}
**🎯 Narrative:** [Your analysis here]
**🛡️ Risk Check:** [Highlight security and tax risks]
**💡 Verdict:** [Final conclusion]

Please write the report in Chinese, but keep the headers and token symbols in English for professional look."""

        llm = get_deep_dive_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return {**state, "report": response.content, "status": "passed"}
    except Exception as e:
        print(f"[!] [L3] 报错: {e}")
        return {**state, "report": f"Failed: {e}", "status": "error", "error_msg": str(e)}
