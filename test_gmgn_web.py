import requests
import json
import time

def test_gmgn_api(chain, contract, cookie=None):
    print(f"[*] Testing GMGN Web API for {chain}:{contract}")
    
    # 尝试不同的可能端点
    urls = [
        f"https://gmgn.ai/api/v1/token_stat/{chain}/{contract}",
        f"https://gmgn.ai/api/v1/token/details/{chain}/{contract}",
        f"https://gmgn.ai/api/v1/token/security/{chain}/{contract}"
    ]
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": "https://gmgn.ai/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    if cookie:
        headers["cookie"] = cookie
        print("[*] Using provided Cookie for authentication.")

    for url in urls:
        print(f"[*] Requesting: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"[*] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[+] Success for {url}!")
                print(f"[+] Sample Keys: {list(data.get('data', {}).keys())[:10]}")
                return True
            else:
                print(f"[-] Failed for {url}: {response.status_code}")
        except Exception as e:
            print(f"[!] Error requesting {url}: {e}")
    
    return False

if __name__ == "__main__":
    # 这是一个实际存在的、活跃的 Solana 代币合约 (示例: Trump)
    test_contract = "6p6W7rqZ9szEuvp9u5p9pGpKfW6h8DpvvK" 
    
    # 如果用户能提供 Cookie，填在这里进行测试
    user_cookie = "" 
    
    test_gmgn_api("sol", test_contract, cookie=user_cookie)
