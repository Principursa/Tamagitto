"""AI-powered analysis API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.repository import Repository
from agents.code_analysis_agent import CodeAnalysisAgent
from services.github_service import GitHubService
from routers.auth import get_current_user_dependency

router = APIRouter(prefix="/ai", tags=["ai-analysis"])


class AnalyzeCommitRequest(BaseModel):
    repository_id: int
    commit_sha: str


class AnalyzeCodeRequest(BaseModel):
    code_snippet: str
    language: str
    context: Optional[str] = None


@router.post("/analyze-commit")
async def analyze_commit_with_ai(
    request: AnalyzeCommitRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Analyze a specific commit using AI for detailed insights."""
    repository = db.query(Repository).filter(
        Repository.id == request.repository_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    try:
        # Initialize services
        ai_agent = CodeAnalysisAgent()
        github_service = GitHubService()
        
        # Get commit details from GitHub
        access_token = current_user.decrypt_token()
        commit_data = await github_service.get_commit_details(
            access_token, repository.full_name, request.commit_sha
        )
        
        # Prepare repository context
        repository_context = {
            "name": repository.full_name,
            "language": repository.language,
            "type": "repository"
        }
        
        # Perform AI analysis
        ai_analysis = await ai_agent.analyze_commit_quality(commit_data, repository_context)
        
        # Get health impact suggestion
        commit_metrics = github_service.extract_commit_metrics(commit_data)
        health_impact = await ai_agent.suggest_health_impact(
            ai_analysis, 
            {"commit_metrics": commit_metrics, "repository": repository_context}
        )
        
        return {
            "commit_sha": request.commit_sha,
            "repository": repository.full_name,
            "ai_analysis": ai_analysis,
            "suggested_health_impact": health_impact,
            "commit_metrics": commit_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AI analysis failed: {str(e)}")


@router.post("/analyze-message")
async def analyze_commit_message_with_ai(
    message: str,
    additions: int = 0,
    deletions: int = 0,
    files_changed: int = 0
):
    """Analyze a commit message using AI for quality assessment."""
    try:
        ai_agent = CodeAnalysisAgent()
        
        context = {
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions
        }
        
        analysis = await ai_agent.analyze_commit_message(message, context)
        
        return {
            "message": message,
            "analysis": analysis,
            "context": context
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Message analysis failed: {str(e)}")


@router.post("/analyze-code")
async def analyze_code_snippet_with_ai(
    request: AnalyzeCodeRequest
):
    """Analyze a code snippet using AI for quality insights."""
    try:
        ai_agent = CodeAnalysisAgent()
        
        # Create a mock file structure for analysis
        mock_files = [{
            "filename": f"snippet.{request.language}",
            "additions": len(request.code_snippet.split('\n')),
            "deletions": 0,
            "changes": len(request.code_snippet.split('\n')),
            "patch": request.code_snippet,
            "status": "added"
        }]
        
        analysis = await ai_agent.analyze_code_changes(mock_files, request.language)
        
        return {
            "code_snippet": request.code_snippet[:200] + "..." if len(request.code_snippet) > 200 else request.code_snippet,
            "language": request.language,
            "analysis": analysis,
            "context": request.context
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Code analysis failed: {str(e)}")


@router.get("/capabilities")
async def get_ai_capabilities():
    """Get information about AI analysis capabilities."""
    try:
        ai_agent = CodeAnalysisAgent()
        return {
            "ai_enabled": True,
            "model": "gemini-1.5-flash",
            "capabilities": [
                "Commit quality analysis",
                "Code review and best practices",
                "Commit message evaluation",
                "Security vulnerability detection",
                "Performance impact assessment",
                "Health impact calculation",
                "Documentation quality check",
                "Test coverage analysis"
            ],
            "supported_languages": [
                "Python", "JavaScript", "TypeScript", "Java", "Go", 
                "Rust", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin"
            ],
            "analysis_dimensions": [
                "Code Quality",
                "Best Practices",
                "Testing",
                "Documentation", 
                "Security",
                "Performance",
                "Commit Message Quality"
            ]
        }
    except Exception as e:
        return {
            "ai_enabled": False,
            "error": str(e),
            "fallback_mode": "Basic rule-based analysis"
        }


@router.get("/health")
async def get_ai_health():
    """Check AI service health and performance."""
    try:
        ai_agent = CodeAnalysisAgent()
        
        # Simple test to verify AI is working
        test_analysis = await ai_agent.analyze_commit_message(
            "feat: add AI-powered code analysis", 
            {"files_changed": 1, "additions": 100, "deletions": 0}
        )
        
        return {
            "status": "healthy",
            "ai_responsive": True,
            "test_analysis_score": test_analysis.get("score", 0),
            "message": "AI analysis service is operational"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ai_responsive": False,
            "error": str(e),
            "message": "AI analysis service is not available"
        }