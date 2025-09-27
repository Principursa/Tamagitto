"""Health history model for tracking entity health changes over time."""

from typing import Optional
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from database import Base


class HealthHistory(Base):
    """Model for tracking entity health changes over time."""
    
    __tablename__ = 'health_history'
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    health_score = Column(Integer, nullable=False)
    change_reason = Column(String(100), nullable=False)  # 'commit_analysis', 'daily_decay', 'manual_reset'
    commit_analysis_id = Column(Integer, ForeignKey('commit_analyses.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    entity = relationship("Entity", back_populates="health_history")
    commit_analysis = relationship("CommitAnalysis", back_populates="health_history")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('health_score >= 0 AND health_score <= 100', name='health_history_score_range'),
    )
    
    def __repr__(self) -> str:
        return f"<HealthHistory(id={self.id}, entity_id={self.entity_id}, health_score={self.health_score}, reason='{self.change_reason}')>"
    
    def to_dict(self) -> dict:
        """Convert health history entry to dictionary."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "health_score": self.health_score,
            "change_reason": self.change_reason,
            "commit_analysis_id": self.commit_analysis_id,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }