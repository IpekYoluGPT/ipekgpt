"""
reCAPTCHA verification module for bot protection
"""
import httpx
from typing import Optional
from .config import settings


async def verify_recaptcha(token: str) -> tuple[bool, Optional[float]]:
    """
    Verify reCAPTCHA token with Google's API
    
    Args:
        token: reCAPTCHA token from frontend
        
    Returns:
        Tuple of (success: bool, score: Optional[float])
        Score is only available for reCAPTCHA v3
    """
    if not settings.RECAPTCHA_SECRET_KEY:
        # If no secret key configured, skip verification (development mode)
        return True, None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.RECAPTCHA_VERIFY_URL,
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token
                }
            )
            result = response.json()
            
            success = result.get("success", False)
            score = result.get("score")  # Only for v3
            
            return success, score
            
    except Exception as e:
        print(f"reCAPTCHA verification error: {e}")
        return False, None


def is_captcha_configured() -> bool:
    """Check if reCAPTCHA is properly configured"""
    return bool(settings.RECAPTCHA_SITE_KEY and settings.RECAPTCHA_SECRET_KEY)
