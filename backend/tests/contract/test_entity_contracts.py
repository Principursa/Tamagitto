"""Contract tests for entity management endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestEntityManagementContracts:
    """Test entity management endpoint contracts."""

    def test_get_current_entity_success(self):
        """Test GET /entities/current success response."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}

        # Mock entity service
        with patch('backend.services.entity_service.get_user_entity') as mock_get_entity:
            mock_get_entity.return_value = {
                "entity": {
                    "id": 1,
                    "repository": {
                        "full_name": "developer123/awesome-project",
                        "language": "JavaScript"
                    },
                    "name": "CodeBuddy",
                    "type": "pet",
                    "health_score": 75,
                    "status": "alive",
                    "visual_url": "https://storage.tamagitto.xyz/entities/1/healthy.png",
                    "last_updated": "2025-09-27T12:15:00Z"
                },
                "health_trend": [
                    {"date": "2025-09-26", "score": 80},
                    {"date": "2025-09-27", "score": 75}
                ]
            }

            # Act
            response = client.get("/api/entities/current", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "entity" in data
        assert "health_trend" in data
        
        # Verify entity object
        entity = data["entity"]
        required_fields = ["id", "repository", "name", "type", "health_score", 
                          "status", "visual_url", "last_updated"]
        for field in required_fields:
            assert field in entity
        
        # Verify types
        assert isinstance(entity["id"], int)
        assert isinstance(entity["health_score"], int)
        assert entity["health_score"] >= 0 and entity["health_score"] <= 100
        assert entity["status"] in ["alive", "dying", "dead"]

    def test_get_current_entity_not_found(self):
        """Test GET /entities/current when no entity exists."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}

        # Mock entity service to return None
        with patch('backend.services.entity_service.get_user_entity') as mock_get_entity:
            mock_get_entity.return_value = None

            # Act
            response = client.get("/api/entities/current", headers=headers)

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"] == "no_active_entity"
        assert "message" in data

    def test_get_entity_health_history_success(self):
        """Test GET /entities/{entity_id}/health-history success."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        entity_id = 1
        params = {"days": 7, "granularity": "daily"}

        # Mock health service
        with patch('backend.services.health_service.get_health_history') as mock_history:
            mock_history.return_value = {
                "entity_id": 1,
                "health_history": [
                    {
                        "timestamp": "2025-09-27T10:00:00Z",
                        "health_score": 78,
                        "change_reason": "commit_analysis",
                        "commit_sha": "abc123",
                        "delta": 3
                    },
                    {
                        "timestamp": "2025-09-26T15:30:00Z",
                        "health_score": 75,
                        "change_reason": "daily_decay",
                        "delta": -2
                    }
                ],
                "summary": {
                    "current_health": 78,
                    "trend": "improving",
                    "days_tracked": 7
                }
            }

            # Act
            response = client.get(
                f"/api/entities/{entity_id}/health-history",
                headers=headers,
                params=params
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "entity_id" in data
        assert "health_history" in data
        assert "summary" in data
        
        # Verify history entries
        history = data["health_history"]
        assert len(history) == 2
        
        entry = history[0]
        assert "timestamp" in entry
        assert "health_score" in entry
        assert "change_reason" in entry
        assert "delta" in entry

    def test_reset_entity_success(self):
        """Test POST /entities/{entity_id}/reset success."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        entity_id = 1

        # Mock entity service
        with patch('backend.services.entity_service.reset_entity') as mock_reset:
            mock_reset.return_value = {
                "entity": {
                    "id": 2,
                    "name": "CodeBuddy II",
                    "health_score": 100,
                    "status": "alive",
                    "visual_url": "https://storage.tamagitto.xyz/entities/2/current.png"
                },
                "cooldown_expires": "2025-09-29T14:30:00Z",
                "message": "New entity created successfully"
            }

            # Act
            response = client.post(f"/api/entities/{entity_id}/reset", headers=headers)

        # Assert
        assert response.status_code == 201
        data = response.json()
        
        # Verify required fields
        assert "entity" in data
        assert "cooldown_expires" in data
        assert "message" in data
        
        # Verify new entity
        entity = data["entity"]
        assert entity["health_score"] == 100
        assert entity["status"] == "alive"

    def test_reset_entity_cooldown_active(self):
        """Test POST /entities/{entity_id}/reset during cooldown."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        entity_id = 1

        # Mock service to return cooldown error
        with patch('backend.services.entity_service.reset_entity') as mock_reset:
            mock_reset.side_effect = Exception("Cooldown active")

            # Act
            response = client.post(f"/api/entities/{entity_id}/reset", headers=headers)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"] == "cooldown_active"


# Simplified test fixtures
@pytest.fixture
def sample_entity():
    """Sample entity data for tests."""
    return {
        "id": 1,
        "name": "TestPet",
        "type": "pet",
        "health_score": 85,
        "status": "alive",
        "visual_url": "https://test.com/entity.png"
    }