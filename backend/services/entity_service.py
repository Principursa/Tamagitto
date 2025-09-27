"""Entity service for managing Tamagotchi-like creatures."""

import os
import httpx
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.entity import Entity
from models.repository import Repository
from models.health_history import HealthHistory
from models.commit_analysis import CommitAnalysis


class EntityService:
    """Service for managing virtual entities tied to repositories."""
    
    # Entity types and their characteristics
    ENTITY_TYPES = {
        "pet": {
            "base_health": 50,
            "health_decay_rate": 2,
            "max_cooldown_hours": 4,
            "traits": ["playful", "loyal", "energetic"]
        },
        "plant": {
            "base_health": 60,
            "health_decay_rate": 1,
            "max_cooldown_hours": 8,
            "traits": ["patient", "steady", "resilient"]
        },
        "creature": {
            "base_health": 40,
            "health_decay_rate": 3,
            "max_cooldown_hours": 2,
            "traits": ["wild", "unpredictable", "sensitive"]
        }
    }
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("Gemini API key not configured")
    
    async def create_entity(self, db: Session, repository: Repository, 
                          entity_type: str = None, name: str = None) -> Entity:
        """
        Create a new entity for a repository.
        
        Args:
            db: Database session
            repository: Repository to create entity for
            entity_type: Type of entity (pet, plant, creature)
            name: Custom name for entity
            
        Returns:
            Created entity
        """
        # Auto-select entity type based on repository language if not specified
        if not entity_type:
            entity_type = self._suggest_entity_type(repository.language)
        
        # Generate name if not provided
        if not name:
            name = self._generate_entity_name(entity_type, repository.name)
        
        # Get entity configuration
        config = self.ENTITY_TYPES.get(entity_type, self.ENTITY_TYPES["pet"])
        
        # Create entity with initial health
        entity = Entity(
            repository_id=repository.id,
            name=name,
            entity_type=entity_type,
            health_score=config["base_health"],
            status="alive",
            birth_date=datetime.utcnow(),
            metadata_json={
                "traits": config["traits"],
                "base_health": config["base_health"],
                "health_decay_rate": config["health_decay_rate"],
                "max_cooldown_hours": config["max_cooldown_hours"],
                "birth_repository": repository.full_name
            }
        )
        
        db.add(entity)
        db.flush()  # Get entity ID
        
        # Create initial health history entry
        initial_history = HealthHistory(
            entity_id=entity.id,
            health_score=config["base_health"],
            change_reason="birth",
            commit_analysis_id=None
        )
        db.add(initial_history)
        
        # Generate visual representation
        await self._generate_entity_visuals(entity)
        
        db.commit()
        return entity
    
    def apply_commit_impact(self, db: Session, entity: Entity, 
                          commit_analysis: CommitAnalysis) -> Dict[str, Any]:
        """
        Apply the impact of a commit analysis to an entity's health.
        
        Args:
            db: Database session
            entity: Entity to update
            commit_analysis: Commit analysis with health impact
            
        Returns:
            Dictionary with update results
        """
        if not entity.is_alive:
            return {"success": False, "reason": "Entity is dead"}
        
        if not entity.can_receive_health_update():
            return {
                "success": False, 
                "reason": "Entity is in cooldown period",
                "cooldown_remaining": entity.time_until_cooldown_expires()
            }
        
        # Apply health change
        old_health = entity.health_score
        entity_died = entity.apply_health_delta(
            commit_analysis.health_impact,
            f"commit_analysis_{commit_analysis.quality_score}",
            commit_analysis.id
        )
        
        # Update last interaction
        entity.last_interaction = datetime.utcnow()
        
        # Apply cooldown based on entity type
        config = self.ENTITY_TYPES.get(entity.entity_type, self.ENTITY_TYPES["pet"])
        cooldown_hours = random.randint(1, config["max_cooldown_hours"])
        entity.interaction_cooldown_until = datetime.utcnow() + timedelta(hours=cooldown_hours)
        
        db.commit()
        
        return {
            "success": True,
            "health_change": entity.health_score - old_health,
            "new_health": entity.health_score,
            "entity_died": entity_died,
            "status": entity.status,
            "cooldown_until": entity.interaction_cooldown_until
        }
    
    def apply_daily_decay(self, db: Session, entity: Entity) -> Dict[str, Any]:
        """
        Apply daily health decay to an entity based on inactivity.
        
        Args:
            db: Database session
            entity: Entity to update
            
        Returns:
            Dictionary with decay results
        """
        if not entity.is_alive:
            return {"success": False, "reason": "Entity is dead"}
        
        # Calculate days since last commit
        repository = db.query(Repository).filter(Repository.id == entity.repository_id).first()
        if not repository or not repository.last_monitored_at:
            days_inactive = 0
        else:
            time_diff = datetime.utcnow() - repository.last_monitored_at
            days_inactive = max(0, int(time_diff.total_seconds() / 86400))  # 86400 seconds in a day
        
        if days_inactive == 0:
            return {"success": True, "decay_applied": 0, "reason": "No inactivity"}
        
        # Apply decay
        old_health = entity.health_score
        entity_died = entity.decay_health(days_inactive)
        
        db.commit()
        
        return {
            "success": True,
            "decay_applied": old_health - entity.health_score,
            "days_inactive": days_inactive,
            "new_health": entity.health_score,
            "entity_died": entity_died,
            "status": entity.status
        }
    
    def revive_entity(self, db: Session, entity: Entity, 
                     initial_health: int = 30) -> Dict[str, Any]:
        """
        Revive a dead entity (premium feature or special conditions).
        
        Args:
            db: Database session
            entity: Entity to revive
            initial_health: Health to revive with
            
        Returns:
            Dictionary with revival results
        """
        if entity.is_alive:
            return {"success": False, "reason": "Entity is already alive"}
        
        # Reset entity status
        entity.status = "alive"
        entity.death_date = None
        entity.last_interaction = datetime.utcnow()
        entity.interaction_cooldown_until = None
        
        # Set health
        entity.update_health(initial_health, "revival")
        
        # Update metadata
        metadata = entity.custom_metadata
        metadata["revival_count"] = metadata.get("revival_count", 0) + 1
        metadata["last_revival"] = datetime.utcnow().isoformat()
        entity.update_metadata(**metadata)
        
        db.commit()
        
        return {
            "success": True,
            "new_health": entity.health_score,
            "revival_count": metadata["revival_count"]
        }
    
    def get_entity_stats(self, db: Session, entity: Entity) -> Dict[str, Any]:
        """
        Get comprehensive statistics for an entity.
        
        Args:
            db: Database session
            entity: Entity to get stats for
            
        Returns:
            Dictionary with entity statistics
        """
        # Get health history
        health_history = db.query(HealthHistory).filter(
            HealthHistory.entity_id == entity.id
        ).order_by(HealthHistory.created_at.desc()).limit(100).all()
        
        # Calculate stats
        age_days = (datetime.utcnow() - entity.birth_date).days
        total_interactions = len([h for h in health_history if h.commit_analysis_id])
        
        # Health trends
        recent_history = health_history[:30]  # Last 30 entries
        health_trend = "stable"
        if len(recent_history) >= 2:
            recent_avg = sum(h.health_score for h in recent_history[:10]) / min(10, len(recent_history))
            older_avg = sum(h.health_score for h in recent_history[10:20]) / min(10, len(recent_history[10:20]))
            if recent_avg > older_avg + 5:
                health_trend = "improving"
            elif recent_avg < older_avg - 5:
                health_trend = "declining"
        
        # Longest survival streak
        max_health = max((h.health_score for h in health_history), default=0)
        min_health = min((h.health_score for h in health_history), default=100)
        
        return {
            "entity_id": entity.id,
            "age_days": age_days,
            "current_health": entity.health_score,
            "max_health_achieved": max_health,
            "min_health_achieved": min_health,
            "total_interactions": total_interactions,
            "health_trend": health_trend,
            "status": entity.status,
            "time_until_cooldown": entity.time_until_cooldown_expires(),
            "can_interact": entity.can_receive_health_update(),
            "traits": entity.custom_metadata.get("traits", []),
            "revival_count": entity.custom_metadata.get("revival_count", 0)
        }
    
    def _suggest_entity_type(self, language: str) -> str:
        """Suggest entity type based on repository language."""
        language_mappings = {
            "Python": "creature",
            "JavaScript": "pet",
            "TypeScript": "pet", 
            "Go": "creature",
            "Rust": "creature",
            "Java": "pet",
            "C++": "creature",
            "C": "creature",
            "Ruby": "pet",
            "PHP": "pet",
            "Swift": "pet",
            "Kotlin": "pet",
            "HTML": "plant",
            "CSS": "plant",
            "Vue": "plant",
            "React": "pet"
        }
        return language_mappings.get(language, "pet")
    
    def _generate_entity_name(self, entity_type: str, repo_name: str) -> str:
        """Generate a name for the entity based on type and repo."""
        prefixes = {
            "pet": ["Buddy", "Companion", "Friend", "Pal"],
            "plant": ["Sprout", "Bloom", "Leaf", "Branch"],
            "creature": ["Shadow", "Spirit", "Guardian", "Wisp"]
        }
        
        # Clean repo name for use in entity name
        clean_repo = repo_name.replace("-", " ").replace("_", " ").title()
        if len(clean_repo) > 15:
            clean_repo = clean_repo[:15]
        
        prefix = random.choice(prefixes.get(entity_type, prefixes["pet"]))
        return f"{prefix} {clean_repo}"
    
    async def _generate_entity_visuals(self, entity: Entity) -> None:
        """
        Generate visual representations using Gemini API.
        
        Args:
            entity: Entity to generate visuals for
        """
        # This would integrate with Gemini API to generate images
        # For now, we'll set placeholder URLs
        entity.visual_url = f"https://placeholder.com/300x300?text={entity.entity_type.title()}"
        
        # Set different visual states
        visual_urls = {
            "thriving": f"https://placeholder.com/300x300?text=Happy+{entity.entity_type.title()}",
            "healthy": f"https://placeholder.com/300x300?text=Good+{entity.entity_type.title()}",
            "declining": f"https://placeholder.com/300x300?text=Sad+{entity.entity_type.title()}",
            "critical": f"https://placeholder.com/300x300?text=Sick+{entity.entity_type.title()}",
            "dead": f"https://placeholder.com/300x300?text=RIP+{entity.entity_type.title()}"
        }
        
        entity.set_visual_urls(visual_urls)
        
        # TODO: Implement actual Gemini API integration for image generation
        # This would generate custom images based on entity characteristics,
        # repository language, current health status, etc.