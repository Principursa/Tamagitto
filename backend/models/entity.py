"""Entity model for virtual Tamagotchi-like creatures."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from backend.database import Base, TimestampMixin


class Entity(Base, TimestampMixin):
    """Entity model representing virtual creatures/pets/plants tied to repositories."""
    
    __tablename__ = 'entities'
    
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id'), nullable=False, unique=True)
    entity_type = Column(String(50), nullable=False)  # 'pet', 'plant', 'robot', 'golem', 'blob'
    name = Column(String(100), nullable=True)
    health_score = Column(Integer, default=100, nullable=False)
    visual_url = Column(Text, nullable=False)
    visual_urls_json = Column(JSON, nullable=True)  # Different health state images
    status = Column(String(20), default='alive', nullable=False)  # 'alive', 'dying', 'dead'
    metadata_json = Column(JSON, default=dict, nullable=False)  # Entity-specific attributes
    death_date = Column(DateTime, nullable=True)
    
    # Relationships
    repository = relationship("Repository", back_populates="entity")
    health_history = relationship("HealthHistory", back_populates="entity", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('health_score >= 0 AND health_score <= 100', name='health_score_range'),
        CheckConstraint("status IN ('alive', 'dying', 'dead')", name='valid_status'),
        CheckConstraint("entity_type IN ('pet', 'plant', 'robot', 'golem', 'blob')", name='valid_entity_type'),
    )
    
    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}', health={self.health_score})>"
    
    @property
    def is_alive(self) -> bool:
        """Check if the entity is alive."""
        return self.status == 'alive'
    
    @property
    def is_dead(self) -> bool:
        """Check if the entity is dead."""
        return self.status == 'dead'
    
    @property
    def health_status(self) -> str:
        """Get descriptive health status based on health score."""
        if self.health_score >= 80:
            return 'thriving'
        elif self.health_score >= 60:
            return 'healthy'
        elif self.health_score >= 40:
            return 'okay'
        elif self.health_score >= 20:
            return 'poor'
        else:
            return 'dying'
    
    @property
    def visual_state_url(self) -> str:
        """Get the appropriate visual URL based on current health status."""
        if not self.visual_urls_json:
            return self.visual_url
        
        urls = self.visual_urls_json
        health_status = self.health_status
        
        if self.is_dead:
            return urls.get('dead', self.visual_url)
        
        return urls.get(health_status, self.visual_url)
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if isinstance(self.metadata_json, str):
            return json.loads(self.metadata_json)
        return self.metadata_json or {}
    
    def update_health(self, new_health: int, reason: str = "manual_update", 
                     commit_analysis_id: Optional[int] = None) -> bool:
        """
        Update entity health score and manage status transitions.
        
        Args:
            new_health: New health score (0-100)
            reason: Reason for health change
            commit_analysis_id: Optional commit analysis that caused the change
            
        Returns:
            True if entity died due to this update, False otherwise
        """
        # Clamp health score to valid range
        new_health = max(0, min(100, new_health))
        old_health = self.health_score
        old_status = self.status
        
        self.health_score = new_health
        
        # Update status based on health
        if new_health == 0 and self.status != 'dead':
            self.status = 'dead'
            self.death_date = datetime.utcnow()
        elif new_health <= 15 and self.status == 'alive':
            self.status = 'dying'
        elif new_health > 15 and self.status == 'dying':
            self.status = 'alive'
        
        # Create health history entry
        from backend.models.health_history import HealthHistory
        history_entry = HealthHistory(
            entity_id=self.id,
            health_score=new_health,
            change_reason=reason,
            commit_analysis_id=commit_analysis_id
        )
        self.health_history.append(history_entry)
        
        # Return True if entity just died
        return old_status != 'dead' and self.status == 'dead'
    
    def apply_health_delta(self, delta: int, reason: str = "commit_analysis",
                          commit_analysis_id: Optional[int] = None) -> bool:
        """
        Apply a health delta to the current health score.
        
        Args:
            delta: Health change (-20 to +20 typically)
            reason: Reason for health change
            commit_analysis_id: Optional commit analysis that caused the change
            
        Returns:
            True if entity died due to this update, False otherwise
        """
        new_health = self.health_score + delta
        return self.update_health(new_health, reason, commit_analysis_id)
    
    def decay_health(self, days_since_last_commit: int) -> bool:
        """
        Apply daily health decay based on inactivity.
        
        Args:
            days_since_last_commit: Number of days since last commit
            
        Returns:
            True if entity died due to decay, False otherwise
        """
        if not self.is_alive:
            return False
        
        # Apply decay: -2 health per day after 3-day grace period
        if days_since_last_commit > 3:
            decay_days = days_since_last_commit - 3
            decay_amount = min(decay_days * 2, 20)  # Cap at -20 per decay cycle
            return self.apply_health_delta(-decay_amount, "daily_decay")
        
        return False
    
    def reset_to_full_health(self, reason: str = "manual_reset") -> None:
        """Reset entity to full health and alive status."""
        self.health_score = 100
        self.status = 'alive'
        self.death_date = None
        
        # Create health history entry
        from backend.models.health_history import HealthHistory
        history_entry = HealthHistory(
            entity_id=self.id,
            health_score=100,
            change_reason=reason
        )
        self.health_history.append(history_entry)
    
    def set_visual_urls(self, urls: Dict[str, str]) -> None:
        """
        Set visual URLs for different health states.
        
        Args:
            urls: Dictionary mapping health states to image URLs
                 Expected keys: 'thriving', 'healthy', 'okay', 'poor', 'dying', 'dead'
        """
        self.visual_urls_json = urls
        # Update main visual URL to current state
        self.visual_url = self.visual_state_url
    
    def update_metadata(self, **kwargs) -> None:
        """Update entity metadata with new key-value pairs."""
        current_metadata = self.metadata
        current_metadata.update(kwargs)
        self.metadata_json = current_metadata
    
    def to_dict(self, include_repository: bool = False, include_history: bool = False) -> dict:
        """
        Convert entity to dictionary.
        
        Args:
            include_repository: Whether to include repository information
            include_history: Whether to include recent health history
            
        Returns:
            Dictionary representation of the entity
        """
        data = {
            "id": self.id,
            "repository_id": self.repository_id,
            "name": self.name,
            "type": self.entity_type,
            "health_score": self.health_score,
            "health_status": self.health_status,
            "status": self.status,
            "visual_url": self.visual_state_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "death_date": self.death_date.isoformat() if self.death_date else None,
        }
        
        if include_repository and self.repository:
            data["repository"] = {
                "full_name": self.repository.full_name,
                "language": self.repository.language,
                "private": self.repository.private
            }
        
        if include_history and self.health_history:
            # Include last 10 health history entries
            recent_history = sorted(self.health_history, key=lambda x: x.created_at, reverse=True)[:10]
            data["recent_history"] = [entry.to_dict() for entry in recent_history]
        
        return data
    
    @classmethod
    def create_for_repository(cls, repository_id: int, entity_preferences: Optional[Dict[str, Any]] = None) -> "Entity":
        """
        Create a new entity for a repository.
        
        Args:
            repository_id: The repository ID this entity belongs to
            entity_preferences: Optional preferences for entity creation
            
        Returns:
            New Entity instance (not yet committed to database)
        """
        preferences = entity_preferences or {}
        
        # Determine entity type (will be enhanced with language detection)
        entity_type = preferences.get("type", "pet")
        
        # Generate name (will be enhanced with AI generation)
        name = preferences.get("name", f"Code{entity_type.title()}")
        
        # Default visual URL (will be replaced with generated image)
        visual_url = f"https://api.placeholder.com/entities/{entity_type}/default.png"
        
        return cls(
            repository_id=repository_id,
            entity_type=entity_type,
            name=name,
            health_score=100,
            visual_url=visual_url,
            status='alive',
            metadata_json={
                "preferences": preferences,
                "created_from": "repository_monitoring"
            }
        )
    
    def days_since_creation(self) -> int:
        """Get the number of days since entity was created."""
        if not self.created_at:
            return 0
        delta = datetime.utcnow() - self.created_at
        return delta.days
    
    def time_until_cooldown_expires(self, cooldown_hours: int = 48) -> Optional[timedelta]:
        """
        Calculate time remaining until entity reset cooldown expires.
        
        Args:
            cooldown_hours: Hours to wait before allowing reset
            
        Returns:
            Timedelta until cooldown expires, or None if not in cooldown
        """
        if not self.death_date:
            return None
        
        cooldown_end = self.death_date + timedelta(hours=cooldown_hours)
        now = datetime.utcnow()
        
        if now < cooldown_end:
            return cooldown_end - now
        
        return None
    
    @property
    def can_be_reset(self) -> bool:
        """Check if entity can be reset (cooldown period has passed)."""
        return self.time_until_cooldown_expires() is None