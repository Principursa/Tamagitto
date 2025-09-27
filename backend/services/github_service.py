"""GitHub API service for repository and commit operations."""

import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from models.user import User
from models.repository import Repository


class GitHubService:
    """Service for interacting with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError("GitHub client credentials not configured")
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from GitHub OAuth flow
            
        Returns:
            Dictionary containing access token and user info
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"}
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Failed to get access token from GitHub")
            
            # Get user information
            user_response = await client.get(
                f"{self.BASE_URL}/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            user_data = user_response.json()
            
            return {
                "access_token": access_token,
                "user": user_data
            }
    
    async def get_user_repositories(self, access_token: str, 
                                  per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get user's repositories from GitHub.
        
        Args:
            access_token: GitHub access token
            per_page: Number of repositories per page
            
        Returns:
            List of repository dictionaries
        """
        repositories = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.BASE_URL}/user/repos",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "type": "owner"  # Only repos owned by user
                    },
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                page_repos = response.json()
                
                if not page_repos:
                    break
                    
                repositories.extend(page_repos)
                page += 1
                
                # GitHub API pagination limit safety
                if page > 10:  # Max 1000 repos
                    break
        
        return repositories
    
    async def get_repository_commits(self, access_token: str, full_name: str, 
                                   since: Optional[datetime] = None,
                                   per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Get commits from a repository.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            since: Only commits after this date
            per_page: Number of commits per page
            
        Returns:
            List of commit dictionaries
        """
        commits = []
        page = 1
        
        params = {
            "per_page": per_page,
            "page": page
        }
        
        if since:
            params["since"] = since.isoformat()
        
        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{full_name}/commits",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                page_commits = response.json()
                
                if not page_commits:
                    break
                    
                commits.extend(page_commits)
                page += 1
                params["page"] = page
                
                # Limit to recent commits for performance
                if page > 5 or len(commits) >= 500:
                    break
        
        return commits
    
    async def get_commit_details(self, access_token: str, full_name: str, 
                               sha: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific commit.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            sha: Commit SHA
            
        Returns:
            Detailed commit information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{full_name}/commits/{sha}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def create_webhook(self, access_token: str, full_name: str, 
                           webhook_url: str) -> Dict[str, Any]:
        """
        Create a webhook for repository events.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            webhook_url: URL to receive webhook events
            
        Returns:
            Webhook configuration
        """
        webhook_config = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "insecure_ssl": "0"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{full_name}/hooks",
                json=webhook_config,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_webhook(self, access_token: str, full_name: str, 
                           webhook_id: str) -> bool:
        """
        Delete a repository webhook.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            webhook_id: Webhook ID to delete
            
        Returns:
            True if successful
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/repos/{full_name}/hooks/{webhook_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return True
    
    async def verify_repository_access(self, access_token: str, 
                                     full_name: str) -> bool:
        """
        Verify that the user has access to a repository.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            
        Returns:
            True if user has access
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{full_name}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False
    
    async def get_repository_languages(self, access_token: str, 
                                     full_name: str) -> Dict[str, int]:
        """
        Get programming languages used in repository.
        
        Args:
            access_token: GitHub access token
            full_name: Repository full name (owner/repo)
            
        Returns:
            Dictionary of languages and their byte counts
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{full_name}/languages",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    def extract_commit_metrics(self, commit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract useful metrics from GitHub commit data.
        
        Args:
            commit_data: Commit data from GitHub API
            
        Returns:
            Dictionary of extracted metrics
        """
        commit = commit_data.get("commit", {})
        stats = commit_data.get("stats", {})
        files = commit_data.get("files", [])
        
        # Calculate basic metrics
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        total_changes = additions + deletions
        changed_files = len(files)
        
        # Extract commit message
        message = commit.get("message", "")
        message_lines = message.split('\n')
        title = message_lines[0] if message_lines else ""
        
        # Check for conventional commit format
        conventional_prefixes = ['feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:']
        has_conventional_format = any(title.lower().startswith(prefix) for prefix in conventional_prefixes)
        
        # Extract author info
        author = commit.get("author", {})
        commit_date = author.get("date")
        if commit_date:
            commit_date = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
        
        return {
            "sha": commit_data.get("sha"),
            "message": message,
            "title": title,
            "author_name": author.get("name"),
            "author_email": author.get("email"),
            "commit_date": commit_date,
            "additions": additions,
            "deletions": deletions,
            "total_changes": total_changes,
            "changed_files": changed_files,
            "has_conventional_format": has_conventional_format,
            "message_length": len(message),
            "files_modified": [f.get("filename") for f in files],
        }