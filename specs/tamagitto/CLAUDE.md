# Claude Code Development Guidance for Tamagitto

**Feature**: Tamagitto Developer Monitoring Tamagotchi  
**Date**: 2025-09-27  
**Claude Code Version**: Latest

## Project Context for Claude Code

### High-Level Architecture
Tamagitto is a Chrome extension that gamifies developer productivity through virtual entities (Tamagotchi-style pets) that live or die based on code quality and commit frequency. The system consists of:

1. **Chrome Extension** (JavaScript/HTML/CSS) - User interface in browser
2. **Python Backend** (FastAPI + google-adk) - API server with AI agents for commit analysis  
3. **Static Website** (HTML/CSS/JS) - Marketing and feature showcase
4. **Infrastructure** (Docker + Caddy) - Container deployment with reverse proxy

### Key Technologies
- **Frontend**: Vanilla JavaScript, Chrome Extensions API, WebSockets
- **Backend**: Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, google-adk agents
- **AI Integration**: Gemini image generation, commit quality analysis agents
- **Infrastructure**: Docker, Caddy reverse proxy, VPS hosting

## Development Workflow for Claude Code

### When Working on Backend Python Code
```python
# Always check existing imports and patterns first
# Example: Look for existing database patterns
# File: backend/models/user.py

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from backend.database import Base

class User(Base):
    __tablename__ = 'users'
    # Follow existing naming conventions and patterns
```

**Claude Code Guidelines**:
- Check `backend/pyproject.toml` for dependencies before adding new ones
- Follow existing SQLAlchemy model patterns in `backend/models/`
- Use existing FastAPI route structure in `backend/api/`
- Run `mypy .` and `pytest` before marking tasks complete
- Follow the health calculation algorithms defined in research.md

### When Working on Chrome Extension JavaScript
```javascript
// Always check manifest.json permissions first
// File: extension/manifest.json - verify permissions before using APIs

// Follow existing storage patterns
class ExtensionStorage {
    static async getSessionToken() {
        const result = await chrome.storage.local.get(['sessionToken']);
        return result.sessionToken;
    }
}

// Use established API client patterns
const api = new TamagittoAPI();
const entityData = await api.getCurrentEntity();
```

**Claude Code Guidelines**:
- Check `extension/manifest.json` for available permissions
- Follow Chrome Extensions Manifest V3 patterns
- Use existing WebSocket connection handling in popup.js
- Test OAuth flow with GitHub before marking authentication tasks complete
- Maintain popup UI state management patterns

### When Working on Infrastructure
```yaml
# File: docker-compose.yml
# Follow existing service naming and networking
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tamagitto
  
  db:
    image: postgres:15
    # Use consistent volume naming
```

**Claude Code Guidelines**:
- Check existing Docker configurations before creating new ones
- Use established environment variable patterns from `.env.example`
- Follow Caddy reverse proxy patterns in existing Caddyfile
- Ensure proper networking between services

## Common Development Patterns

### Database Operations
```python
# Always use existing session management
from backend.database import get_db
from sqlalchemy.orm import joinedload

def get_entity_with_repository(entity_id: int, db: Session):
    return db.query(Entity)\
        .options(joinedload(Entity.repository))\
        .filter(Entity.id == entity_id)\
        .first()
```

### API Error Handling  
```python
# Follow established error response patterns
from fastapi import HTTPException, status

if not entity:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Entity not found"
    )
```

### Extension State Management
```javascript
// Use existing UI state patterns
showScreen(screenName) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    document.getElementById(`${screenName}-screen`).classList.remove('hidden');
}
```

## Testing Expectations

### Backend Testing
- **Unit Tests**: All business logic in `backend/services/`
- **Integration Tests**: API endpoints with test database
- **Contract Tests**: External API integrations (GitHub, Gemini)

```python
# Test example pattern
@pytest.mark.asyncio
async def test_entity_health_calculation(test_db):
    # Arrange: Create test data
    entity = Entity(health_score=100)
    
    # Act: Perform health calculation
    new_health = calculate_health_delta(analysis_data)
    
    # Assert: Verify result
    assert new_health >= 0
```

### Extension Testing  
- **Unit Tests**: API client and utility functions
- **Integration Tests**: OAuth flow, WebSocket connections
- **Manual Tests**: UI interactions, cross-browser compatibility

