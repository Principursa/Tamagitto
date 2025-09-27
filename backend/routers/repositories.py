"""Repository management API routes."""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.repository import Repository
from models.entity import Entity
from services.github_service import GitHubService
from services.entity_service import EntityService
from services.webhook_service import WebhookService
from routers.auth import get_current_user_dependency

router = APIRouter(prefix="/repositories", tags=["repositories"])
github_service = GitHubService()
entity_service = EntityService()
webhook_service = WebhookService()


class CreateEntityRequest(BaseModel):
    entity_type: Optional[str] = None
    name: Optional[str] = None


class EnableMonitoringRequest(BaseModel):
    enable_webhook: bool = True


@router.get("")
async def get_repositories(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get user's repositories from database."""
    repositories = db.query(Repository).filter(
        Repository.user_id == current_user.id
    ).all()
    
    return {
        "repositories": [repo.to_dict() for repo in repositories],
        "total": len(repositories)
    }


@router.get("/github")
async def get_github_repositories(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Fetch repositories from GitHub and sync with database."""
    try:
        access_token = current_user.decrypt_token()
        github_repos = await github_service.get_user_repositories(access_token)
        
        # Sync with database
        synced_repos = []
        for github_repo in github_repos:
            # Check if repository exists in database
            existing_repo = db.query(Repository).filter(
                Repository.user_id == current_user.id,
                Repository.github_repo_id == github_repo["id"]
            ).first()
            
            if existing_repo:
                # Update existing repository info
                existing_repo.full_name = github_repo["full_name"]
                existing_repo.default_branch = github_repo.get("default_branch", "main")
                existing_repo.language = github_repo.get("language")
                existing_repo.private = github_repo.get("private", False)
                synced_repos.append(existing_repo.to_dict())
            else:
                # Create new repository record
                new_repo = Repository.create_from_github(current_user.id, github_repo)
                db.add(new_repo)
                db.flush()
                synced_repos.append(new_repo.to_dict())
        
        db.commit()
        
        return {
            "repositories": synced_repos,
            "total": len(synced_repos),
            "synced_from_github": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch GitHub repositories: {str(e)}")


@router.get("/{repository_id}")
async def get_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get a specific repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo_dict = repository.to_dict()
    
    # Include entity information if exists
    if repository.entity:
        repo_dict["entity"] = repository.entity.to_dict()
    
    return repo_dict


@router.post("/{repository_id}/entity")
async def create_entity_for_repository(
    repository_id: int,
    request: CreateEntityRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Create an entity for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Check if entity already exists
    if repository.entity:
        raise HTTPException(status_code=400, detail="Entity already exists for this repository")
    
    try:
        entity = await entity_service.create_entity(
            db, repository, request.entity_type, request.name
        )
        
        return {
            "message": "Entity created successfully",
            "entity": entity.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create entity: {str(e)}")


@router.post("/{repository_id}/monitoring/enable")
async def enable_repository_monitoring(
    repository_id: int,
    request: EnableMonitoringRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Enable monitoring for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if not repository.entity:
        raise HTTPException(status_code=400, detail="Repository must have an entity before enabling monitoring")
    
    # Enable monitoring
    repository.enable_monitoring()
    
    webhook_result = None
    if request.enable_webhook:
        # Set up webhook
        webhook_url = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/webhook/github"
        webhook_secret = os.getenv('WEBHOOK_SECRET', 'default_secret')
        
        webhook_result = await webhook_service.setup_repository_webhook(
            db, repository, webhook_url, webhook_secret
        )
    
    db.commit()
    
    return {
        "message": "Monitoring enabled successfully",
        "repository": repository.to_dict(),
        "webhook": webhook_result
    }


@router.post("/{repository_id}/monitoring/disable")
async def disable_repository_monitoring(
    repository_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Disable monitoring for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Remove webhook if exists
    webhook_result = None
    if repository.webhook_id:
        webhook_result = await webhook_service.remove_repository_webhook(db, repository)
    
    # Disable monitoring
    repository.disable_monitoring()
    db.commit()
    
    return {
        "message": "Monitoring disabled successfully",
        "repository": repository.to_dict(),
        "webhook_removal": webhook_result
    }


@router.get("/{repository_id}/commits")
async def get_repository_commits(
    repository_id: int,
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get recent commits for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        access_token = current_user.decrypt_token()
        commits = await github_service.get_repository_commits(
            access_token, repository.full_name, per_page=limit
        )
        
        return {
            "commits": commits,
            "total": len(commits),
            "repository": repository.full_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch commits: {str(e)}")


@router.get("/{repository_id}/analysis")
async def get_repository_analysis(
    repository_id: int,
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get analysis summary for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    from services.analysis_service import AnalysisService
    analysis_service = AnalysisService()
    
    trend_data = analysis_service.get_repository_quality_trend(
        db, repository_id, days
    )
    
    return {
        "repository_id": repository_id,
        "analysis_period_days": days,
        "trend_data": trend_data
    }


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete a repository and its associated data."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Remove webhook if exists
    if repository.webhook_id:
        try:
            await webhook_service.remove_repository_webhook(db, repository)
        except Exception as e:
            print(f"Warning: Failed to remove webhook: {e}")
    
    # Delete repository (cascade will handle entity and analyses)
    db.delete(repository)
    db.commit()
    
    return {"message": "Repository deleted successfully"}