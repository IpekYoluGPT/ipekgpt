"""
Configuration settings for İpekGPT Web Application
"""
import os
from pathlib import Path
from datetime import date


class Settings:
    """Application configuration settings"""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = Path(__file__).resolve().parent
    
    # Database
    DATABASE_URL = f"sqlite:///{BASE_DIR}/ipekgpt.db"
    
    # ==========================================================================
    # Gemini API Configuration
    # ==========================================================================
    
    # ADD YOUR API KEYS HERE - Get them from: https://aistudio.google.com/app/apikey
    GEMINI_API_KEYS = [
        # "your-api-key-1",
        # "your-api-key-2",
        # "your-api-key-3",
    ]
    
    # Model to use
    GEMINI_MODEL = "gemini-2.0-flash"
    
    # Delay between API requests in milliseconds (to prevent rate limiting)
    REQUEST_DELAY_MS = 500
    
    # ==========================================================================
    # reCAPTCHA Configuration (Optional)
    # ==========================================================================
    
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
    RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
    
    # ==========================================================================
    # Rate Limiting & Limits
    # ==========================================================================
    
    DAILY_REQUEST_LIMIT = 100  # Total AI requests per day for the server
    MAX_MESSAGE_LENGTH = 400   # Maximum characters per user message
    USER_TOKEN_LIMIT = 1024    # Max tokens in user context window
    
    # ==========================================================================
    # Vector Database (RAG - Unchanged)
    # ==========================================================================
    
    VECTOR_DB_PATH = str(BASE_DIR / "chroma_db")
    COLLECTION_NAME = "org_knowledge_turkish"
    
    # Data Paths
    OLD_DATA_PATH = str(BASE_DIR / "data")
    NEW_DATA_PATH = str(BASE_DIR / "IPEKYOLU_RAG_VERISETI")
    
    # Embedding Model
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Retrieval settings
    TOP_K_RESULTS = 10
    
    # ==========================================================================
    # Server & CORS Settings
    # ==========================================================================
    
    HOST = "127.0.0.1"
    PORT = 8000
    DEBUG = False  # Set to False for production
    
    # CORS - Add your production domains here
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        # Add your production domain(s) here:
        # "https://yourdomain.com",
    ]


settings = Settings()
