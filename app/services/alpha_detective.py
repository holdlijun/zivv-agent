import os
import requests
import json
from typing import List, Dict, Optional
from app.core.config import config

class AlphaDetective:
    def __init__(self):
        self.helius_api_key = os.getenv("HELIUS_API_KEY", "")
        self.birdeye_api_key = os.getenv("BIRDEYE_API_KEY", "")
        self.helius_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        self.birdeye_base_url = "https://public-api.birdeye.so"

    def get_top_holders(self, mint_address: str, limit: int = 20) -> List[Dict]:
        """通过 Helius 获取前 N 名持仓者"""
        if not self.helius_api_key:
            print("[!] Missing HELIUS_API_KEY")
            return []

        payload = {
            "jsonrpc": "2.0",
            "id": "get-holders",
            "method": "getTokenAccounts",
            "params": {
                "mint": mint_address,
                "page": 1,
                "limit": 100 # Helius 最小分页通常是 100
            }
        }
        
        try:
            response = requests.post(self.helius_rpc_url, json=payload, timeout=10)
            data = response.json()
            if "result" in data and "token_accounts" in data["result"]:
                accounts = data["result"]["token_accounts"]
                # 排序并取前 N 名 (Helius 结果可能未严格按金额排序)
                sorted_accounts = sorted(accounts, key=lambda x: float(x.get("amount", 0)), reverse=True)
                return sorted_accounts[:limit]
            else:
                print(f"[!] Helius Error: {data}")
        except Exception as e:
            print(f"[!] Helius Request Exception: {e}")
        
        return []

    def get_wallet_pnl(self, wallet_address: str) -> Optional[Dict]:
        """通过 Birdeye 获取钱包的整体盈利情况"""
        if not self.birdeye_api_key:
            return None

        url = f"{self.birdeye_base_url}/v1/wallet/pnl?address={wallet_address}"
        headers = {"X-API-KEY": self.birdeye_api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data")
        except Exception as e:
            print(f"[!] Birdeye Request Error for {wallet_address}: {e}")
            
        return None

    def analyze_token(self, mint_address: str) -> Dict:
        """综合分析代币 Alpha 数据"""
        print(f"[*] Analyzing Alpha for {mint_address}...")
        holders = self.get_top_holders(mint_address)
        
        if not holders:
            return {"error": "No holders found or API error"}

        smart_money_count = 0
        total_pnl = 0
        real_holders = 0
        
        # 分析前 10 名持仓者
        for holder in holders[:10]:
            wallet = holder.get("owner")
            # 简单判断是否是合约地址 (通常持仓极大的可能是池子，但这里简单处理)
            pnl_data = self.get_wallet_pnl(wallet)
            if pnl_data:
                real_holders += 1
                roi = pnl_data.get("realized_pnl_percentage", 0)
                if roi > 50: # 简单定义：盈利超过 50% 的算聪明钱
                    smart_money_count += 1
                total_pnl += pnl_data.get("realized_pnl_usd", 0)

        # 计算集中度
        # 注意：这里需要知道总供应量来算百分比，简化版先只记原始数据
        
        return {
            "smart_money_count": smart_money_count,
            "avg_top_pnl": total_pnl / real_holders if real_holders > 0 else 0,
            "holder_count_analyzed": len(holders),
            "is_alpha": smart_money_count >= 2 # 超过 2 个聪明钱在里面就算 Alpha
        }

alpha_detective = AlphaDetective()
