"""Commit analysis API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.repository import Repository
from models.commit_analysis import CommitAnalysis
from services.analysis_service import AnalysisService
from services.github_service import GitHubService
from routers.auth import get_current_user_dependency

router = APIRouter(prefix="/analysis", tags=["analysis"])
analysis_service = AnalysisService()
github_service = GitHubService()


class AnalyzeCommitsRequest(BaseModel):
    repository_id: int
    commit_shas: Optional[List[str]] = None
    since_date: Optional[str] = None
    limit: int = 10


@router.get("/repository/{repository_id}")
async def get_repository_analyses(
    repository_id: int,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get commit analyses for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    analyses = db.query(CommitAnalysis).filter(
        CommitAnalysis.repository_id == repository_id
    ).order_by(CommitAnalysis.commit_date.desc()).limit(limit).all()
    
    return {
        "repository_id": repository_id,
        "repository": repository.full_name,
        "analyses": [analysis.to_dict() for analysis in analyses],
        "total": len(analyses)
    }


@router.get("/repository/{repository_id}/trends")
async def get_repository_trends(
    repository_id: int,
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get quality trends for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    trend_data = analysis_service.get_repository_quality_trend(
        db, repository_id, days
    )
    
    return {
        "repository_id": repository_id,
        "repository": repository.full_name,
        "period_days": days,
        "trends": trend_data
    }


@router.get("/commit/{commit_sha}")
async def get_commit_analysis(
    commit_sha: str,
    repository_id: int = Query(...),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get analysis for a specific commit."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    analysis = db.query(CommitAnalysis).filter(
        CommitAnalysis.commit_sha == commit_sha,
        CommitAnalysis.repository_id == repository_id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Commit analysis not found")
    
    return analysis.to_dict()


@router.post("/analyze")
async def analyze_commits(
    request: AnalyzeCommitsRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Manually trigger commit analysis for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == request.repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        access_token = current_user.decrypt_token()
        
        if request.commit_shas:
            # Analyze specific commits
            commits_to_analyze = []
            for sha in request.commit_shas:
                commit_data = await github_service.get_commit_details(
                    access_token, repository.full_name, sha
                )
                commits_to_analyze.append(commit_data)
        else:
            # Get recent commits
            since_date = None
            if request.since_date:
                try:
                    since_date = datetime.fromisoformat(request.since_date.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid since_date format")
            
            commits_to_analyze = await github_service.get_repository_commits(
                access_token, repository.full_name, 
                since=since_date, per_page=request.limit
            )
        
        # Analyze commits
        analyses = await analysis_service.batch_analyze_commits(
            db, repository, commits_to_analyze, access_token
        )
        
        return {
            "message": "Commits analyzed successfully",
            "repository": repository.full_name,
            "analyses_created": len(analyses),
            "analyses": [analysis.to_dict() for analysis in analyses]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")


@router.get("/quality-distribution")
async def get_quality_distribution(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get quality score distribution for user's repositories."""
    # Get user's repositories
    repositories = db.query(Repository).filter(Repository.user_id == current_user.id).all()
    repository_ids = [repo.id for repo in repositories]
    
    if not repository_ids:
        return {
            "distribution": {"excellent": 0, "good": 0, "average": 0, "poor": 0, "terrible": 0},
            "total_commits": 0,
            "period_days": days
        }
    
    # Get recent analyses
    since_date = datetime.utcnow() - timedelta(days=days)
    analyses = db.query(CommitAnalysis).filter(
        CommitAnalysis.repository_id.in_(repository_ids),
        CommitAnalysis.created_at >= since_date
    ).all()
    
    # Calculate distribution
    quality_scores = [analysis.quality_score for analysis in analyses]
    distribution = analysis_service._calculate_quality_distribution(quality_scores)
    
    return {
        "distribution": distribution,
        "total_commits": len(analyses),
        "period_days": days,
        "repositories_analyzed": len(repository_ids)
    }


@router.get("/leaderboard")
async def get_quality_leaderboard(
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get quality leaderboard for user's repositories."""
    # Get user's repositories
    repositories = db.query(Repository).filter(Repository.user_id == current_user.id).all()
    
    leaderboard = []
    since_date = datetime.utcnow() - timedelta(days=days)
    
    for repository in repositories:
        analyses = db.query(CommitAnalysis).filter(
            CommitAnalysis.repository_id == repository.id,
            CommitAnalysis.created_at >= since_date
        ).all()
        
        if analyses:
            avg_quality = sum(a.quality_score for a in analyses) / len(analyses)
            avg_health_impact = sum(a.health_impact for a in analyses) / len(analyses)
            
            leaderboard.append({
                "repository": repository.to_dict(),
                "avg_quality_score": round(avg_quality, 2),
                "avg_health_impact": round(avg_health_impact, 2),
                "commit_count": len(analyses),
                "best_commit": max(analyses, key=lambda x: x.quality_score).to_dict(),
            })
    
    # Sort by average quality score
    leaderboard.sort(key=lambda x: x["avg_quality_score"], reverse=True)
    
    return {
        "leaderboard": leaderboard,
        "period_days": days,
        "total_repositories": len(leaderboard)
    }


@router.delete("/repository/{repository_id}")
async def delete_repository_analyses(
    repository_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete all analyses for a repository."""
    repository = db.query(Repository).filter(
        Repository.id == repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Count and delete analyses
    analyses = db.query(CommitAnalysis).filter(
        CommitAnalysis.repository_id == repository_id
    ).all()
    
    deleted_count = len(analyses)
    for analysis in analyses:
        db.delete(analysis)
    
    db.commit()
    
    return {
        "message": "Analyses deleted successfully",
        "repository": repository.full_name,
        "deleted_count": deleted_count
    }