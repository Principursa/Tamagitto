"""Authentication service for JWT tokens and user sessions."""

import os
import jwt
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from models.user import User
from models.user_session import UserSession


class AuthService:
    """Service for handling authentication and JWT tokens."""
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET environment variable not set")
        
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours
        self.refresh_token_expire_days = 30  # 30 days
    
    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user_id: User ID to encode in token
            expires_delta: Optional custom expiration time
            
        Returns:
            JWT access token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def create_refresh_token(self, user_id: int) -> str:
        """
        Create a JWT refresh token for a user.
        
        Args:
            user_id: User ID to encode in token
            
        Returns:
            JWT refresh token string
        """
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # Unique token ID for revocation
        }
        
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Extract user ID from a valid access token.
        
        Args:
            token: JWT access token
            
        Returns:
            User ID or None if token is invalid
        """
        payload = self.verify_token(token, "access")
        if payload:
            try:
                return int(payload.get("sub"))
            except (ValueError, TypeError):
                return None
        return None
    
    def create_user_session(self, db: Session, user: User, refresh_token: str,
                          user_agent: Optional[str] = None, 
                          ip_address: Optional[str] = None) -> UserSession:
        """
        Create and store a user session.
        
        Args:
            db: Database session
            user: User object
            refresh_token: JWT refresh token
            user_agent: Browser user agent
            ip_address: Client IP address
            
        Returns:
            Created user session
        """
        # Decode refresh token to get expiration and jti
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            raise ValueError("Invalid refresh token")
        
        expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        token_id = payload.get("jti")
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            refresh_token_id=token_id,
            user_agent=user_agent[:500] if user_agent else None,  # Truncate long user agents
            ip_address=ip_address,
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(session)
        db.commit()
        return session
    
    def refresh_access_token(self, db: Session, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Create a new access token using a refresh token.
        
        Args:
            db: Database session
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary with new access token or None if invalid
        """
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        user_id = payload.get("sub")
        token_id = payload.get("jti")
        
        # Verify session is still active
        session = db.query(UserSession).filter(
            UserSession.refresh_token_id == token_id,
            UserSession.is_active == True
        ).first()
        
        if not session or session.expires_at < datetime.now(timezone.utc):
            return None
        
        # Update session last used
        session.last_used_at = datetime.utcnow()
        db.commit()
        
        # Create new access token
        new_access_token = self.create_access_token(int(user_id))
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    def revoke_session(self, db: Session, refresh_token: str) -> bool:
        """
        Revoke a user session by marking it inactive.
        
        Args:
            db: Database session
            refresh_token: Refresh token to revoke
            
        Returns:
            True if session was revoked
        """
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return False
        
        token_id = payload.get("jti")
        
        session = db.query(UserSession).filter(
            UserSession.refresh_token_id == token_id,
            UserSession.is_active == True
        ).first()
        
        if session:
            session.is_active = False
            session.revoked_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    def revoke_all_user_sessions(self, db: Session, user_id: int) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of sessions revoked
        """
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.revoked_at = datetime.utcnow()
        
        db.commit()
        return len(sessions)
    
    def cleanup_expired_sessions(self, db: Session) -> int:
        """
        Clean up expired sessions from the database.
        
        Args:
            db: Database session
            
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.now(timezone.utc),
            UserSession.is_active == True
        ).all()
        
        for session in expired_sessions:
            session.is_active = False
            session.revoked_at = datetime.utcnow()
        
        db.commit()
        return len(expired_sessions)
    
    def get_user_sessions(self, db: Session, user_id: int, active_only: bool = True) -> list:
        """
        Get all sessions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            active_only: Only return active sessions
            
        Returns:
            List of user sessions
        """
        query = db.query(UserSession).filter(UserSession.user_id == user_id)
        
        if active_only:
            query = query.filter(
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        
        return query.order_by(UserSession.created_at.desc()).all()
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength (for future password-based auth).
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "strong" if len(errors) == 0 else "weak"
        }
    
    def create_auth_response(self, user: User, access_token: str, 
                           refresh_token: str) -> Dict[str, Any]:
        """
        Create a standardized authentication response.
        
        Args:
            user: Authenticated user
            access_token: JWT access token
            refresh_token: JWT refresh token
            
        Returns:
            Authentication response dictionary
        """
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,  # seconds
            "user": user.to_dict()
        }