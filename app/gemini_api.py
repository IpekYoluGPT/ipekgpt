"""
Gemini API Manager - Handles API key rotation and rate limiting
Dynamically reads API keys from config on each request
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
    - Dynamic API key loading from config
    - API key rotation
    - Daily failed key reset
    - Rate limiting between requests
    """
    
    def __init__(self):
        self.current_key_index = 0
        self.failed_keys: Dict[str, date] = {}  # key -> date it failed
        self.last_request_time = 0
        
        print(f"[OK] Gemini API Manager initialized")
    
    @property
    def api_keys(self):
        """Dynamically get API keys from settings (allows hot reload)"""
        return settings.GEMINI_API_KEYS.copy()
    
    @property
    def request_delay(self):
        """Dynamically get request delay from settings"""
        return settings.REQUEST_DELAY_MS / 1000
    
    def _reset_daily_failed_keys(self):
        """Reset failed keys that were marked on previous days"""
        today = date.today()
        keys_to_reset = [
            key for key, failed_date in self.failed_keys.items()
            if failed_date < today
        ]
        for key in keys_to_reset:
            del self.failed_keys[key]
            print(f"[RESET] API key reset (new day): ...{key[-8:]}")
    
    def _get_available_key(self) -> Optional[str]:
        """Get the next available API key, skipping failed ones"""
        current_keys = self.api_keys  # Get fresh keys from config
        
        if not current_keys:
            print("[ERROR] No API keys configured in settings.GEMINI_API_KEYS")
            return None
        
        # Reset daily failed keys
        self._reset_daily_failed_keys()
        
        # Also remove failed keys that are no longer in config
        self.failed_keys = {k: v for k, v in self.failed_keys.items() if k in current_keys}
        
        # Ensure current_key_index is within bounds
        if self.current_key_index >= len(current_keys):
            self.current_key_index = 0
        
        # Try to find an available key
        attempts = 0
        while attempts < len(current_keys):
            key = current_keys[self.current_key_index]
            
            if key not in self.failed_keys:
                return key
            
            # Move to next key
            self.current_key_index = (self.current_key_index + 1) % len(current_keys)
            attempts += 1
        
        # All keys failed
        return None
    
    def _mark_key_failed(self, key: str):
        """Mark an API key as failed for today"""
        self.failed_keys[key] = date.today()
        print(f"[WARN] API key marked as failed (until tomorrow): ...{key[-8:]}")
        
        # Move to next key
        current_keys = self.api_keys
        if current_keys:
            self.current_key_index = (self.current_key_index + 1) % len(current_keys)
    
    def _rotate_key(self):
        """Rotate to the next API key"""
        current_keys = self.api_keys
        if len(current_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(current_keys)
    
    async def _apply_rate_limit(self):
        """
        Note: Global rate limiting removed to allow concurrent requests.
        The Gemini API handles its own rate limiting via 429 responses,
        which we handle by rotating to the next API key.
        """
        pass  # No blocking - allow concurrent requests
    
    async def generate_response(self, prompt: str, retry_count: int = 0) -> Dict[str, Any]:
        """
        Generate a response using Gemini API with key rotation and error handling
        
        Returns:
            Dict with 'text' (response) or 'error' (error message)
        """
        MAX_RETRIES = 3
        RETRY_DELAY_SECONDS = 2
        
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Get available key
        api_key = self._get_available_key()
        
        if not api_key:
            # No available keys - try resetting failed keys if this is a retry scenario
            if self.failed_keys:
                print("[GEMINI] All keys marked as failed, resetting for retry...")
                self.failed_keys.clear()
                api_key = self._get_available_key()
            
            if not api_key:
                return {
                    'error': 'API anahtarı yapılandırılmamış. Lütfen .env dosyasını kontrol edin.',
                    'text': None
                }
        
        try:
            # Configure Gemini with current key
            genai.configure(api_key=api_key)
            
            # Create model instance
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            print(f"[GEMINI] Sending prompt ({len(prompt)} chars) to {settings.GEMINI_MODEL}")
            
            # Generate response
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )
            
            # Check if response has valid text
            if not response.parts:
                print("[GEMINI] WARNING: Empty response from API")
                return {
                    'error': 'API boş yanıt döndürdü. Lütfen tekrar deneyin.',
                    'text': None
                }
            
            print(f"[GEMINI] Response received: {len(response.text)} chars")
            print(f"[GEMINI] Response preview: '{response.text[:100]}...'")
            
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
                print(f"[GEMINI] Rate limit hit (attempt {retry_count + 1}/{MAX_RETRIES + 1}): {str(e)[:100]}")
                
                # Retry with exponential backoff instead of marking key as failed for the whole day
                # retry_count starts at 0, so we retry when retry_count < MAX_RETRIES (0, 1, 2 = 3 retries)
                if retry_count < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * (retry_count + 1)
                    print(f"[GEMINI] Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    self._rotate_key()
                    return await self.generate_response(prompt, retry_count + 1)
                else:
                    # All retries exhausted - don't mark as failed, just return error
                    print(f"[GEMINI] All {MAX_RETRIES + 1} attempts failed, giving up.")
                    return {
                        'error': 'API kota limiti aşıldı. Lütfen birkaç dakika bekleyip tekrar deneyin.',
                        'text': None
                    }
            
            # Other API errors
            print(f"[ERROR] Gemini API error: {e}")
            return {
                'error': f'API hatası: {str(e)[:100]}',
                'text': None
            }
    
    def get_status(self) -> Dict:
        """Get current API manager status"""
        current_keys = self.api_keys
        return {
            'total_keys': len(current_keys),
            'available_keys': len(current_keys) - len(self.failed_keys),
            'failed_keys_count': len(self.failed_keys),
            'current_key_index': self.current_key_index
        }


# Global instance
gemini_manager = GeminiAPIManager()