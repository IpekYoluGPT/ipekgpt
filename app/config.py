"""
Configuration settings for İpekGPT Web Application
"""
import os
from pathlib import Path


class Settings:
    """Application configuration settings"""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = Path(__file__).resolve().parent
    
    # Database
    DATABASE_URL = f"sqlite:///{BASE_DIR}/ipekgpt.db"
    
    # reCAPTCHA Configuration
    # Get your keys from: https://www.google.com/recaptcha/admin
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
    RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
    
    # Rate Limiting
    DAILY_REQUEST_LIMIT = 100  # Total AI requests per day for the server
    USER_TOKEN_LIMIT = 1024   # Max tokens in user context window
    
    # Vector Database
    VECTOR_DB_PATH = str(BASE_DIR / "chroma_db")
    COLLECTION_NAME = "org_knowledge_turkish"
    
    # Data Paths
    OLD_DATA_PATH = str(BASE_DIR / "data")
    NEW_DATA_PATH = str(BASE_DIR / "IPEKYOLU_RAG_VERISETI")
    
    # Embedding Model
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # LLM Configuration (Turkish Gemma)
    GEMMA_REPO_ID = "ytu-ce-cosmos/Turkish-Gemma-9b-T1-GGUF"
    GEMMA_FILENAME = "*Q4_K.gguf"
    
    # Gemma inference parameters
    GEMMA_PARAMS = {
        "n_gpu_layers": -1,  # Use all GPU layers
        "n_threads": 4,
        "n_ctx": 8192,
        "n_predict": 2048,
        "top_k": 40,
        "top_p": 0.90,
        "temp": 0.1,
        "repeat_penalty": 1.1,
    }
    
    # Retrieval settings
    TOP_K_RESULTS = 10
    
    # Server settings
    HOST = "127.0.0.1"
    PORT = 8000
    DEBUG = True


settings = Settings()
