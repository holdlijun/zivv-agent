import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_llm_connection():
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("SLM_MODEL", "gpt-3.5-turbo")

    print(f"[*] Testing connection to: {base_url}")
    print(f"[*] Using model: {model}")
    
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zivv.ai", # Optional for OpenRouter
        "X-Title": "Zivv Agent"           # Optional for OpenRouter
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[+] Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"[+] Success! Response: {response.json()['choices'][0]['message']['content']}")
        else:
            print(f"[!] Error: {response.text}")
    except Exception as e:
        print(f"[X] Connection Failed: {e}")

if __name__ == "__main__":
    test_llm_connection()
