# API Contracts

**Feature**: Tamagitto Developer Monitoring Tamagotchi  
**Date**: 2025-09-27  
**Base URL**: `https://tamagitto.xyz/api`

## Authentication

### GitHub OAuth Flow

#### POST /auth/github/initiate
Initiate GitHub OAuth flow from extension

**Request**:
```json
{
    "redirect_uri": "chrome-extension://[extension-id]/oauth-callback.html"
}
```

**Response** (200):
```json
{
    "oauth_url": "https://github.com/login/oauth/authorize?client_id=...&state=...",
    "state": "randomized-state-token"
}
```

#### POST /auth/github/callback
Complete OAuth flow with authorization code

**Request**:
```json
{
    "code": "github-oauth-code",
    "state": "state-token-from-initiate"
}
```

**Response** (200):
```json
{
    "session_token": "jwt-session-token",
    "user": {
        "id": 1,
        "username": "developer123",
        "avatar_url": "https://github.com/avatars/...",
        "email": "dev@example.com"
    },
    "expires_at": "2025-09-28T14:30:00Z"
}
```

**Error Response** (400):
```json
{
    "error": "invalid_code",
    "message": "GitHub OAuth code is invalid or expired"
}
```

#### POST /auth/refresh
Refresh expired session token

**Request Headers**: 
```
Authorization: Bearer <expired-session-token>
```

**Response** (200):
```json
{
    "session_token": "new-jwt-session-token",
    "expires_at": "2025-09-28T14:30:00Z"
}
```

## Repository Management

#### GET /repositories
Get user's GitHub repositories

**Request Headers**:
```
Authorization: Bearer <session-token>
```

**Query Parameters**:
- `type` (optional): `all`, `public`, `private` (default: `all`)
- `sort` (optional): `updated`, `created`, `pushed`, `full_name` (default: `updated`)
- `per_page` (optional): 1-100 (default: 30)

**Response** (200):
```json
{
    "repositories": [
        {
            "id": 123456789,
            "full_name": "developer123/awesome-project",
            "private": false,
            "language": "JavaScript",
            "default_branch": "main",
            "updated_at": "2025-09-27T10:30:00Z",
            "monitoring_enabled": false
        }
    ],
    "total_count": 15,
    "has_more": true
}
```

#### POST /repositories/{github_repo_id}/monitor
Start monitoring a repository

**Request Headers**:
```
Authorization: Bearer <session-token>
```

**Request**:
```json
{
    "entity_preferences": {
        "type": "pet",  // optional: auto-detected from language
        "name": "CodeBuddy"  // optional: auto-generated
    }
}
```

**Response** (201):
```json
{
    "repository": {
        "id": 1,
        "github_repo_id": 123456789,
        "full_name": "developer123/awesome-project",
        "monitoring_active": true,
        "last_monitored_at": "2025-09-27T14:30:00Z"
    },
    "entity": {
        "id": 1,
        "name": "CodeBuddy",
        "type": "pet",
        "health_score": 100,
        "status": "alive",
        "visual_url": "https://storage.tamagitto.xyz/entities/1/current.png",
        "created_at": "2025-09-27T14:30:00Z"
    },
    "message": "Entity is being generated, check back in a few seconds"
}
```

#### DELETE /repositories/{github_repo_id}/monitor
Stop monitoring a repository

**Response** (200):
```json
{
    "message": "Repository monitoring stopped",
    "entity_archived": true
}
```

## Entity Management

#### GET /entities/current
Get user's active entity

**Request Headers**:
```
Authorization: Bearer <session-token>
```

**Response** (200):
```json
{
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
```

**Response** (404):
```json
{
    "error": "no_active_entity",
    "message": "No active entity found. Start monitoring a repository first."
}
```

#### GET /entities/{entity_id}/health-history
Get entity health history

**Query Parameters**:
- `days` (optional): 1-90 (default: 30)
- `granularity` (optional): `hourly`, `daily` (default: `daily`)

**Response** (200):
```json
{
    "entity_id": 1,
    "health_history": [
        {
            "timestamp": "2025-09-27T10:00:00Z",
            "health_score": 78,
            "change_reason": "commit_analysis",
            "commit_sha": "abc123...",
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
```

