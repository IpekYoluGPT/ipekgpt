"""
Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    session_id: str = Field(..., description="Session ID for the conversation")
    message: str = Field(..., min_length=1, max_length=300, description="User message (max 300 characters)")
    recaptcha_token: Optional[str] = Field(None, description="reCAPTCHA verification token")


class FeedbackRequest(BaseModel):
    """Request model for feedback endpoint"""
    message_id: int = Field(..., description="ID of the AI message to rate")
    rating: int = Field(..., ge=-1, le=1, description="Rating: 1 for thumbs up, -1 for thumbs down")


class RecaptchaVerifyRequest(BaseModel):
    """Request model for reCAPTCHA verification"""
    token: str = Field(..., description="reCAPTCHA token from frontend")


# ============================================================================
# Response Models
# ============================================================================

class SessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str
    created_at: datetime


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    message_id: int
    response: str
    response_time_ms: int
    sources_count: int
    rating: int = Field(default=0, description="Rating: 0 = no vote, 1 = positive, -1 = negative")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    success: bool
    message: str


class RecaptchaVerifyResponse(BaseModel):
    """Response model for reCAPTCHA verification"""
    success: bool
    score: Optional[float] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None


class RateLimitResponse(BaseModel):
    """Response when rate limit is exceeded"""
    error: str = "Rate limit exceeded"
    remaining_requests: int = 0
    reset_time: str
