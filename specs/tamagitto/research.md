# Phase 0 Research: Tamagitto Technical Architecture

**Feature**: Tamagitto Developer Monitoring Tamagotchi  
**Date**: 2025-09-27  
**Status**: Technical decisions resolved for Phase 1

## Database Architecture Decision

### Chosen: PostgreSQL with SQLAlchemy ORM

**Justification**: 
- Entity health tracking requires ACID transactions for consistent state updates
- Complex relationships between users, repositories, entities, and commit analysis
- JSON columns for flexible entity metadata and commit analysis results  
- Better performance for time-series queries (entity health over time)
- Robust backup/recovery for production deployment

**Schema Overview**:
```sql
users (id, github_id, access_token_encrypted, created_at)
repositories (id, user_id, github_repo_id, full_name, monitoring_active)
entities (id, repository_id, health_score, visual_url, entity_type, metadata_json)
commit_analyses (id, repository_id, commit_sha, quality_score, analysis_json, created_at)
health_history (id, entity_id, health_score, timestamp)
```

## GitHub API Integration Strategy

### OAuth Flow: Extension → Backend Proxy
- Extension initiates OAuth with `chrome.identity.launchWebAuthFlow()`
- Backend handles OAuth callback and token exchange
- Encrypted token storage in PostgreSQL with AES-256-GCM
- Extension receives session token, never stores GitHub token directly

### Repository Monitoring: Hybrid Polling + Webhooks
- **Primary**: GitHub webhooks to backend `/webhook/github` endpoint
- **Fallback**: Polling every 5 minutes for webhook failures
- **Rate Limiting**: GitHub Apps API (5000 req/hr) vs OAuth (60 req/hr)
- **Decision**: Use OAuth initially, migrate to GitHub App for scale

## Entity Generation Pipeline

### Gemini Image Generation Integration
- **Trigger**: Repository selection or entity reset
- **Prompt Engineering**: "Generate a cute [creature_type] representing a [language] codebase with [initial_health] vitality"
- **Caching**: Store generated images in object storage (AWS S3/DigitalOcean Spaces)
- **Fallback**: Default entity sprites for API failures
- **Variations**: Health-based image variations (5 states: thriving, healthy, okay, poor, dying)

### Entity Types by Repository Language
```
JavaScript/TypeScript → Digital Pet (cat, dog, hamster)
Python → Plant (succulent, fern, flower)  
Go/Rust/C++ → Robot/Android
Java/C# → Golem/Stone creature
Other → Adaptable blob creature
```

## Commit Analysis Agent Architecture

### Agent Pipeline Design
```
Commit Event → Language Detection → Quality Analysis → Health Calculation → Update Entity
```

### Quality Metrics (google-adk agents)
1. **Code Complexity**: Cyclomatic complexity, function length, nesting depth
2. **Testing**: Test coverage changes, new tests added, test passing rate
3. **Documentation**: Comments added, README updates, inline documentation
4. **Code Style**: Linting violations, formatting consistency
5. **Security**: Vulnerability patterns, secrets detection, dependency updates

### Health Calculation Algorithm
```python
def calculate_health_delta(analysis):
    base_score = 0
    base_score += analysis.test_coverage_delta * 0.3
    base_score += analysis.documentation_score * 0.2  
    base_score -= analysis.complexity_increase * 0.4
    base_score -= analysis.linting_violations * 0.1
    return max(-20, min(20, base_score))  # Cap at ±20 points
```

### Health Deterioration Rules
- **No commits**: -2 health per day after 3-day grace period
- **Poor quality commits**: Additional -5 health penalty  
- **Death threshold**: Health <= 0 for 24 hours
- **Revival**: New repository selection after 48-hour cooldown

## Real-Time Updates Architecture

### WebSocket Implementation
- **Backend**: FastAPI WebSocket endpoints for real-time entity updates
- **Extension**: WebSocket client for live health changes
- **Fallback**: 30-second polling if WebSocket connection fails
- **Message Format**: JSON with entity_id, health_score, timestamp, visual_url

```javascript
// Extension WebSocket client
const ws = new WebSocket('wss://tamagitto.xyz/api/ws');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    updateEntityUI(update.entity_id, update.health_score, update.visual_url);
};
```

## Security Architecture

### Extension Security Model
- **Content Security Policy**: Strict CSP with nonce-based script execution
- **Cross-Origin**: CORS configuration for tamagitto.xyz API access
- **Token Storage**: Extension storage.local with Chrome's encryption
- **Permissions**: Minimal manifest permissions (storage, identity, activeTab)

### Backend Security  
- **API Authentication**: JWT tokens with 24-hour expiration
- **Rate Limiting**: 100 requests per minute per user
- **Input Validation**: Pydantic models with strict validation
- **GitHub Token**: AES-256-GCM encryption at rest, rotation support

## Performance Requirements Resolution

### Response Time Targets
- **Entity Health Update**: <100ms (in-memory calculation)
- **Commit Analysis**: <2s (async processing with immediate acknowledgment)
- **Extension Popup Load**: <500ms (cached entity state)
- **Image Generation**: <5s (async with loading states)

### Caching Strategy
- **Entity States**: Redis cache with 5-minute TTL
- **Repository Metadata**: In-memory LRU cache (1000 entries)
- **Generated Images**: CDN caching with 30-day expiration
- **Commit Analysis**: Database indexing on repository_id + timestamp

## Infrastructure Deployment

### Docker Architecture
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tamagitto
      - GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
```

### Caddy Reverse Proxy Configuration
```
tamagitto.xyz {
    root * /var/www/static
    file_server
    
    handle /api/* {
        reverse_proxy backend:8000
    }
}
```

## Development Environment

### Backend Development
- **Python 3.13** with uv for dependency management
- **FastAPI** with automatic OpenAPI documentation
- **Alembic** for database migrations
- **pytest** with fixtures for GitHub API mocking
- **mypy** for static type checking

### Extension Development  
- **Chrome Extensions Manifest V3**
- **Vanilla JavaScript** with ES2020+ features
- **Web Extensions Polyfill** for cross-browser compatibility
- **Jest** for unit testing extension logic
- **Chrome DevTools** for debugging and profiling

### Static Site
- **Vanilla HTML/CSS/JS** for maximum performance
- **Lighthouse CI** for performance monitoring
- **Image optimization** with WebP format support
- **CSS Grid/Flexbox** for responsive design

## Risk Mitigation

### GitHub API Rate Limits
- **Monitoring**: Track rate limit headers in each request
- **Backoff**: Exponential backoff for rate limit exceeded errors
- **Caching**: Cache repository metadata for 1 hour minimum
- **User Communication**: Clear messaging about rate limit constraints

### Entity Generation Failures  
- **Retry Logic**: 3 retry attempts with exponential backoff
- **Fallback Images**: Pre-generated default entities per language
- **Offline Mode**: Extension works with last cached entity state
- **Error UX**: Friendly error messages with retry buttons

### Database Reliability
- **Connection Pooling**: SQLAlchemy connection pool (10-20 connections)
- **Health Checks**: Endpoint monitoring with automatic restarts
- **Backup Strategy**: Daily automated backups to cloud storage
- **Migration Safety**: Reversible migrations with rollback procedures

## Phase 0 Complete

All technical decisions resolved. No remaining NEEDS CLARIFICATION items for implementation. Ready for Phase 1 design artifacts.