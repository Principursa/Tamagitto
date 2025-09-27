"""Entity management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.entity import Entity
from models.repository import Repository
from services.entity_service import EntityService
from routers.auth import get_current_user_dependency

router = APIRouter(prefix="/entities", tags=["entities"])
entity_service = EntityService()


class UpdateEntityRequest(BaseModel):
    name: Optional[str] = None
    metadata: Optional[dict] = None


class ManualHealthUpdateRequest(BaseModel):
    health_change: int
    reason: str


@router.get("")
async def get_user_entities(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get all entities for the current user."""
    entities = db.query(Entity).join(Repository).filter(
        Repository.user_id == current_user.id
    ).all()
    
    entities_data = []
    for entity in entities:
        entity_dict = entity.to_dict(include_repository=True)
        # Add statistics
        stats = entity_service.get_entity_stats(db, entity)
        entity_dict["stats"] = stats
        entities_data.append(entity_dict)
    
    return {
        "entities": entities_data,
        "total": len(entities_data)
    }


@router.get("/{entity_id}")
async def get_entity(
    entity_id: int,
    include_history: bool = Query(default=False),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get a specific entity with optional history."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity_dict = entity.to_dict(
        include_repository=True, 
        include_history=include_history
    )
    
    # Add detailed statistics
    stats = entity_service.get_entity_stats(db, entity)
    entity_dict["stats"] = stats
    
    return entity_dict


@router.put("/{entity_id}")
async def update_entity(
    entity_id: int,
    request: UpdateEntityRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Update entity information."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Update name if provided
    if request.name:
        entity.name = request.name
    
    # Update metadata if provided
    if request.metadata:
        entity.update_metadata(**request.metadata)
    
    db.commit()
    
    return {
        "message": "Entity updated successfully",
        "entity": entity.to_dict(include_repository=True)
    }


@router.post("/{entity_id}/health")
async def update_entity_health(
    entity_id: int,
    request: ManualHealthUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Manually update entity health (admin/testing feature)."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if not entity.is_alive:
        raise HTTPException(status_code=400, detail="Cannot update health of dead entity")
    
    # Validate health change range
    if not -50 <= request.health_change <= 50:
        raise HTTPException(status_code=400, detail="Health change must be between -50 and +50")
    
    # Apply health change
    old_health = entity.health_score
    entity_died = entity.apply_health_delta(
        request.health_change, 
        f"manual_{request.reason}"
    )
    
    db.commit()
    
    return {
        "message": "Health updated successfully",
        "previous_health": old_health,
        "new_health": entity.health_score,
        "health_change": request.health_change,
        "entity_died": entity_died,
        "status": entity.status
    }


@router.post("/{entity_id}/revive")
async def revive_entity(
    entity_id: int,
    initial_health: int = Query(default=30, ge=1, le=50),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Revive a dead entity."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if entity.is_alive:
        raise HTTPException(status_code=400, detail="Entity is already alive")
    
    # Revive entity
    revival_result = entity_service.revive_entity(db, entity, initial_health)
    
    if not revival_result["success"]:
        raise HTTPException(status_code=400, detail=revival_result["reason"])
    
    return {
        "message": "Entity revived successfully",
        "entity": entity.to_dict(),
        "revival_count": revival_result["revival_count"]
    }


@router.post("/{entity_id}/decay")
async def apply_decay_to_entity(
    entity_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Apply daily decay to entity (testing/admin feature)."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Apply decay
    decay_result = entity_service.apply_daily_decay(db, entity)
    
    return {
        "message": "Decay applied",
        "decay_result": decay_result,
        "entity": entity.to_dict()
    }


@router.get("/{entity_id}/history")
async def get_entity_health_history(
    entity_id: int,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get entity health history."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    from models.health_history import HealthHistory
    
    history = db.query(HealthHistory).filter(
        HealthHistory.entity_id == entity_id
    ).order_by(HealthHistory.created_at.desc()).limit(limit).all()
    
    return {
        "entity_id": entity_id,
        "history": [h.to_dict() for h in history],
        "total_entries": len(history)
    }


@router.get("/{entity_id}/stats")
async def get_entity_statistics(
    entity_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get detailed entity statistics."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    stats = entity_service.get_entity_stats(db, entity)
    
    return {
        "entity_id": entity_id,
        "stats": stats
    }


@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete an entity and all its data."""
    entity = db.query(Entity).join(Repository).filter(
        Entity.id == entity_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Store info for response
    entity_name = entity.name
    repository_name = entity.repository.full_name
    
    # Delete entity (cascade will handle health history)
    db.delete(entity)
    db.commit()
    
    return {
        "message": "Entity deleted successfully",
        "deleted_entity": entity_name,
        "repository": repository_name
    }