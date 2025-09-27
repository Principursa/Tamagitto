"""User model with GitHub integration and token encryption."""

import os
import hashlib
from typing import Optional
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import base64

from backend.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model with GitHub OAuth integration."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    github_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    access_token_encrypted = Column(Text, nullable=False)
    encryption_key_hash = Column(String(64), nullable=False)
    avatar_url = Column(Text, nullable=True)
    last_active = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Relationships
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', github_id='{self.github_id}')>"
    
    def encrypt_token(self, token: str, master_key: Optional[bytes] = None) -> None:
        """
        Encrypt and store the GitHub access token.
        
        Args:
            token: The GitHub access token to encrypt
            master_key: Optional master encryption key, will use environment variable if not provided
        """
        if master_key is None:
            master_key = self._get_master_key()
        
        # Generate a unique key for this user
        user_key = self._derive_user_key(master_key, self.github_id)
        
        # Encrypt the token
        f = Fernet(user_key)
        encrypted_token = f.encrypt(token.encode())
        
        # Store encrypted token and key hash
        self.access_token_encrypted = base64.b64encode(encrypted_token).decode()
        self.encryption_key_hash = hashlib.sha256(user_key).hexdigest()
    
    def decrypt_token(self, master_key: Optional[bytes] = None) -> str:
        """
        Decrypt and return the GitHub access token.
        
        Args:
            master_key: Optional master encryption key, will use environment variable if not provided
            
        Returns:
            The decrypted GitHub access token
            
        Raises:
            ValueError: If decryption fails or key doesn't match
        """
        if master_key is None:
            master_key = self._get_master_key()
        
        # Derive the user key
        user_key = self._derive_user_key(master_key, self.github_id)
        
        # Verify key matches stored hash
        if hashlib.sha256(user_key).hexdigest() != self.encryption_key_hash:
            raise ValueError("Encryption key mismatch")
        
        # Decrypt the token
        f = Fernet(user_key)
        encrypted_token = base64.b64decode(self.access_token_encrypted.encode())
        
        try:
            decrypted_token = f.decrypt(encrypted_token).decode()
            return decrypted_token
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {e}")
    
    def update_last_active(self) -> None:
        """Update the last_active timestamp to current time."""
        self.last_active = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding sensitive data)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "github_id": self.github_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None
        }
    
    @staticmethod
    def _get_master_key() -> bytes:
        """Get the master encryption key from environment."""
        key_str = os.getenv("ENCRYPTION_KEY")
        if not key_str:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        try:
            # Decode base64 key
            return base64.b64decode(key_str)
        except Exception:
            # If not base64, treat as raw string and pad/truncate to 32 bytes
            key_bytes = key_str.encode()[:32].ljust(32, b'\0')
            return base64.urlsafe_b64encode(key_bytes)
    
    @staticmethod
    def _derive_user_key(master_key: bytes, github_id: str) -> bytes:
        """
        Derive a unique encryption key for a user.
        
        Args:
            master_key: The master encryption key
            github_id: The user's GitHub ID
            
        Returns:
            A Fernet-compatible key unique to this user
        """
        # Create a unique salt using the GitHub ID
        salt = hashlib.sha256(github_id.encode()).digest()
        
        # Derive key using PBKDF2
        import hashlib
        key = hashlib.pbkdf2_hmac('sha256', master_key, salt, 100000)
        
        # Encode as base64 for Fernet
        return base64.urlsafe_b64encode(key)
    
    @classmethod
    def create_from_github(cls, github_user: dict, access_token: str) -> "User":
        """
        Create a new user from GitHub user data.
        
        Args:
            github_user: GitHub user information dictionary
            access_token: GitHub access token
            
        Returns:
            New User instance (not yet committed to database)
        """
        user = cls(
            github_id=str(github_user["id"]),
            username=github_user["login"],
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url")
        )
        
        # Encrypt and store the access token
        user.encrypt_token(access_token)
        
        return user