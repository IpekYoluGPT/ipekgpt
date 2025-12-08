"""
Database layer for İpekGPT - SQLite with SQLAlchemy ORM
Protects against SQL injection using parameterized queries
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import uuid

from .config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================

class Session(Base):
    """Chat session - one per dialog"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Individual message in a conversation"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Integer, nullable=True)  # Only for assistant messages
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False)


class Feedback(Base):
    """User feedback on AI responses (thumbs up/down)"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, unique=True)
    rating = Column(Integer, nullable=False)  # 1 for thumbs up, -1 for thumbs down
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    message = relationship("Message", back_populates="feedback")


class RateLimit(Base):
    """Daily rate limit tracking"""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    request_count = Column(Integer, default=0)


# ============================================================================
# Database Operations
# ============================================================================

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session - use as dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Session Operations
def create_session(db) -> Session:
    """Create a new chat session"""
    session = Session()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db, session_id: str) -> Optional[Session]:
    """Get session by ID"""
    return db.query(Session).filter(Session.id == session_id).first()


def update_session_activity(db, session_id: str):
    """Update last activity timestamp"""
    session = get_session(db, session_id)
    if session:
        session.last_activity = datetime.utcnow()
        db.commit()


# Message Operations
def add_message(db, session_id: str, role: str, content: str, response_time_ms: Optional[int] = None) -> Message:
    """Add a message to a session"""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        response_time_ms=response_time_ms
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_session_messages(db, session_id: str, limit: int = 50) -> List[Message]:
    """Get messages for a session (for context)"""
    return db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(limit).all()[::-1]


# Feedback Operations
def add_feedback(db, message_id: int, rating: int) -> Feedback:
    """Add or update feedback for a message"""
    try:
        existing = db.query(Feedback).filter(Feedback.message_id == message_id).first()
        if existing:
            existing.rating = rating
            existing.created_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            print(f"[DB] Updated feedback for message {message_id}: rating={rating}")
            return existing
        
        feedback = Feedback(message_id=message_id, rating=rating)
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        print(f"[DB] Created feedback for message {message_id}: rating={rating}, id={feedback.id}")
        return feedback
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] add_feedback failed: {e}")
        raise


# Rate Limit Operations
def get_today_request_count(db) -> int:
    """Get today's request count"""
    try:
        today = date.today()
        rate_limit = db.query(RateLimit).filter(RateLimit.date == today).first()
        count = rate_limit.request_count if rate_limit else 0
        return count
    except Exception as e:
        print(f"[DB ERROR] get_today_request_count failed: {e}")
        return 0


def increment_request_count(db) -> int:
    """Increment today's request count and return new count"""
    try:
        today = date.today()
        rate_limit = db.query(RateLimit).filter(RateLimit.date == today).first()
        
        if rate_limit:
            rate_limit.request_count += 1
        else:
            rate_limit = RateLimit(date=today, request_count=1)
            db.add(rate_limit)
        
        db.commit()
        print(f"[DB] Rate limit for {today}: count={rate_limit.request_count}")
        return rate_limit.request_count
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] increment_request_count failed: {e}")
        raise


def check_rate_limit(db) -> tuple[bool, int]:
    """Check if rate limit is exceeded. Returns (is_allowed, remaining_requests)"""
    current_count = get_today_request_count(db)
    remaining = settings.DAILY_REQUEST_LIMIT - current_count
    return remaining > 0, max(0, remaining)

