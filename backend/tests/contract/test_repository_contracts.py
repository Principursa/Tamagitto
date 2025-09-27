"""Contract tests for repository management endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestRepositoryManagementContracts:
    """Test repository management endpoint contracts."""

    def test_get_repositories_success(self):
        """Test GET /repositories success response."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}

        # Mock GitHub API response
        with patch('backend.services.github_service.get_user_repositories') as mock_repos:
            mock_repos.return_value = [
                {
                    "id": 123456789,
                    "full_name": "developer123/awesome-project",
                    "private": False,
                    "language": "JavaScript",
                    "default_branch": "main",
                    "updated_at": "2025-09-27T10:30:00Z"
                },
                {
                    "id": 987654321,
                    "full_name": "developer123/python-app",
                    "private": True,
                    "language": "Python",
                    "default_branch": "main",
                    "updated_at": "2025-09-26T15:20:00Z"
                }
            ]

            # Act
            response = client.get("/api/repositories", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "repositories" in data
        assert "total_count" in data
        assert "has_more" in data
        
        # Verify repository objects
        repos = data["repositories"]
        assert len(repos) == 2
        
        repo = repos[0]
        assert "id" in repo
        assert "full_name" in repo
        assert "private" in repo
        assert "language" in repo
        assert "default_branch" in repo
        assert "updated_at" in repo
        assert "monitoring_enabled" in repo
        
        # Verify types
        assert isinstance(repo["id"], int)
        assert isinstance(repo["private"], bool)
        assert isinstance(repo["monitoring_enabled"], bool)

    def test_get_repositories_with_query_params(self):
        """Test GET /repositories with query parameters."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        params = {
            "type": "public",
            "sort": "updated",
            "per_page": 10
        }

        # Mock GitHub API response
        with patch('backend.services.github_service.get_user_repositories') as mock_repos:
            mock_repos.return_value = []

            # Act
            response = client.get("/api/repositories", headers=headers, params=params)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "repositories" in data

    def test_get_repositories_unauthorized(self):
        """Test GET /repositories without authentication."""
        # Arrange
        client = TestClient(app)

        # Act
        response = client.get("/api/repositories")

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_start_monitoring_repository_success(self):
        """Test POST /repositories/{github_repo_id}/monitor success."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        github_repo_id = 123456789
        request_data = {
            "entity_preferences": {
                "type": "pet",
                "name": "CodeBuddy"
            }
        }

        # Mock services
        with patch('backend.services.entity_service.create_entity') as mock_create, \
             patch('backend.services.github_service.get_repository') as mock_get_repo:
            
            mock_get_repo.return_value = {
                "id": github_repo_id,
                "full_name": "developer123/awesome-project",
                "language": "JavaScript"
            }
            
            mock_create.return_value = {
                "id": 1,
                "name": "CodeBuddy",
                "type": "pet",
                "health_score": 100,
                "status": "alive",
                "visual_url": "https://storage.tamagitto.xyz/entities/1/current.png",
                "created_at": "2025-09-27T14:30:00Z"
            }

            # Act
            response = client.post(
                f"/api/repositories/{github_repo_id}/monitor",
                headers=headers,
                json=request_data
            )

        # Assert
        assert response.status_code == 201
        data = response.json()
        
        # Verify required fields
        assert "repository" in data
        assert "entity" in data
        assert "message" in data
        
        # Verify repository object
        repo = data["repository"]
        assert "id" in repo
        assert "github_repo_id" in repo
        assert "full_name" in repo
        assert "monitoring_active" in repo
        assert repo["monitoring_active"] is True
        
        # Verify entity object
        entity = data["entity"]
        assert "id" in entity
        assert "name" in entity
        assert "type" in entity
        assert "health_score" in entity
        assert "status" in entity
        assert "visual_url" in entity
        assert entity["health_score"] == 100
        assert entity["status"] == "alive"

    def test_start_monitoring_repository_already_monitored(self):
        """Test POST /repositories/{github_repo_id}/monitor when already monitored."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        github_repo_id = 123456789
        request_data = {"entity_preferences": {}}

        # Mock service to return existing monitoring
        with patch('backend.services.repository_service.is_monitoring') as mock_is_monitoring:
            mock_is_monitoring.return_value = True

            # Act
            response = client.post(
                f"/api/repositories/{github_repo_id}/monitor",
                headers=headers,
                json=request_data
            )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_start_monitoring_repository_not_found(self):
        """Test POST /repositories/{github_repo_id}/monitor with non-existent repo."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        github_repo_id = 999999999
        request_data = {"entity_preferences": {}}

        # Mock GitHub service to return not found
        with patch('backend.services.github_service.get_repository') as mock_get_repo:
            mock_get_repo.return_value = None

            # Act
            response = client.post(
                f"/api/repositories/{github_repo_id}/monitor",
                headers=headers,
                json=request_data
            )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_stop_monitoring_repository_success(self):
        """Test DELETE /repositories/{github_repo_id}/monitor success."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        github_repo_id = 123456789

        # Mock service
        with patch('backend.services.repository_service.stop_monitoring') as mock_stop:
            mock_stop.return_value = True

            # Act
            response = client.delete(
                f"/api/repositories/{github_repo_id}/monitor",
                headers=headers
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "entity_archived" in data
        assert isinstance(data["entity_archived"], bool)

    def test_stop_monitoring_repository_not_monitored(self):
        """Test DELETE /repositories/{github_repo_id}/monitor when not monitored."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        github_repo_id = 123456789

        # Mock service to return not monitoring
        with patch('backend.services.repository_service.stop_monitoring') as mock_stop:
            mock_stop.return_value = False

            # Act
            response = client.delete(
                f"/api/repositories/{github_repo_id}/monitor",
                headers=headers
            )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "message" in data


class TestWebhookContracts:
    """Test webhook endpoint contracts."""

    def test_github_webhook_push_event(self):
        """Test POST /webhook/github with push event."""
        # Arrange
        client = TestClient(app)
        headers = {
            "X-GitHub-Event": "push",
            "X-GitHub-Signature-256": "sha256=test-signature"
        }
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "id": 123456789,
                "full_name": "developer123/awesome-project"
            },
            "commits": [
                {
                    "id": "abc123def456",
                    "message": "Fix authentication bug",
                    "author": {
                        "username": "developer123"
                    },
                    "timestamp": "2025-09-27T14:30:00Z",
                    "added": ["src/auth.py"],
                    "modified": ["src/utils.py"],
                    "removed": []
                }
            ]
        }

        # Mock webhook verification
        with patch('backend.services.webhook_service.verify_signature') as mock_verify:
            mock_verify.return_value = True

            # Act
            response = client.post("/api/webhook/github", headers=headers, json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "commits_queued" in data
        assert isinstance(data["commits_queued"], int)

    def test_github_webhook_invalid_signature(self):
        """Test POST /webhook/github with invalid signature."""
        # Arrange
        client = TestClient(app)
        headers = {
            "X-GitHub-Event": "push",
            "X-GitHub-Signature-256": "sha256=invalid-signature"
        }
        payload = {"ref": "refs/heads/main"}

        # Mock webhook verification failure
        with patch('backend.services.webhook_service.verify_signature') as mock_verify:
            mock_verify.return_value = False

            # Act
            response = client.post("/api/webhook/github", headers=headers, json=payload)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"] == "webhook_verification_failed"

    def test_github_webhook_unsupported_event(self):
        """Test POST /webhook/github with unsupported event type."""
        # Arrange
        client = TestClient(app)
        headers = {
            "X-GitHub-Event": "issues",
            "X-GitHub-Signature-256": "sha256=valid-signature"
        }
        payload = {"action": "opened"}

        # Mock webhook verification
        with patch('backend.services.webhook_service.verify_signature') as mock_verify:
            mock_verify.return_value = True

            # Act
            response = client.post("/api/webhook/github", headers=headers, json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Should acknowledge but not process unsupported events


# Test fixtures
@pytest.fixture
def mock_authenticated_user():
    """Mock authenticated user for tests."""
    return {
        "id": 1,
        "github_id": "12345",
        "username": "testuser",
        "access_token": "encrypted_token"
    }


@pytest.fixture
def sample_repositories():
    """Sample repository data for tests."""
    return [
        {
            "id": 123456789,
            "full_name": "user/repo1",
            "private": False,
            "language": "Python",
            "default_branch": "main",
            "updated_at": "2025-09-27T10:00:00Z"
        },
        {
            "id": 987654321,
            "full_name": "user/repo2",
            "private": True,
            "language": "JavaScript",
            "default_branch": "develop",
            "updated_at": "2025-09-26T15:30:00Z"
        }
    ]