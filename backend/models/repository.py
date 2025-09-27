"""Repository model for GitHub repository monitoring."""

from typing import Optional
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base, TimestampMixin


class Repository(Base, TimestampMixin):
    """Repository model for tracking monitored GitHub repositories."""
    
    __tablename__ = 'repositories'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    github_repo_id = Column(BigInteger, nullable=False)
    full_name = Column(String(255), nullable=False)  # e.g., "username/repo-name"
    default_branch = Column(String(100), default='main', nullable=False)
    language = Column(String(50), nullable=True)
    private = Column(Boolean, default=False, nullable=False)
    monitoring_active = Column(Boolean, default=True, nullable=False)
    webhook_id = Column(String(50), nullable=True)  # GitHub webhook ID if configured
    last_commit_sha = Column(String(40), nullable=True)
    last_monitored_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="repositories")
    entity = relationship("Entity", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    commit_analyses = relationship("CommitAnalysis", back_populates="repository", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        # Unique constraint on user_id and github_repo_id
        {"sqlite_autoincrement": True}  # For SQLite compatibility
    )
    
    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, full_name='{self.full_name}', monitoring_active={self.monitoring_active})>"
    
    def update_last_monitored(self, commit_sha: Optional[str] = None) -> None:
        """Update the last monitored timestamp and optionally the last commit SHA."""
        self.last_monitored_at = datetime.utcnow()
        if commit_sha:
            self.last_commit_sha = commit_sha
    
    def enable_monitoring(self) -> None:
        """Enable monitoring for this repository."""
        self.monitoring_active = True
        self.update_last_monitored()
    
    def disable_monitoring(self) -> None:
        """Disable monitoring for this repository."""
        self.monitoring_active = False
    
    def set_webhook(self, webhook_id: str) -> None:
        """Set the GitHub webhook ID for this repository."""
        self.webhook_id = webhook_id
    
    def remove_webhook(self) -> None:
        """Remove the GitHub webhook ID for this repository."""
        self.webhook_id = None
    
    def to_dict(self, include_monitoring_status: bool = True) -> dict:
        """
        Convert repository to dictionary.
        
        Args:
            include_monitoring_status: Whether to include monitoring status fields
            
        Returns:
            Dictionary representation of the repository
        """
        data = {
            "id": self.id,
            "github_repo_id": self.github_repo_id,
            "full_name": self.full_name,
            "default_branch": self.default_branch,
            "language": self.language,
            "private": self.private,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_monitoring_status:
            data.update({
                "monitoring_active": self.monitoring_active,
                "last_commit_sha": self.last_commit_sha,
                "last_monitored_at": self.last_monitored_at.isoformat() if self.last_monitored_at else None,
                "has_webhook": self.webhook_id is not None,
            })
        
        return data
    
    @property
    def is_being_monitored(self) -> bool:
        """Check if this repository is currently being monitored."""
        return self.monitoring_active and self.entity is not None
    
    @property
    def owner(self) -> str:
        """Get the repository owner from the full name."""
        return self.full_name.split("/")[0] if "/" in self.full_name else ""
    
    @property
    def name(self) -> str:
        """Get the repository name from the full name."""
        return self.full_name.split("/")[1] if "/" in self.full_name else self.full_name
    
    @classmethod
    def create_from_github(cls, user_id: int, github_repo: dict) -> "Repository":
        """
        Create a new repository from GitHub repository data.
        
        Args:
            user_id: The ID of the user who owns this repository
            github_repo: GitHub repository information dictionary
            
        Returns:
            New Repository instance (not yet committed to database)
        """
        return cls(
            user_id=user_id,
            github_repo_id=github_repo["id"],
            full_name=github_repo["full_name"],
            default_branch=github_repo.get("default_branch", "main"),
            language=github_repo.get("language"),
            private=github_repo.get("private", False),
            monitoring_active=False  # Start with monitoring disabled
        )
    
    def needs_monitoring_update(self, hours_threshold: int = 6) -> bool:
        """
        Check if this repository needs a monitoring update.
        
        Args:
            hours_threshold: Hours since last monitoring to consider update needed
            
        Returns:
            True if repository needs monitoring update
        """
        if not self.monitoring_active:
            return False
        
        if not self.last_monitored_at:
            return True
        
        time_diff = datetime.utcnow() - self.last_monitored_at
        return time_diff.total_seconds() > (hours_threshold * 3600)