"""
İpekGPT Web Application - FastAPI Main Entry Point
"""
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DBSession

from .config import settings
from .database import (
    init_db, get_db, create_session, get_session, update_session_activity,
    add_feedback, check_rate_limit, increment_request_count
)

# In-memory message ID counter for feedback (no message content stored)
_message_id_counter = 0
from .models import (
    ChatRequest, ChatResponse, SessionResponse, FeedbackRequest,
    FeedbackResponse, ErrorResponse, RateLimitResponse
)
from .rate_limiter import rate_limiter
from .request_queue import request_queue


# ============================================================================
# Application Lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize resources on startup"""

    
    # Initialize database
    init_db()

    
    # Initialize RAG system (loads ChromaDB - no heavy model download needed anymore)

    from .rag_engine import rag_system
    rag_system.initialize()

    
    # Set up request queue handler
    async def process_chat_request(session_id: str, message: str, history: list):
        """Handler for queued chat requests with conversation history"""
        result = await rag_system.ask_async(message, history=history)
        return result
    
    request_queue.set_handler(process_chat_request)
    await request_queue.start_processor()

    
    yield
    
    # Cleanup
    await request_queue.stop_processor()



# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="İpekGPT API",
    description="RAG-based AI Assistant for İpek Yolu Uluslararası Çocuk ve Gençlik Çalışmaları Merkezi",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware - use configured origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# Routes
# ============================================================================

@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the chat interface"""
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)


@app.get("/api/config")
async def get_config():
    """Get frontend configuration"""
    return {
        "daily_limit": settings.DAILY_REQUEST_LIMIT,
        "max_message_length": settings.MAX_MESSAGE_LENGTH
    }


@app.post("/api/session", response_model=SessionResponse)
async def create_new_session(db: DBSession = Depends(get_db)):
    """Create a new chat session"""
    session = create_session(db)
    return SessionResponse(
        session_id=session.id,
        created_at=session.created_at
    )


@app.post("/ipekgpt/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: DBSession = Depends(get_db)):
    """
    Send a message and get AI response
    Protected by rate limiting and optional reCAPTCHA
    Uses FIFO queue for request ordering
    """
    # Check rate limit
    allowed, remaining = check_rate_limit(db)
    if not allowed:
        reset_time = rate_limiter.get_reset_time()
        return JSONResponse(
            status_code=429,
            content=RateLimitResponse(
                remaining_requests=0,
                reset_time=reset_time
            ).model_dump()
        )
    
    # Verify session exists
    session = get_session(db, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session activity
    update_session_activity(db, request.session_id)
    
    # Process through FIFO queue with history
    result = await request_queue.enqueue(request.session_id, request.message, request.history)
    
    # Generate message ID for feedback tracking (no content stored)
    global _message_id_counter
    _message_id_counter += 1
    message_id = _message_id_counter
    
    return ChatResponse(
        message_id=message_id,
        response=result['answer'],
        response_time_ms=result.get('response_time_ms', 0),
        sources_count=result.get('num_sources', 0),
        rating=0  # New message, no vote yet
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, db: DBSession = Depends(get_db)):
    """Submit feedback (thumbs up/down) for an AI response"""
    try:

        result = add_feedback(db, request.message_id, request.rating)

        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )
    except Exception as e:

        return FeedbackResponse(
            success=False,
            message=str(e)
        )



@app.get("/api/rate-limit")
async def get_rate_limit_status(db: DBSession = Depends(get_db)):
    """Get current rate limit status"""
    allowed, remaining = check_rate_limit(db)
    return {
        "allowed": allowed,
        "remaining": remaining,
        "daily_limit": settings.DAILY_REQUEST_LIMIT,
        "reset_time": rate_limiter.get_reset_time()
    }


@app.get("/api/queue-status")
async def get_queue_status():
    """Get request queue status"""
    return request_queue.get_status()


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from .gemini_api import gemini_manager
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "api_keys_status": gemini_manager.get_status(),
        "queue_status": request_queue.get_status()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        access_log=False,
        log_level="critical"
    )
