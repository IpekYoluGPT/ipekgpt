"""
Gemini API Manager - Handles API key rotation and rate limiting
"""
import asyncio
import time
from datetime import date
from typing import Optional, Dict, Any
import google.generativeai as genai

from .config import settings


class GeminiAPIManager:
    """
    Manages Gemini API calls with:
    - API key rotation
    - Daily failed key reset
    - Rate limiting between requests
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if GeminiAPIManager._initialized:
            return
        
        self.api_keys = settings.GEMINI_API_KEYS.copy()
        self.current_key_index = 0
        self.failed_keys: Dict[str, date] = {}  # key -> date it failed
        self.last_request_time = 0
        self.request_delay = settings.REQUEST_DELAY_MS / 1000  # Convert to seconds
        
        # Clean up any failed keys from previous days on init
        self._reset_daily_failed_keys()
        
        GeminiAPIManager._initialized = True
        print(f"✅ Gemini API Manager initialized with {len(self.api_keys)} key(s)")
    
    def _reset_daily_failed_keys(self):
        """Reset failed keys that were marked on previous days"""
        today = date.today()
        keys_to_reset = [
            key for key, failed_date in self.failed_keys.items()
            if failed_date < today
        ]
        for key in keys_to_reset:
            del self.failed_keys[key]
            print(f"🔄 API key reset (new day): ...{key[-8:]}")
    
    def _get_available_key(self) -> Optional[str]:
        """Get the next available API key, skipping failed ones"""
        if not self.api_keys:
            return None
        
        # Reset daily failed keys
        self._reset_daily_failed_keys()
        
        # Try to find an available key
        attempts = 0
        while attempts < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            
            if key not in self.failed_keys:
                return key
            
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            attempts += 1
        
        # All keys failed
        return None
    
    def _mark_key_failed(self, key: str):
        """Mark an API key as failed for today"""
        self.failed_keys[key] = date.today()
        print(f"⚠️ API key marked as failed (until tomorrow): ...{key[-8:]}")
        
        # Move to next key
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
    
    def _rotate_key(self):
        """Rotate to the next API key"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            wait_time = self.request_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def generate_response(self, prompt: str) -> Dict[str, Any]:
        """
        Generate a response using Gemini API with key rotation and error handling
        
        Returns:
            Dict with 'text' (response) or 'error' (error message)
        """
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Get available key
        api_key = self._get_available_key()
        
        if not api_key:
            return {
                'error': 'Tüm API anahtarları geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.',
                'text': None
            }
        
        try:
            # Configure Gemini with current key
            genai.configure(api_key=api_key)
            
            # Create model instance
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            # Generate response
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )
            
            # Rotate key for next request (distribute load)
            self._rotate_key()
            
            return {
                'text': response.text,
                'error': None
            }
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit or quota errors
            if any(err in error_str for err in ['429', 'too many requests', 'quota', 'resource exhausted']):
                self._mark_key_failed(api_key)
                
                # Try again with next key
                return await self.generate_response(prompt)
            
            # Other API errors
            print(f"❌ Gemini API error: {e}")
            return {
                'error': f'API hatası: {str(e)[:100]}',
                'text': None
            }
    
    def get_status(self) -> Dict:
        """Get current API manager status"""
        return {
            'total_keys': len(self.api_keys),
            'available_keys': len(self.api_keys) - len(self.failed_keys),
            'failed_keys_count': len(self.failed_keys),
            'current_key_index': self.current_key_index
        }


# Global instance
gemini_manager = GeminiAPIManager()
