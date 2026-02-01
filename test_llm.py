import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

def test_llm(model_name, use_json=False):
    print(f"\n--- Testing Model: {model_name} (JSON Mode: {use_json}) ---")
    
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    
    kwargs = {}
    if use_json:
        kwargs["response_format"] = {"type": "json_object"}
    
    try:
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            base_url=base_url,
            model_kwargs=kwargs,
            timeout=10
        )
        
        system_msg = "You are a helpful assistant."
        if use_json:
            system_msg += " Output must be in JSON format."
            
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content="Hello, please respond with {'status': 'ok'}")
        ]
        
        response = llm.invoke(messages)
        print(f"Success! Response: {response.content}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    current_model = os.getenv("LLM_MODEL")
    
    # Test 1: Current setting
    test_llm(current_model, use_json=True)
    
    # Test 2: Current setting without JSON mode
    test_llm(current_model, use_json=False)
    
    # Test 3: Potential alternative model names
    alternatives = [
        "deepseek-v3",
        "deepseek-chat",
        "deepseek-reasoner",
        "aiberm/deepseek/deepseek-v3.2"
    ]
    
    for alt in alternatives:
        test_llm(alt, use_json=False)
