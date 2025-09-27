"""Commit analysis model for tracking code quality metrics."""

from typing import Optional, Dict, Any
from datetime import datetime
import json

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from database import Base, TimestampMixin


class CommitAnalysis(Base, TimestampMixin):
    """Model for storing commit analysis results and quality metrics."""
    
    __tablename__ = 'commit_analyses'
    
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)
    commit_sha = Column(String(40), nullable=False)
    commit_message = Column(Text, nullable=True)
    author_login = Column(String(100), nullable=True)
    committed_at = Column(DateTime, nullable=False)
    
    # File change metrics
    files_changed = Column(Integer, default=0, nullable=False)
    lines_added = Column(Integer, default=0, nullable=False)
    lines_deleted = Column(Integer, default=0, nullable=False)
    
    # Quality metrics (scores from 0.0 to 10.0)
    complexity_score = Column(Numeric(5, 2), nullable=True)
    test_coverage_delta = Column(Numeric(5, 2), nullable=True)
    documentation_score = Column(Numeric(5, 2), nullable=True)
    linting_violations = Column(Integer, default=0, nullable=False)
    security_issues = Column(Integer, default=0, nullable=False)
    
    # Calculated scores
    overall_quality_score = Column(Numeric(5, 2), nullable=False)
    health_delta = Column(Integer, nullable=False)  # Impact on entity health (-20 to +20)
    
    # Detailed analysis data
    analysis_json = Column(JSON, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    repository = relationship("Repository", back_populates="commit_analyses")
    health_history = relationship("HealthHistory", back_populates="commit_analysis")
    
    def __repr__(self) -> str:
        return f"<CommitAnalysis(id={self.id}, commit_sha='{self.commit_sha[:8]}', quality_score={self.overall_quality_score})>"
    
    @property
    def short_sha(self) -> str:
        """Get shortened commit SHA."""
        return self.commit_sha[:8] if self.commit_sha else ""
    
    @property
    def analysis_data(self) -> Dict[str, Any]:
        """Get analysis data as dictionary."""
        if isinstance(self.analysis_json, str):
            return json.loads(self.analysis_json)
        return self.analysis_json or {}
    
    @property
    def net_lines_changed(self) -> int:
        """Get net lines changed (added - deleted)."""
        return self.lines_added - self.lines_deleted
    
    @property
    def total_lines_changed(self) -> int:
        """Get total lines changed (added + deleted)."""
        return self.lines_added + self.lines_deleted
    
    def calculate_overall_quality_score(self) -> float:
        """
        Calculate overall quality score based on individual metrics.
        
        Returns:
            Overall quality score from 0.0 to 10.0
        """
        scores = []
        weights = []
        
        # Complexity score (lower is better, so invert)
        if self.complexity_score is not None:
            scores.append(max(0, 10.0 - float(self.complexity_score)))
            weights.append(0.3)
        
        # Test coverage delta (higher is better)
        if self.test_coverage_delta is not None:
            scores.append(max(0, min(10.0, float(self.test_coverage_delta))))
            weights.append(0.3)
        
        # Documentation score (higher is better)
        if self.documentation_score is not None:
            scores.append(float(self.documentation_score))
            weights.append(0.2)
        
        # Linting violations (fewer is better)
        linting_penalty = min(5.0, self.linting_violations * 0.5)
        scores.append(max(0, 10.0 - linting_penalty))
        weights.append(0.1)
        
        # Security issues (fewer is better)
        security_penalty = min(10.0, self.security_issues * 2.0)
        scores.append(max(0, 10.0 - security_penalty))
        weights.append(0.1)
        
        if not scores:
            return 5.0  # Default neutral score
        
        # Calculate weighted average
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)
        
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 5.0
    
    def calculate_health_delta(self) -> int:
        """
        Calculate health impact based on quality score and other factors.
        
        Returns:
            Health delta from -20 to +20
        """
        base_delta = 0
        quality_score = float(self.overall_quality_score)
        
        # Base delta from quality score
        if quality_score >= 8.0:
            base_delta = 5  # Excellent quality
        elif quality_score >= 6.0:
            base_delta = 2  # Good quality
        elif quality_score >= 4.0:
            base_delta = 0  # Neutral quality
        elif quality_score >= 2.0:
            base_delta = -3  # Poor quality
        else:
            base_delta = -5  # Very poor quality
        
        # Adjust for specific factors
        if self.security_issues > 0:
            base_delta -= self.security_issues * 2  # Security issues are serious
        
        if self.test_coverage_delta and float(self.test_coverage_delta) > 0:
            base_delta += 2  # Bonus for adding tests
        
        # Size adjustment (very large commits are riskier)
        if self.total_lines_changed > 1000:
            base_delta -= 2
        elif self.total_lines_changed > 500:
            base_delta -= 1
        
        # Clamp to valid range
        return max(-20, min(20, base_delta))
    
    def update_metrics_from_analysis(self, analysis_result: Dict[str, Any]) -> None:
        """
        Update metrics from analysis result dictionary.
        
        Args:
            analysis_result: Dictionary containing analysis results
        """
        self.analysis_json = analysis_result
        
        # Extract individual metrics
        self.complexity_score = analysis_result.get("complexity_score")
        self.test_coverage_delta = analysis_result.get("test_coverage_delta")
        self.documentation_score = analysis_result.get("documentation_score")
        self.linting_violations = analysis_result.get("linting_violations", 0)
        self.security_issues = analysis_result.get("security_issues", 0)
        
        # Calculate derived metrics
        self.overall_quality_score = self.calculate_overall_quality_score()
        self.health_delta = self.calculate_health_delta()
        
        self.processed_at = datetime.utcnow()
    
    def to_dict(self, include_analysis_data: bool = False) -> dict:
        """
        Convert commit analysis to dictionary.
        
        Args:
            include_analysis_data: Whether to include detailed analysis data
            
        Returns:
            Dictionary representation of the commit analysis
        """
        data = {
            "id": self.id,
            "repository_id": self.repository_id,
            "commit": {
                "sha": self.commit_sha,
                "short_sha": self.short_sha,
                "message": self.commit_message,
                "author": self.author_login,
                "committed_at": self.committed_at.isoformat() if self.committed_at else None,
            },
            "file_changes": {
                "files_changed": self.files_changed,
                "lines_added": self.lines_added,
                "lines_deleted": self.lines_deleted,
                "net_change": self.net_lines_changed,
                "total_change": self.total_lines_changed,
            },
            "quality_metrics": {
                "overall_score": float(self.overall_quality_score) if self.overall_quality_score else None,
                "complexity_score": float(self.complexity_score) if self.complexity_score else None,
                "test_coverage_delta": float(self.test_coverage_delta) if self.test_coverage_delta else None,
                "documentation_score": float(self.documentation_score) if self.documentation_score else None,
                "linting_violations": self.linting_violations,
                "security_issues": self.security_issues,
            },
            "health_impact": {
                "delta": self.health_delta,
                "reason": self._get_health_impact_reason(),
            },
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_analysis_data:
            data["analysis_data"] = self.analysis_data
        
        return data
    
    def _get_health_impact_reason(self) -> str:
        """Get human-readable reason for health impact."""
        if self.health_delta > 5:
            return "Excellent code quality with great test coverage"
        elif self.health_delta > 0:
            return "Good code quality and clean implementation"
        elif self.health_delta == 0:
            return "Neutral code quality"
        elif self.health_delta > -5:
            return "Below average code quality"
        else:
            return "Poor code quality with security or complexity issues"
    
    @classmethod
    def create_from_commit(cls, repository_id: int, commit_data: Dict[str, Any]) -> "CommitAnalysis":
        """
        Create a new commit analysis from commit data.
        
        Args:
            repository_id: The repository ID this commit belongs to
            commit_data: Commit information from GitHub API
            
        Returns:
            New CommitAnalysis instance (not yet committed to database)
        """
        return cls(
            repository_id=repository_id,
            commit_sha=commit_data["sha"],
            commit_message=commit_data.get("message", ""),
            author_login=commit_data.get("author", {}).get("login"),
            committed_at=datetime.fromisoformat(commit_data["committed_at"].replace("Z", "+00:00")),
            files_changed=len(commit_data.get("files", [])),
            lines_added=sum(f.get("additions", 0) for f in commit_data.get("files", [])),
            lines_deleted=sum(f.get("deletions", 0) for f in commit_data.get("files", [])),
            overall_quality_score=5.0,  # Default neutral score
            health_delta=0  # Will be calculated after analysis
        )