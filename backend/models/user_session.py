"""User session model for JWT token management."""

from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class UserSession(Base):
    """Model for managing user authentication sessions."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at='{self.expires_at}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid (not expired)."""
        return not self.is_expired
    
    def extend_session(self, hours: int = 24) -> None:
        """Extend session expiration time."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_used_at = datetime.utcnow()
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_valid": self.is_valid,
        }
    
    @classmethod
    def create_for_user(cls, user_id: int, session_token: str, hours: int = 24) -> "UserSession":
        """
        Create a new session for a user.
        
        Args:
            user_id: The user ID this session belongs to
            session_token: The JWT session token
            hours: Hours until session expires
            
        Returns:
            New UserSession instance
        """
        expires_at = datetime.utcnow() + timedelta(hours=hours)
        
        return cls(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at
        )