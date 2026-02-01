import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    # Unified LLM Config
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    # Model Config
    SLM_MODEL = os.getenv("SLM_MODEL", "deepseek/deepseek-v3.2")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Proxy Config
    HTTP_PROXY = os.getenv("HTTP_PROXY")
    HTTPS_PROXY = os.getenv("HTTPS_PROXY")

    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
    MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "2000"))
    MAX_TAX = float(os.getenv("MAX_TAX", "0.20"))
    REQUIRE_NOT_HONEYPOT = os.getenv("REQUIRE_NOT_HONEYPOT", "true").lower() in ("1", "true", "yes")

config = Config()
