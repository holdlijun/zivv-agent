import os
import json
import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import AgentState
from app.core.config import config


# 初始化 LLM 客户端
def get_slm_llm():
    return ChatOpenAI(
        model=config.SLM_MODEL,
        openai_api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        model_kwargs={"response_format": {"type": "json_object"}},
        timeout=10,
        openai_proxy=config.HTTPS_PROXY or config.HTTP_PROXY,
    )

def get_deep_dive_llm():
    return ChatOpenAI(
        model=config.LLM_MODEL,
        openai_api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=30,
        openai_proxy=config.HTTPS_PROXY or config.HTTP_PROXY,
    )


def rule_filter_node(state: AgentState):
    """Layer 1: 规则清洗节点"""
    print(f"[*] [L1] 正在处理: {state['symbol']} ({state['contract']})")

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


def slm_tagger_node(state: AgentState):
    """Layer 2: SLM 快筛节点 (LangChain 版)"""
    print(f"[*] [L2] 正在分析标签: {state['symbol']}")

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
        data = json.loads(response.content)
        
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


def deep_dive_node(state: AgentState):
    """Layer 3: LLM 深度研报节点 (Zivv Agent 侦探版)"""
    print(f"[*] [L3] 正在生成深度研报 (侦探视角): {state['symbol']}")

    if not config.LLM_API_KEY:
        return {**state, "report": "Missing API Key", "status": "error", "error_msg": "Missing API Key"}

    try:
        token_info = state.get("data", {})
        
        # 1. 组装上下文数据 (Assembling Context)
        market_data = f"Symbol ${state['symbol']}, Liquidity: ${token_info.get('liquidity', '0')}, MC: ${token_info.get('market_cap', '0')}"
        security_data = f"Honeypot: {'Yes' if token_info.get('honeypot') else 'No'}, Buy Tax: {token_info.get('buy_tax', '0')}%, Sell Tax: {token_info.get('sell_tax', '0')}%"
        search_data = "No recent social signals found in local context. (Search capability pending)"
        dev_data = f"Deployer: {state['contract']} (History lookup pending)"

        assembled_context = f"""
[MARKET]: {market_data}
[SECURITY]: {security_data}
[SEARCH]: {search_data}
[DEV]: {dev_data}
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
2. **Security Audit:** Look at the [SECURITY] and [DEV] data. Even if GoPlus says safe, if the Dev has a history of Rugs, mark it as "Dangerous".
3. **Verdict:** Give a final recommendation: "Ape in" (High conviction), "Degen Play" (Small bag), or "Stay Away".

Output format (Markdown):
## 🕵️ Zivv Analysis: ${state['symbol']}
**🎯 Narrative:** [Your analysis here]
**🛡️ Risk Check:** [Highlight Dev history and tax risks]
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