#### POST /entities/{entity_id}/reset
Reset dead entity (create new one)

**Response** (201):
```json
{
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
```

**Error Response** (400):
```json
{
    "error": "cooldown_active",
    "message": "Must wait 22 hours before creating new entity",
    "cooldown_expires": "2025-09-28T12:30:00Z"
}
```

## Commit Analysis

#### GET /analysis/recent
Get recent commit analyses for user's monitored repositories

**Query Parameters**:
- `limit` (optional): 1-50 (default: 10)
- `repository_id` (optional): Filter by specific repository

**Response** (200):
```json
{
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
```

#### POST /analysis/trigger
Manually trigger analysis for latest commits (rate limited)

**Request**:
```json
{
    "repository_id": 1
}
```

**Response** (202):
```json
{
    "message": "Analysis queued for processing",
    "estimated_completion": "2025-09-27T14:35:00Z"
}
```

## WebSocket Real-Time Updates

#### WS /ws
Real-time entity updates

**Connection Headers**:
```
Authorization: Bearer <session-token>
```

**Message Types**:

**Entity Health Update**:
```json
{
    "type": "health_update",
    "entity_id": 1,
    "health_score": 75,
    "visual_url": "https://storage.tamagitto.xyz/entities/1/healthy.png",
    "change_reason": "commit_analysis",
    "timestamp": "2025-09-27T14:30:00Z"
}
```

**Entity Status Change**:
```json
{
    "type": "status_change", 
    "entity_id": 1,
    "old_status": "alive",
    "new_status": "dying",
    "health_score": 15,
    "message": "Your entity is in critical condition!",
    "timestamp": "2025-09-27T14:30:00Z"
}
```

**Analysis Complete**:
```json
{
    "type": "analysis_complete",
    "repository": "developer123/awesome-project",
    "commit_sha": "abc123def456",
    "quality_score": 8.5,
    "health_delta": 3,
    "timestamp": "2025-09-27T14:30:00Z"
}
```

## Webhook Endpoints

#### POST /webhook/github
GitHub repository webhook receiver

**Request Headers**:
```
X-GitHub-Event: push
X-GitHub-Signature-256: sha256=...
```

**Request** (Push Event):
```json
{
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
            "timestamp": "2025-09-27T14:30:00Z"
        }
    ]
}
```

**Response** (200):
```json
{
    "message": "Webhook processed successfully",
    "commits_queued": 1
}
```

## Error Handling

### Standard Error Response Format
```json
{
    "error": "error_code",
    "message": "Human readable error message",
    "details": {},  // Optional additional context
    "timestamp": "2025-09-27T14:30:00Z"
}
```

### Common Error Codes
- `invalid_token`: Session token invalid or expired
- `repository_not_found`: GitHub repository not accessible 
- `rate_limit_exceeded`: API rate limit reached
- `entity_dead`: Cannot perform action on dead entity
- `cooldown_active`: Action blocked by cooldown period
- `webhook_verification_failed`: GitHub webhook signature invalid
- `analysis_failed`: Commit analysis processing error

## Rate Limiting

### Limits by Endpoint
- **Authentication**: 10 requests/minute
- **Repository Management**: 60 requests/minute  
- **Entity Updates**: 120 requests/minute
- **Analysis Triggers**: 5 requests/minute
- **Webhooks**: No limit (GitHub controlled)

### Rate Limit Headers
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1695825600
```

## API Contract Testing

### Contract Test Requirements
1. **Authentication Flow**: Complete OAuth roundtrip
2. **Repository CRUD**: List, monitor, stop monitoring
3. **Entity Lifecycle**: Creation, health updates, death, reset
4. **Real-time Updates**: WebSocket connection and message handling
5. **Error Scenarios**: Rate limits, authentication failures, dead entities

### Mock Data Requirements
- **GitHub API Responses**: Repository lists, commit data, webhook payloads
- **Entity Images**: Sample generated images for different health states
- **User Data**: Test users with various repository configurations
- **Time-based Scenarios**: Health decay, cooldown periods, analysis timing