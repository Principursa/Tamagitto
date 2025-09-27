"""Webhook service for handling GitHub webhook events."""

import hmac
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.repository import Repository
from models.user import User
from services.github_service import GitHubService
from services.analysis_service import AnalysisService
from services.entity_service import EntityService


class WebhookService:
    """Service for handling GitHub webhook events and processing them."""
    
    def __init__(self):
        self.github_service = GitHubService()
        self.analysis_service = AnalysisService()
        self.entity_service = EntityService()
    
    def verify_github_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify GitHub webhook signature.
        
        Args:
            payload: Raw request payload
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        if not signature.startswith('sha256='):
            return False
        
        expected_signature = 'sha256=' + hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def process_webhook_event(self, db: Session, event_type: str, 
                                  payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming GitHub webhook event.
        
        Args:
            db: Database session
            event_type: GitHub event type (e.g., 'push')
            payload: Webhook payload
            
        Returns:
            Processing result dictionary
        """
        try:
            if event_type == 'push':
                return await self._handle_push_event(db, payload)
            elif event_type == 'ping':
                return self._handle_ping_event(payload)
            else:
                return {
                    "success": False,
                    "message": f"Unsupported event type: {event_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing webhook: {str(e)}"
            }
    
    async def _handle_push_event(self, db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitHub push event.
        
        Args:
            db: Database session
            payload: Push event payload
            
        Returns:
            Processing result
        """
        # Extract repository information
        repo_data = payload.get('repository', {})
        repo_full_name = repo_data.get('full_name')
        repo_github_id = repo_data.get('id')
        
        if not repo_full_name or not repo_github_id:
            return {"success": False, "message": "Missing repository information"}
        
        # Find repository in our database
        repository = db.query(Repository).filter(
            Repository.github_repo_id == repo_github_id
        ).first()
        
        if not repository:
            return {
                "success": False,
                "message": f"Repository {repo_full_name} not found in database"
            }
        
        if not repository.monitoring_active:
            return {
                "success": False,
                "message": f"Monitoring not active for {repo_full_name}"
            }
        
        # Get user and access token
        user = db.query(User).filter(User.id == repository.user_id).first()
        if not user:
            return {"success": False, "message": "Repository owner not found"}
        
        try:
            access_token = user.decrypt_token()
        except Exception as e:
            return {"success": False, "message": f"Failed to decrypt access token: {e}"}
        
        # Extract commits from payload
        commits = payload.get('commits', [])
        if not commits:
            return {"success": True, "message": "No commits to process"}
        
        # Filter out merge commits and commits by non-repository owner
        filtered_commits = []
        for commit in commits:
            # Skip merge commits
            if len(commit.get('parents', [])) > 1:
                continue
            
            # Skip commits by other users (for now, only process repo owner's commits)
            commit_author = commit.get('author', {})
            if commit_author.get('username') != user.username:
                continue
            
            filtered_commits.append(commit)
        
        if not filtered_commits:
            return {"success": True, "message": "No relevant commits to process"}
        
        # Get detailed commit information from GitHub API
        detailed_commits = []
        for commit in filtered_commits:
            try:
                detailed_commit = await self.github_service.get_commit_details(
                    access_token, repo_full_name, commit['id']
                )
                detailed_commits.append(detailed_commit)
            except Exception as e:
                print(f"Failed to get details for commit {commit['id']}: {e}")
                continue
        
        # Analyze commits
        analyses = await self.analysis_service.batch_analyze_commits(
            db, repository, detailed_commits, access_token
        )
        
        # Apply health impacts to entity
        entity = repository.entity
        if not entity:
            return {
                "success": False,
                "message": "No entity found for repository"
            }
        
        entity_updates = []
        for analysis in analyses:
            update_result = self.entity_service.apply_commit_impact(
                db, entity, analysis
            )
            entity_updates.append({
                "commit_sha": analysis.commit_sha,
                "quality_score": analysis.quality_score,
                "health_impact": analysis.health_impact,
                "update_result": update_result
            })
        
        # Update repository monitoring info
        repository.update_last_monitored()
        if commits:
            latest_commit = max(commits, key=lambda x: x.get('timestamp', ''))
            repository.last_commit_sha = latest_commit.get('id')
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Processed {len(analyses)} commits",
            "repository": repo_full_name,
            "entity_health": entity.health_score,
            "entity_status": entity.status,
            "commits_processed": len(analyses),
            "entity_updates": entity_updates
        }
    
    def _handle_ping_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitHub ping event (webhook verification).
        
        Args:
            payload: Ping event payload
            
        Returns:
            Ping response
        """
        return {
            "success": True,
            "message": "Webhook ping received",
            "zen": payload.get('zen', 'GitHub is awesome!'),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def setup_repository_webhook(self, db: Session, repository: Repository, 
                                     webhook_url: str, webhook_secret: str) -> Dict[str, Any]:
        """
        Set up webhook for a repository.
        
        Args:
            db: Database session
            repository: Repository to set up webhook for
            webhook_url: URL for webhook events
            webhook_secret: Secret for webhook verification
            
        Returns:
            Setup result
        """
        # Get user and access token
        user = db.query(User).filter(User.id == repository.user_id).first()
        if not user:
            return {"success": False, "message": "Repository owner not found"}
        
        try:
            access_token = user.decrypt_token()
        except Exception as e:
            return {"success": False, "message": f"Failed to decrypt access token: {e}"}
        
        try:
            # Create webhook on GitHub
            webhook_data = await self.github_service.create_webhook(
                access_token, repository.full_name, webhook_url
            )
            
            # Update repository with webhook ID
            repository.set_webhook(str(webhook_data.get('id')))
            db.commit()
            
            return {
                "success": True,
                "message": "Webhook created successfully",
                "webhook_id": webhook_data.get('id'),
                "webhook_url": webhook_data.get('config', {}).get('url')
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create webhook: {str(e)}"
            }
    
    async def remove_repository_webhook(self, db: Session, repository: Repository) -> Dict[str, Any]:
        """
        Remove webhook for a repository.
        
        Args:
            db: Database session
            repository: Repository to remove webhook from
            
        Returns:
            Removal result
        """
        if not repository.webhook_id:
            return {"success": False, "message": "No webhook configured"}
        
        # Get user and access token
        user = db.query(User).filter(User.id == repository.user_id).first()
        if not user:
            return {"success": False, "message": "Repository owner not found"}
        
        try:
            access_token = user.decrypt_token()
        except Exception as e:
            return {"success": False, "message": f"Failed to decrypt access token: {e}"}
        
        try:
            # Delete webhook from GitHub
            await self.github_service.delete_webhook(
                access_token, repository.full_name, repository.webhook_id
            )
            
            # Remove webhook ID from repository
            repository.remove_webhook()
            db.commit()
            
            return {
                "success": True,
                "message": "Webhook removed successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to remove webhook: {str(e)}"
            }
    
    def get_webhook_delivery_status(self, db: Session, repository_id: int, 
                                  limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent webhook delivery status for a repository.
        
        Args:
            db: Database session
            repository_id: Repository ID
            limit: Maximum number of deliveries to return
            
        Returns:
            List of webhook delivery information
        """
        # This would query webhook delivery logs if we stored them
        # For now, return placeholder data showing the structure
        return [
            {
                "id": "12345",
                "event": "push",
                "delivered_at": datetime.utcnow().isoformat(),
                "status": "success",
                "response_code": 200,
                "duration": 1.2,
                "redelivery": False
            }
        ]
    
    async def test_webhook_connectivity(self, webhook_url: str) -> Dict[str, Any]:
        """
        Test if webhook URL is reachable.
        
        Args:
            webhook_url: URL to test
            
        Returns:
            Connectivity test result
        """
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                # Send a test POST request
                test_payload = {
                    "test": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                response = await client.post(
                    webhook_url,
                    json=test_payload,
                    timeout=10.0
                )
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "reachable": True
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reachable": False
            }
    
    def validate_webhook_payload(self, payload: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """
        Validate webhook payload structure.
        
        Args:
            payload: Webhook payload to validate
            event_type: Expected event type
            
        Returns:
            Validation result
        """
        errors = []
        
        if event_type == 'push':
            required_fields = ['repository', 'commits', 'pusher']
            for field in required_fields:
                if field not in payload:
                    errors.append(f"Missing required field: {field}")
            
            if 'repository' in payload:
                repo = payload['repository']
                repo_required = ['id', 'full_name', 'name']
                for field in repo_required:
                    if field not in repo:
                        errors.append(f"Missing repository field: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }