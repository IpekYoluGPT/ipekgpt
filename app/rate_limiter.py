"""
Rate limiting middleware for controlling daily API requests
"""
from datetime import datetime, date, timedelta
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from .config import settings


class RateLimiter:
    """Rate limiter that tracks daily request count"""
    
    def __init__(self, daily_limit: int = None):
        self.daily_limit = daily_limit or settings.DAILY_REQUEST_LIMIT
    
    def get_reset_time(self) -> str:
        """Get the time when rate limit resets (midnight local time)"""
        tomorrow = date.today() + timedelta(days=1)
        reset_datetime = datetime.combine(tomorrow, datetime.min.time())
        return reset_datetime.isoformat()
    
    def check_and_increment(self, db: DBSession) -> tuple[bool, int, str]:
        """
        Check if request is allowed and increment counter
        
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_time: str)
        """
        from .database import get_today_request_count, increment_request_count
        
        current_count = get_today_request_count(db)
        
        if current_count >= self.daily_limit:
            return False, 0, self.get_reset_time()
        
        # Increment the counter
        new_count = increment_request_count(db)
        remaining = max(0, self.daily_limit - new_count)
        
        return True, remaining, self.get_reset_time()


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to check rate limits for chat endpoints
    Note: This only applies to POST /api/chat endpoint
    """
    # Only rate limit the chat endpoint
    if request.url.path == "/api/chat" and request.method == "POST":
        # Rate limiting is handled in the endpoint itself
        # because we need the database session
        pass
    
    response = await call_next(request)
    return response
