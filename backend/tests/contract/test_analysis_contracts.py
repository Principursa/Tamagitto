"""Contract tests for commit analysis endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestCommitAnalysisContracts:
    """Test commit analysis endpoint contracts."""

    def test_get_recent_analyses_success(self):
        """Test GET /analysis/recent success response."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        params = {"limit": 10}

        # Mock analysis service
        with patch('backend.services.analysis_service.get_recent_analyses') as mock_analyses:
            mock_analyses.return_value = {
                "analyses": [
                    {
                        "id": 1,
                        "repository": "developer123/awesome-project",
                        "commit": {
                            "sha": "abc123def456",
                            "message": "Add user authentication system",
                            "author": "developer123",
                            "committed_at": "2025-09-27T10:30:00Z"
                        },
                        "quality_metrics": {
                            "overall_score": 8.5,
                            "complexity_score": 7.2,
                            "test_coverage_delta": 5.3,
                            "documentation_score": 9.0,
                            "linting_violations": 2,
                            "security_issues": 0
                        },
                        "health_impact": {
                            "delta": 5,
                            "reason": "Good test coverage and documentation"
                        },
                        "processed_at": "2025-09-27T10:32:00Z"
                    }
                ]
            }

            # Act
            response = client.get("/api/analysis/recent", headers=headers, params=params)

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "analyses" in data
        analyses = data["analyses"]
        assert len(analyses) == 1
        
        # Verify analysis structure
        analysis = analyses[0]
        required_fields = ["id", "repository", "commit", "quality_metrics", 
                          "health_impact", "processed_at"]
        for field in required_fields:
            assert field in analysis
        
        # Verify commit structure
        commit = analysis["commit"]
        assert "sha" in commit
        assert "message" in commit
        assert "author" in commit
        assert "committed_at" in commit
        
        # Verify quality metrics
        metrics = analysis["quality_metrics"]
        assert "overall_score" in metrics
        assert "complexity_score" in metrics
        assert "test_coverage_delta" in metrics

    def test_trigger_analysis_success(self):
        """Test POST /analysis/trigger success response."""
        # Arrange
        client = TestClient(app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        request_data = {"repository_id": 1}

        # Mock analysis service
        with patch('backend.services.analysis_service.trigger_analysis') as mock_trigger:
            mock_trigger.return_value = True

            # Act
            response = client.post("/api/analysis/trigger", headers=headers, json=request_data)

        # Assert
        assert response.status_code == 202
        data = response.json()
        
        assert "message" in data
        assert "estimated_completion" in data