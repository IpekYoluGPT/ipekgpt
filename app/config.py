"""
Configuration settings for İpekGPT Web Application
Loads sensitive data from environment variables (.env file)
"""
import os
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application configuration settings"""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = Path(__file__).resolve().parent
    
    # Database
    DATABASE_URL = f"sqlite:///{BASE_DIR}/ipekgpt.db"
    
    # ==========================================================================
    # Gemini API Configuration (loaded from .env)
    # ==========================================================================
    
    # API keys loaded from environment variable (comma-separated if multiple)
    @property
    def GEMINI_API_KEYS(self):
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        if not keys_str:
            return []
        return [key.strip() for key in keys_str.split(",") if key.strip()]
    
    # Model loaded from environment variable
    @property
    def GEMINI_MODEL(self):
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
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
    
    DAILY_REQUEST_LIMIT = 300  # Total AI requests per day for the server
    MAX_MESSAGE_LENGTH = 300   # Maximum characters per user message
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
