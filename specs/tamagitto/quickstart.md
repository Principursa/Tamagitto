# Development Quickstart Guide

**Feature**: Tamagitto Developer Monitoring Tamagotchi  
**Date**: 2025-09-27  
**Prerequisites**: Docker, Node.js 18+, Python 3.13, Chrome browser

## Environment Setup

### 1. Repository Structure Setup
```bash
# Create required directories
mkdir -p backend/{models,services,agents,api,tests}
mkdir -p extension/{styles,icons,oauth}
mkdir -p static-site/{assets,styles}
mkdir -p infrastructure

# Initialize Python environment
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Install development tools
pip install pytest mypy black ruff pytest-asyncio
```

### 2. Environment Variables
Create `.env` file in project root:
```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_app_client_id
GITHUB_CLIENT_SECRET=your_github_app_secret

# Database
DATABASE_URL=postgresql://tamagitto:password@localhost:5432/tamagitto_dev
TEST_DATABASE_URL=postgresql://tamagitto:password@localhost:5432/tamagitto_test

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Security
JWT_SECRET=your-super-secret-jwt-key
ENCRYPTION_KEY=your-32-byte-encryption-key

# API Configuration
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=["chrome-extension://your-extension-id"]

# Infrastructure
DOMAIN=localhost:8000
```

### 3. Database Setup
```bash
# Start PostgreSQL with Docker
docker run --name tamagitto-postgres \
  -e POSTGRES_USER=tamagitto \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=tamagitto_dev \
  -p 5432:5432 \
  -d postgres:15

# Run database migrations
cd backend
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_dev_data.py
```

### 4. GitHub App Configuration
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App:
   - **Application name**: Tamagitto Development
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `chrome-extension://[your-extension-id]/oauth-callback.html`
3. Copy Client ID and Client Secret to `.env`

## Development Workflow

### Backend Development

#### Start Development Server
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# API will be available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

#### Run Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires test database)
pytest tests/integration/

# All tests with coverage
pytest --cov=. --cov-report=html

# Type checking
mypy .

# Code formatting and linting
black .
ruff check .
```

#### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Reset database (development only)
alembic downgrade base
alembic upgrade head
python scripts/seed_dev_data.py
```

### Extension Development

#### Load Extension in Chrome
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension/` directory
4. Note the Extension ID for OAuth configuration

#### Development Process
```bash
# Watch for changes (if using build tools)
cd extension
npm run dev  # or just edit files directly

# Test OAuth flow
# 1. Click extension icon
# 2. Try GitHub login
# 3. Check browser console and extension console for errors
```

#### Extension Testing
```bash
# Unit tests for extension logic
cd extension
npm test

# Manual testing checklist:
# - Popup opens and displays correctly
# - OAuth flow completes successfully  
# - Repository selection works
# - Entity display updates in real-time
# - WebSocket connection establishes
# - Error states display properly
```

### Static Site Development

#### Local Development
```bash
cd static-site

# Simple HTTP server for testing
python -m http.server 3000
# or
npx serve .

# Site available at http://localhost:3000
```

#### Performance Testing
```bash
# Lighthouse CI (requires Chrome)
npm install -g @lhci/cli
lhci autorun --upload.target=temporary-public-storage
```

## API Testing

### Manual API Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test authentication (need actual OAuth code)
curl -X POST http://localhost:8000/api/auth/github/initiate \
  -H "Content-Type: application/json" \
  -d '{"redirect_uri": "chrome-extension://test/oauth-callback.html"}'

# Test with session token
curl -H "Authorization: Bearer your-jwt-token" \
  http://localhost:8000/api/entities/current
```

### Automated API Testing
```bash
# Run contract tests
pytest tests/contract/

# Test with different scenarios
pytest tests/contract/ -k "test_auth_flow"
pytest tests/contract/ -k "test_entity_lifecycle"
```

## Docker Development

