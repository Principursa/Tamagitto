"""Commit analysis service using AI agents for code quality assessment."""

import os
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from models.commit_analysis import CommitAnalysis
from models.repository import Repository
from services.github_service import GitHubService
from agents.code_analysis_agent import CodeAnalysisAgent


class AnalysisService:
    """Service for analyzing commits and calculating health impact using AI agents."""
    
    # Quality scoring weights (used for fallback analysis)
    QUALITY_WEIGHTS = {
        "commit_message": 0.15,
        "code_changes": 0.30,
        "test_coverage": 0.20,
        "documentation": 0.10,
        "best_practices": 0.15,
        "consistency": 0.10
    }
    
    # Health impact ranges (used for fallback analysis)
    HEALTH_IMPACT_RANGES = {
        "excellent": (15, 20),    # 90-100 quality score
        "good": (5, 15),          # 70-89 quality score  
        "average": (-2, 5),       # 50-69 quality score
        "poor": (-10, -2),        # 30-49 quality score
        "terrible": (-20, -10)    # 0-29 quality score
    }
    
    def __init__(self):
        self.github_service = GitHubService()
        
        # Initialize AI agent for enhanced analysis
        try:
            self.ai_agent = CodeAnalysisAgent()
            self.ai_enabled = True
            print("AI analysis agent initialized successfully")
        except Exception as e:
            print(f"Failed to initialize AI agent, falling back to basic analysis: {e}")
            self.ai_agent = None
            self.ai_enabled = False
    
    async def analyze_commit(self, db: Session, repository: Repository, 
                           commit_data: Dict[str, Any], 
                           access_token: str) -> CommitAnalysis:
        """
        Analyze a single commit and calculate its health impact.
        
        Args:
            db: Database session
            repository: Repository the commit belongs to
            commit_data: Commit data from GitHub API
            access_token: GitHub access token for detailed analysis
            
        Returns:
            Created CommitAnalysis object
        """
        # Extract basic metrics
        metrics = self.github_service.extract_commit_metrics(commit_data)
        
        # Get detailed commit information if needed
        if "files" not in commit_data or len(commit_data.get("files", [])) == 0:
            detailed_commit = await self.github_service.get_commit_details(
                access_token, repository.full_name, metrics["sha"]
            )
            commit_data.update(detailed_commit)
            metrics = self.github_service.extract_commit_metrics(commit_data)
        
        # Prepare repository context for AI analysis
        repository_context = {
            "name": repository.full_name,
            "language": repository.language,
            "type": "repository"
        }
        
        # Perform AI-powered analysis if available
        if self.ai_enabled and self.ai_agent:
            try:
                ai_analysis = await self.ai_agent.analyze_commit_quality(
                    commit_data, repository_context
                )
                quality_score = ai_analysis.get("overall_quality_score", 60)
                
                # Get AI-suggested health impact
                health_impact = await self.ai_agent.suggest_health_impact(
                    ai_analysis, {"commit_metrics": metrics, "repository": repository_context}
                )
                
                # Store AI analysis results
                quality_scores = ai_analysis.get("dimension_scores", {})
                
            except Exception as e:
                print(f"AI analysis failed, falling back to basic analysis: {e}")
                # Fallback to basic analysis
                quality_scores = await self._analyze_commit_quality(commit_data, repository)
                quality_score = self._calculate_quality_score(quality_scores)
                health_impact = self._calculate_health_impact(quality_score, metrics)
        else:
            # Use basic analysis
            quality_scores = await self._analyze_commit_quality(commit_data, repository)
            quality_score = self._calculate_quality_score(quality_scores)
            health_impact = self._calculate_health_impact(quality_score, metrics)
        
        # Create analysis record
        analysis = CommitAnalysis(
            repository_id=repository.id,
            commit_sha=metrics["sha"],
            commit_message=metrics["message"],
            author_name=metrics["author_name"],
            author_email=metrics["author_email"],
            commit_date=metrics["commit_date"],
            additions=metrics["additions"],
            deletions=metrics["deletions"],
            files_changed=metrics["changed_files"],
            quality_score=quality_score,
            health_impact=health_impact,
            analysis_data={
                "metrics": metrics,
                "quality_breakdown": quality_scores,
                "files_modified": metrics["files_modified"],
                "ai_analysis": ai_analysis if self.ai_enabled and 'ai_analysis' in locals() else None,
                "analysis_method": "ai_powered" if self.ai_enabled and 'ai_analysis' in locals() else "basic"
            }
        )
        
        db.add(analysis)
        db.commit()
        return analysis
    
    async def batch_analyze_commits(self, db: Session, repository: Repository,
                                  commits: List[Dict[str, Any]], 
                                  access_token: str) -> List[CommitAnalysis]:
        """
        Analyze multiple commits in batch for efficiency.
        
        Args:
            db: Database session
            repository: Repository the commits belong to
            commits: List of commit data from GitHub API
            access_token: GitHub access token
            
        Returns:
            List of created CommitAnalysis objects
        """
        analyses = []
        
        # Process commits in smaller batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i + batch_size]
            batch_tasks = [
                self.analyze_commit(db, repository, commit, access_token)
                for commit in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    # Log error but continue with other commits
                    print(f"Error analyzing commit: {result}")
                else:
                    analyses.append(result)
            
            # Small delay between batches to be respectful to APIs
            await asyncio.sleep(0.5)
        
        return analyses
    
    def get_repository_quality_trend(self, db: Session, repository_id: int, 
                                   days: int = 30) -> Dict[str, Any]:
        """
        Calculate quality trends for a repository over time.
        
        Args:
            db: Database session
            repository_id: Repository ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with quality trend analysis
        """
        # Get recent analyses
        since_date = datetime.utcnow() - timedelta(days=days)
        analyses = db.query(CommitAnalysis).filter(
            CommitAnalysis.repository_id == repository_id,
            CommitAnalysis.created_at >= since_date
        ).order_by(CommitAnalysis.commit_date.desc()).all()
        
        if not analyses:
            return {"trend": "no_data", "commit_count": 0}
        
        # Calculate trend
        quality_scores = [a.quality_score for a in analyses]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        # Split into two halves to compare trend
        mid_point = len(quality_scores) // 2
        if mid_point > 0:
            recent_avg = sum(quality_scores[:mid_point]) / mid_point
            older_avg = sum(quality_scores[mid_point:]) / (len(quality_scores) - mid_point)
            trend = "improving" if recent_avg > older_avg + 5 else "declining" if recent_avg < older_avg - 5 else "stable"
        else:
            trend = "stable"
        
        # Calculate other metrics
        health_impacts = [a.health_impact for a in analyses]
        avg_health_impact = sum(health_impacts) / len(health_impacts)
        
        return {
            "trend": trend,
            "commit_count": len(analyses),
            "avg_quality_score": round(avg_quality, 2),
            "avg_health_impact": round(avg_health_impact, 2),
            "best_commit": max(analyses, key=lambda x: x.quality_score).to_dict(),
            "worst_commit": min(analyses, key=lambda x: x.quality_score).to_dict(),
            "quality_distribution": self._calculate_quality_distribution(quality_scores)
        }
    
    async def _analyze_commit_quality(self, commit_data: Dict[str, Any], 
                                    repository: Repository) -> Dict[str, float]:
        """
        Analyze various aspects of commit quality.
        
        Args:
            commit_data: Commit data with files and changes
            repository: Repository context
            
        Returns:
            Dictionary of quality scores for different aspects
        """
        scores = {}
        
        # 1. Commit Message Quality (0-100)
        scores["commit_message"] = self._analyze_commit_message(
            commit_data.get("commit", {}).get("message", "")
        )
        
        # 2. Code Changes Quality (0-100)
        scores["code_changes"] = await self._analyze_code_changes(
            commit_data.get("files", []), repository
        )
        
        # 3. Test Coverage Impact (0-100)
        scores["test_coverage"] = self._analyze_test_coverage(
            commit_data.get("files", [])
        )
        
        # 4. Documentation Updates (0-100)
        scores["documentation"] = self._analyze_documentation(
            commit_data.get("files", [])
        )
        
        # 5. Best Practices Compliance (0-100)
        scores["best_practices"] = self._analyze_best_practices(
            commit_data, repository
        )
        
        # 6. Consistency with Repository (0-100)
        scores["consistency"] = self._analyze_consistency(
            commit_data, repository
        )
        
        return scores
    
    def _analyze_commit_message(self, message: str) -> float:
        """Analyze commit message quality."""
        if not message:
            return 0.0
        
        score = 50.0  # Base score
        
        # Length check (50-72 characters for first line is ideal)
        lines = message.split('\n')
        first_line = lines[0].strip()
        
        if 10 <= len(first_line) <= 72:
            score += 15
        elif len(first_line) < 10:
            score -= 20
        elif len(first_line) > 72:
            score -= 10
        
        # Conventional commit format check
        conventional_patterns = [
            r'^feat(\(.+\))?: .+',
            r'^fix(\(.+\))?: .+',
            r'^docs(\(.+\))?: .+',
            r'^style(\(.+\))?: .+',
            r'^refactor(\(.+\))?: .+',
            r'^test(\(.+\))?: .+',
            r'^chore(\(.+\))?: .+',
        ]
        
        if any(re.match(pattern, first_line, re.IGNORECASE) for pattern in conventional_patterns):
            score += 20
        
        # Capitalization check
        if first_line and first_line[0].isupper():
            score += 5
        
        # No period at end of first line
        if first_line and not first_line.endswith('.'):
            score += 5
        
        # Has body (detailed description)
        if len(lines) > 2 and len('\n'.join(lines[2:]).strip()) > 20:
            score += 10
        
        # Avoid common bad practices
        bad_patterns = [
            r'^fix$',
            r'^update$',
            r'^changes$',
            r'^wip$',
            r'^tmp$',
        ]
        
        if any(re.match(pattern, first_line, re.IGNORECASE) for pattern in bad_patterns):
            score -= 30
        
        return max(0, min(100, score))
    
    async def _analyze_code_changes(self, files: List[Dict[str, Any]], 
                                  repository: Repository) -> float:
        """Analyze the quality of code changes."""
        if not files:
            return 50.0  # Neutral score for commits with no file changes
        
        score = 50.0
        
        # Size analysis
        total_changes = sum(file.get("changes", 0) for file in files)
        
        # Ideal commit size (50-200 lines changed)
        if 50 <= total_changes <= 200:
            score += 20
        elif total_changes < 50:
            score += 10
        elif total_changes > 500:
            score -= 20
        elif total_changes > 1000:
            score -= 40
        
        # File type analysis
        code_files = 0
        test_files = 0
        config_files = 0
        
        for file in files:
            filename = file.get("filename", "")
            if self._is_test_file(filename):
                test_files += 1
            elif self._is_config_file(filename):
                config_files += 1
            elif self._is_code_file(filename):
                code_files += 1
        
        # Good practices bonuses
        if test_files > 0 and code_files > 0:
            score += 15  # Tests updated with code
        
        if len(files) <= 10:
            score += 10  # Focused commit
        elif len(files) > 20:
            score -= 15  # Too many files changed
        
        # TODO: Use google-adk agent for deeper code analysis
        # This would analyze:
        # - Code complexity changes
        # - Potential bugs introduced
        # - Code style consistency
        # - Security implications
        
        return max(0, min(100, score))
    
    def _analyze_test_coverage(self, files: List[Dict[str, Any]]) -> float:
        """Analyze test coverage impact."""
        if not files:
            return 50.0
        
        test_files = sum(1 for f in files if self._is_test_file(f.get("filename", "")))
        code_files = sum(1 for f in files if self._is_code_file(f.get("filename", "")))
        
        if code_files == 0:
            return 50.0  # No code changes
        
        if test_files == 0:
            return 20.0  # Code changes without tests
        
        # Good test to code ratio
        test_ratio = test_files / max(code_files, 1)
        
        if test_ratio >= 1.0:
            return 90.0
        elif test_ratio >= 0.5:
            return 75.0
        elif test_ratio >= 0.25:
            return 60.0
        else:
            return 40.0
    
    def _analyze_documentation(self, files: List[Dict[str, Any]]) -> float:
        """Analyze documentation updates."""
        if not files:
            return 50.0
        
        doc_files = sum(1 for f in files if self._is_documentation_file(f.get("filename", "")))
        code_files = sum(1 for f in files if self._is_code_file(f.get("filename", "")))
        
        if code_files == 0:
            return 50.0  # No code changes
        
        if doc_files > 0:
            return 80.0  # Documentation updated
        
        # Check for README, changelog, or other important docs
        important_docs = ["README", "CHANGELOG", "CONTRIBUTING", "LICENSE"]
        has_important_docs = any(
            any(doc in f.get("filename", "").upper() for doc in important_docs)
            for f in files
        )
        
        return 70.0 if has_important_docs else 30.0
    
    def _analyze_best_practices(self, commit_data: Dict[str, Any], 
                              repository: Repository) -> float:
        """Analyze adherence to best practices."""
        score = 50.0
        
        stats = commit_data.get("stats", {})
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        
        # Good addition to deletion ratio (indicates refactoring)
        if deletions > 0:
            ratio = additions / deletions
            if 0.5 <= ratio <= 2.0:
                score += 15
        
        # Not too many additions without deletions (might indicate cleanup)
        if additions > 100 and deletions < 10:
            score -= 10
        
        # Check commit timing (avoid late night commits as they might be rushed)
        commit_date = commit_data.get("commit", {}).get("author", {}).get("date")
        if commit_date:
            try:
                dt = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                hour = dt.hour
                if 9 <= hour <= 17:  # Business hours
                    score += 5
                elif 22 <= hour or hour <= 6:  # Late night/early morning
                    score -= 5
            except:
                pass
        
        return max(0, min(100, score))
    
    def _analyze_consistency(self, commit_data: Dict[str, Any], 
                           repository: Repository) -> float:
        """Analyze consistency with repository patterns."""
        # This is a placeholder for consistency analysis
        # In a full implementation, this would:
        # - Compare with recent commits
        # - Check naming conventions
        # - Verify project structure consistency
        return 60.0  # Default neutral score
    
    def _calculate_quality_score(self, quality_scores: Dict[str, float]) -> int:
        """Calculate overall quality score from individual scores."""
        total_score = 0.0
        
        for aspect, weight in self.QUALITY_WEIGHTS.items():
            score = quality_scores.get(aspect, 50.0)
            total_score += score * weight
        
        return int(round(total_score))
    
    def _calculate_health_impact(self, quality_score: int, 
                               metrics: Dict[str, Any]) -> int:
        """Calculate health impact based on quality score."""
        # Determine impact range based on quality
        if quality_score >= 90:
            impact_range = self.HEALTH_IMPACT_RANGES["excellent"]
        elif quality_score >= 70:
            impact_range = self.HEALTH_IMPACT_RANGES["good"]
        elif quality_score >= 50:
            impact_range = self.HEALTH_IMPACT_RANGES["average"]
        elif quality_score >= 30:
            impact_range = self.HEALTH_IMPACT_RANGES["poor"]
        else:
            impact_range = self.HEALTH_IMPACT_RANGES["terrible"]
        
        # Adjust based on commit size (larger commits have more impact)
        base_impact = (impact_range[0] + impact_range[1]) / 2
        size_factor = min(1.5, max(0.5, metrics.get("total_changes", 50) / 100))
        
        final_impact = int(base_impact * size_factor)
        
        # Ensure impact stays within reasonable bounds
        return max(-20, min(20, final_impact))
    
    def _calculate_quality_distribution(self, scores: List[int]) -> Dict[str, int]:
        """Calculate distribution of quality scores."""
        distribution = {"excellent": 0, "good": 0, "average": 0, "poor": 0, "terrible": 0}
        
        for score in scores:
            if score >= 90:
                distribution["excellent"] += 1
            elif score >= 70:
                distribution["good"] += 1
            elif score >= 50:
                distribution["average"] += 1
            elif score >= 30:
                distribution["poor"] += 1
            else:
                distribution["terrible"] += 1
        
        return distribution
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file."""
        test_patterns = [
            r'test[s]?/',
            r'__test[s]?__/',
            r'spec/',
            r'\.test\.',
            r'\.spec\.',
            r'_test\.',
            r'_spec\.',
            r'Test\.java$',
            r'Tests\.java$',
        ]
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in test_patterns)
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file."""
        code_extensions = [
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj', '.hs',
            '.jsx', '.tsx', '.vue', '.svelte'
        ]
        return any(filename.lower().endswith(ext) for ext in code_extensions)
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file."""
        config_patterns = [
            r'\.json$',
            r'\.yaml$',
            r'\.yml$',
            r'\.toml$',
            r'\.ini$',
            r'\.cfg$',
            r'\.conf$',
            r'\.config$',
            r'package\.json$',
            r'requirements\.txt$',
            r'Dockerfile',
            r'docker-compose',
        ]
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in config_patterns)
    
    def _is_documentation_file(self, filename: str) -> bool:
        """Check if file is documentation."""
        doc_patterns = [
            r'\.md$',
            r'\.rst$',
            r'\.txt$',
            r'README',
            r'CHANGELOG',
            r'CONTRIBUTING',
            r'LICENSE',
            r'docs/',
        ]
        return any(re.search(pattern, filename, re.IGNORECASE) for pattern in doc_patterns)