## Constitutional Compliance

### Code Quality Requirements
- **TypeScript**: Use strict mode compilation for extension code
- **Python**: mypy type checking with no errors
- **Testing**: TDD approach - write tests before implementation
- **Performance**: <200ms API response times

### Security Requirements
- **Token Storage**: Encrypt GitHub tokens at rest
- **CORS**: Proper configuration for extension domains  
- **Validation**: Input validation with Pydantic models
- **CSP**: Content Security Policy for extension

## File Structure Awareness

```
tamagitto/
├── backend/                 # Python FastAPI application
│   ├── models/             # SQLAlchemy database models
│   ├── services/           # Business logic
│   ├── agents/             # Commit analysis agents
│   ├── api/                # FastAPI route definitions
│   └── tests/              # Backend test suites
├── extension/              # Chrome extension files  
│   ├── popup.html          # Extension popup interface
│   ├── popup.js            # Extension logic
│   ├── background.js       # Service worker
│   └── manifest.json       # Extension configuration
├── static-site/            # Marketing website
├── infrastructure/         # Docker and deployment configs
└── specs/tamagitto/        # This planning documentation
    ├── plan.md             # Implementation plan
    ├── research.md         # Technical decisions
    ├── data-model.md       # Database schema
    ├── contracts/          # API specifications
    └── quickstart.md       # Development setup
```

## Agent Analysis Implementation Notes

### Commit Quality Analysis
```python
# Use google-adk for agent-based analysis
from google_adk import Agent

class CommitQualityAgent:
    def __init__(self):
        self.agent = Agent("commit-analyzer")
    
    async def analyze_commit(self, commit_data):
        # Implement the quality metrics from research.md:
        # - Code complexity analysis
        # - Test coverage delta  
        # - Documentation scoring
        # - Linting violations
        # - Security issue detection
        
        return {
            "overall_quality_score": score,
            "health_delta": calculate_health_impact(score)
        }
```

## Common Troubleshooting

### GitHub OAuth Issues
- Verify `GITHUB_CLIENT_ID` matches OAuth app configuration
- Check redirect URI matches extension ID
- Ensure proper CORS headers for cross-origin requests

### Database Connection Problems
- Check `DATABASE_URL` format and credentials
- Verify PostgreSQL is running and accessible
- Run `alembic upgrade head` for schema updates

### WebSocket Connection Failures
- Check authentication token in WebSocket headers
- Verify CORS configuration allows WebSocket upgrades
- Implement polling fallback as specified in contracts

### Extension Loading Issues  
- Verify `manifest.json` syntax and required permissions
- Check Chrome developer mode is enabled
- Clear extension storage if authentication state is corrupted

## Development Task Patterns

### Adding New API Endpoints
1. Define route in `backend/api/` following existing patterns
2. Add corresponding service logic in `backend/services/`
3. Update database models if needed
4. Write contract tests in `tests/contract/`
5. Update API documentation

### Adding Extension Features
1. Update `manifest.json` with any new permissions  
2. Modify popup HTML structure and styling
3. Add JavaScript logic following existing state management
4. Test OAuth flow and API integration
5. Add error handling for edge cases

### Modifying Entity Behavior
1. Update health calculation logic in `backend/services/`
2. Modify database models if schema changes needed
3. Update WebSocket message handling for real-time updates
4. Test entity lifecycle from creation to death
5. Update extension UI to reflect behavior changes

## Success Criteria for Task Completion

- All tests passing (`pytest` for backend, manual testing for extension)
- Type checking clean (`mypy .` for backend)  
- Code follows existing patterns and conventions
- API responses match contract specifications
- Extension UI updates reflect backend state changes
- Real-time updates working via WebSocket or polling fallback
- Constitutional requirements met (performance, security, testing)

## Next Steps After Implementation Planning

1. **Run `/tasks` command** to generate specific implementation tasks
2. **Start with database setup** and core models
3. **Implement authentication flow** for GitHub OAuth  
4. **Build entity creation** and health calculation logic
5. **Develop extension UI** with real-time updates
6. **Add commit analysis agents** for quality scoring
7. **Test full integration** across all components
8. **Deploy infrastructure** and static site

Remember: This is a gamification app where code quality directly impacts entity health. The core value is motivating developers through emotional attachment to their virtual pets/plants/creatures.