### Full Stack with Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: tamagitto
      POSTGRES_PASSWORD: password
      POSTGRES_DB: tamagitto_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://tamagitto:password@postgres:5432/tamagitto_dev
    depends_on:
      - postgres
    
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
    volumes:
      - ./Caddyfile.dev:/etc/caddy/Caddyfile
      - ./static-site:/var/www/static
    depends_on:
      - backend

volumes:
  postgres_dev_data:
```

Start development environment:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

## Testing Strategy

### Test Data Management
```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import User, Repository, Entity

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        github_id="123456",
        username="testuser",
        access_token_encrypted="encrypted-token"
    )
    db.add(test_user)
    db.commit()
    
    yield db
    db.close()
```

### Mock GitHub API
```python
# tests/mocks.py
import responses

@responses.activate
def test_github_api_integration():
    responses.add(
        responses.GET,
        "https://api.github.com/user/repos",
        json=[{
            "id": 123456789,
            "full_name": "testuser/test-repo",
            "private": False,
            "language": "Python"
        }],
        status=200
    )
    
    # Test repository fetching logic
```

## Common Development Issues

### OAuth Flow Problems
```bash
# Problem: OAuth redirect doesn't work
# Solution: Check extension ID in manifest matches OAuth callback URL

# Problem: CORS errors in extension
# Solution: Add proper host_permissions in manifest.json

# Problem: Session tokens not persisting
# Solution: Verify chrome.storage.local permissions and usage
```

### Database Connection Issues
```bash
# Problem: Connection refused
# Solution: Ensure PostgreSQL is running and credentials match

# Problem: Migration conflicts
# Solution: Reset migrations in development
alembic downgrade base
rm alembic/versions/*.py
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### WebSocket Connection Problems
```bash
# Problem: WebSocket connection fails
# Solution: Check CORS settings and authentication headers

# Problem: Real-time updates not working
# Solution: Verify WebSocket message handling in extension
```

## Performance Optimization

### Backend Performance
```python
# Database query optimization
from sqlalchemy.orm import joinedload

# Efficient entity loading with relationships
entity = session.query(Entity)\
    .options(
        joinedload(Entity.repository),
        joinedload(Entity.health_history)
    )\
    .filter(Entity.id == entity_id)\
    .first()
```

### Extension Performance
```javascript
// Efficient popup loading
async function loadEntityData() {
    // Check cache first
    const cached = await ExtensionStorage.getEntityCache();
    const cacheAge = Date.now() - cached?.lastUpdate || Infinity;
    
    if (cacheAge < 30000) { // 30 seconds
        updateUI(cached.entity);
        return;
    }
    
    // Fetch fresh data
    const fresh = await api.getCurrentEntity();
    await ExtensionStorage.setEntityCache(fresh.entity);
    updateUI(fresh.entity);
}
```

## Debugging Tips

### Backend Debugging
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for breakpoints
import pdb; pdb.set_trace()

# Monitor SQL queries
echo=True  # in create_engine() for SQLAlchemy
```

### Extension Debugging
```javascript
// Debug popup
// Right-click extension icon → Inspect popup

// Debug background script  
// Go to chrome://extensions → Background page

// Debug content scripts
// Use browser DevTools on target pages

// Comprehensive error logging
window.onerror = (message, source, lineno, colno, error) => {
    console.error('Extension error:', {message, source, lineno, colno, error});
};
```

## Production Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] SSL certificates configured
- [ ] OAuth app configured for production domain
- [ ] Extension submission ready

### Deployment Steps
1. **Build and test backend Docker image**
2. **Deploy database with proper backups**
3. **Configure reverse proxy (Caddy)**
4. **Deploy backend container**
5. **Deploy static site**
6. **Test full integration**
7. **Submit extension to Chrome Web Store**

This quickstart guide provides the essential setup and development workflow for the Tamagitto application. Refer to individual contract files for detailed API specifications and implementation requirements.