# Tasks: Tamagitto Developer Monitoring Tamagotchi

**Input**: Design documents from `/specs/tamagitto/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Execution Status
- [x] **Plan loaded**: Tech stack (Python 3.13, FastAPI, Chrome Extension, PostgreSQL), structure identified
- [x] **Entities extracted**: User, Repository, Entity, CommitAnalysis, HealthHistory models
- [x] **Contracts loaded**: API endpoints, Extension interfaces
- [x] **Technical decisions**: Database (PostgreSQL), Auth (GitHub OAuth), Real-time (WebSocket + polling)

## Task Rules Applied
- **Different files** = marked [P] for parallel execution
- **Same file** = sequential (no [P]) to avoid conflicts
- **Tests before implementation** (TDD mandatory per constitution)
- **Dependencies ordered**: Setup → Tests → Models → Services → Endpoints → Integration → Polish

---

## Phase 3.1: Setup & Infrastructure

- [ ] **T001** Create project directory structure per implementation plan
  - Path: `backend/`, `extension/`, `static-site/`, `infrastructure/`
  - Create all subdirectories: `models/`, `services/`, `agents/`, `api/`, `tests/`

- [ ] **T002** [P] Initialize Python backend with FastAPI dependencies
  - Path: `backend/pyproject.toml`, `backend/requirements.txt`
  - Dependencies: FastAPI, SQLAlchemy, Alembic, google-adk, python-jose, passlib

- [ ] **T003** [P] Configure database setup with PostgreSQL and Alembic
  - Path: `backend/database.py`, `backend/alembic.ini`
  - Initialize Alembic, create database connection module

- [ ] **T004** [P] Set up Chrome extension manifest and basic structure  
  - Path: `extension/manifest.json`, `extension/popup.html`
  - Manifest V3 with required permissions (storage, identity, host_permissions)

- [ ] **T005** [P] Create infrastructure configuration files
  - Path: `infrastructure/docker-compose.yml`, `infrastructure/Dockerfile`, `infrastructure/Caddyfile`
  - Docker setup for backend, PostgreSQL, and Caddy reverse proxy

- [ ] **T006** [P] Configure linting and formatting tools
  - Path: `backend/pyproject.toml`, `extension/.eslintrc.js`
  - Python: mypy, black, ruff; JavaScript: ESLint, Prettier

- [ ] **T007** [P] Create environment configuration template
  - Path: `infrastructure/.env.example`
  - GitHub OAuth, database URLs, API keys, JWT secrets

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

### Contract Tests
- [ ] **T008** [P] Write API contract tests for authentication endpoints
  - Path: `backend/tests/contract/test_auth_contracts.py`
  - Test: GitHub OAuth flow, session management, token refresh

- [ ] **T009** [P] Write API contract tests for repository management
  - Path: `backend/tests/contract/test_repository_contracts.py`  
  - Test: Repository listing, monitoring start/stop, GitHub integration

- [ ] **T010** [P] Write API contract tests for entity management
  - Path: `backend/tests/contract/test_entity_contracts.py`
  - Test: Entity creation, health updates, status changes, reset functionality

- [ ] **T011** [P] Write API contract tests for commit analysis
  - Path: `backend/tests/contract/test_analysis_contracts.py`
  - Test: Commit processing, quality scoring, health impact calculation

- [ ] **T012** [P] Write extension contract tests for OAuth flow
  - Path: `extension/tests/test_oauth_flow.js`
  - Test: GitHub authentication, token storage, session management

- [ ] **T013** [P] Write extension contract tests for UI state management
  - Path: `extension/tests/test_ui_states.js`
  - Test: Screen transitions, entity display updates, error handling

### Integration Tests  
- [ ] **T014** [P] Write database integration tests for user management
  - Path: `backend/tests/integration/test_user_integration.py`
  - Test: User creation, GitHub token encryption/decryption, session handling

- [ ] **T015** [P] Write GitHub API integration tests
  - Path: `backend/tests/integration/test_github_integration.py`
  - Test: Repository fetching, webhook handling, rate limiting, OAuth callbacks

- [ ] **T016** [P] Write Gemini image generation integration tests
  - Path: `backend/tests/integration/test_image_generation.py`
  - Test: Entity image creation, caching, fallback handling

- [ ] **T017** [P] Write WebSocket real-time update tests
  - Path: `backend/tests/integration/test_websocket_integration.py`
  - Test: Connection handling, message broadcasting, authentication

---

## Phase 3.3: Core Implementation

### Database Models & Migrations
- [ ] **T018** Create database base configuration and utilities
  - Path: `backend/database.py`
  - Database connection, session management, Base class setup

- [ ] **T019** Implement User model with encryption utilities
  - Path: `backend/models/user.py`
  - User model with GitHub token encryption/decryption methods

- [ ] **T020** [P] Implement Repository model  
  - Path: `backend/models/repository.py`
  - Repository model with monitoring status and GitHub integration fields

- [ ] **T021** [P] Implement Entity model with health tracking
  - Path: `backend/models/entity.py`
  - Entity model with health calculations, status management, image URLs

- [ ] **T022** [P] Implement CommitAnalysis model
  - Path: `backend/models/commit_analysis.py`
  - Commit analysis model with quality metrics and health impact

- [ ] **T023** [P] Implement HealthHistory model
  - Path: `backend/models/health_history.py`
  - Health history tracking with timestamps and change reasons

- [ ] **T024** [P] Implement UserSession model
  - Path: `backend/models/user_session.py`
  - Session model for JWT token management and expiration

- [ ] **T025** Create database migrations for all models
  - Path: `backend/alembic/versions/001_initial_tables.py`
  - Alembic migration creating all tables with proper indexes and constraints

### Services & Business Logic
- [ ] **T026** Implement GitHub OAuth service
  - Path: `backend/services/auth_service.py`
  - OAuth flow handling, token exchange, user creation/authentication

- [ ] **T027** Implement GitHub API service  
  - Path: `backend/services/github_service.py`
  - Repository fetching, webhook management, commit data retrieval

- [ ] **T028** Implement entity management service
  - Path: `backend/services/entity_service.py`
  - Entity creation, health updates, status changes, image generation coordination

- [ ] **T029** Implement commit analysis agent
  - Path: `backend/agents/commit_analyzer.py`
  - google-adk agent for code quality analysis and health impact calculation

- [ ] **T030** Implement image generation service
  - Path: `backend/services/image_service.py`
  - Gemini API integration, image caching, entity visual generation

- [ ] **T031** Implement health calculation service
  - Path: `backend/services/health_service.py`
  - Health score calculations, deterioration logic, status transitions

- [ ] **T032** Implement WebSocket notification service
  - Path: `backend/services/websocket_service.py`
  - Real-time update broadcasting, connection management, authentication

### API Endpoints
- [ ] **T033** Implement authentication API endpoints
  - Path: `backend/api/auth.py`
  - GitHub OAuth initiate/callback, session refresh, logout endpoints

- [ ] **T034** Implement repository management API endpoints
  - Path: `backend/api/repositories.py`
  - Repository listing, monitoring start/stop, webhook endpoints

- [ ] **T035** Implement entity management API endpoints  
  - Path: `backend/api/entities.py`
  - Current entity, health history, status updates, reset endpoints

- [ ] **T036** Implement commit analysis API endpoints
  - Path: `backend/api/analysis.py`
  - Recent analyses, manual triggers, webhook processing endpoints

- [ ] **T037** Implement WebSocket endpoints
  - Path: `backend/api/websocket.py`
  - WebSocket connection handling, authentication, message routing

- [ ] **T038** Create main FastAPI application
  - Path: `backend/main.py`  
  - Application setup, middleware, CORS, route registration, error handling

---

## Phase 3.4: Extension Implementation

- [ ] **T039** Implement extension storage utilities
  - Path: `extension/storage.js`
  - Chrome storage wrapper for session tokens, entity cache, preferences

- [ ] **T040** Implement extension API client
  - Path: `extension/api-client.js`
  - HTTP client for backend API, authentication handling, error processing

- [ ] **T041** Implement GitHub OAuth flow in extension
  - Path: `extension/oauth.js`
  - Chrome identity API integration, OAuth flow management, token handling

- [ ] **T042** Implement extension UI state management
  - Path: `extension/ui-manager.js`
  - Screen transitions, entity display updates, loading states, error handling

- [ ] **T043** Implement extension popup interface
  - Path: `extension/popup.js`
  - Main popup logic, event handling, WebSocket connections, UI updates

- [ ] **T044** [P] Create extension popup HTML structure
  - Path: `extension/popup.html`
  - Complete HTML structure for all screens (auth, repo selection, entity, death)

- [ ] **T045** [P] Implement extension popup styling
  - Path: `extension/styles/popup.css`
  - CSS styling for all UI states, responsive design, animations

- [ ] **T046** Implement extension background service worker
  - Path: `extension/background.js`
  - Health monitoring, notifications, badge updates, periodic checks

---

## Phase 3.5: Static Site & Infrastructure

- [ ] **T047** [P] Create static site landing page
  - Path: `static-site/index.html`
  - Marketing landing page with feature highlights and download link

- [ ] **T048** [P] Create static site features showcase
  - Path: `static-site/features.html`
  - Detailed features page with screenshots and use cases

- [ ] **T049** [P] Implement static site styling
  - Path: `static-site/styles/main.css`
  - Responsive design, modern styling, consistent branding

- [ ] **T050** [P] Add static site assets and images
  - Path: `static-site/assets/`
  - Screenshots, icons, demo images, entity examples

---

## Phase 3.6: Integration & Testing

- [ ] **T051** Set up database seeding for development
  - Path: `backend/scripts/seed_dev_data.py`
  - Create sample users, repositories, entities for testing

- [ ] **T052** Implement health deterioration background task
  - Path: `backend/tasks/health_monitor.py`
  - Scheduled task for entity health decay and status updates

- [ ] **T053** Set up webhook handling for GitHub events
  - Path: `backend/services/webhook_service.py`
  - GitHub webhook processing, signature verification, commit triggering

- [ ] **T054** Implement comprehensive error handling
  - Path: `backend/middleware/error_handler.py`, `extension/error-handler.js`
  - Global error handling, user-friendly error messages, logging

- [ ] **T055** Add API rate limiting and security middleware
  - Path: `backend/middleware/rate_limiter.py`
  - Rate limiting per user, security headers, request validation

---

## Phase 3.7: Polish & Performance

- [ ] **T056** [P] Write comprehensive unit tests for services
  - Path: `backend/tests/unit/test_*_service.py`
  - Unit tests for all service classes with mocking

- [ ] **T057** [P] Write unit tests for extension utilities
  - Path: `extension/tests/test_utilities.js`
  - Unit tests for storage, API client, OAuth utilities

- [ ] **T058** [P] Add database query optimization and indexing
  - Path: `backend/models/*.py`
  - Query optimization, proper indexing, database performance tuning

- [ ] **T059** [P] Implement caching for frequently accessed data
  - Path: `backend/services/cache_service.py`
  - Redis or in-memory caching for entity states, repository data

- [ ] **T060** [P] Add comprehensive logging and monitoring
  - Path: `backend/utils/logger.py`, `extension/logger.js`
  - Structured logging, error tracking, performance monitoring

- [ ] **T061** [P] Create API documentation
  - Path: `backend/docs/api.md`
  - OpenAPI documentation, usage examples, authentication guide

- [ ] **T062** [P] Performance testing and optimization
  - Path: `backend/tests/performance/`
  - Load testing, response time validation, database performance tests

---

## Dependency Graph

```mermaid
graph TD
    T001[Setup Structure] → T002[Backend Init]
    T001 → T004[Extension Init]
    T002 → T003[Database Setup]
    T003 → T008[API Contract Tests]
    T004 → T012[Extension Contract Tests]
    
    T008 → T018[Database Base]
    T018 → T019[User Model]
    T019 → T020[Repository Model]
    T020 → T021[Entity Model]
    
    T021 → T026[Auth Service]
    T026 → T033[Auth Endpoints]
    T033 → T039[Extension Storage]
    T039 → T043[Extension Popup]
```

## Parallel Execution Examples

### Setup Phase (can run simultaneously)
```bash
# Terminal 1: Backend setup
claude implement T002 "Initialize Python backend with FastAPI dependencies"

# Terminal 2: Extension setup  
claude implement T004 "Set up Chrome extension manifest and basic structure"

# Terminal 3: Infrastructure
claude implement T005 "Create infrastructure configuration files"
```

### Contract Tests (can run simultaneously)
```bash
# Terminal 1: API contracts
claude implement T008 "Write API contract tests for authentication endpoints"
claude implement T009 "Write API contract tests for repository management" 

# Terminal 2: Extension contracts
claude implement T012 "Write extension contract tests for OAuth flow"
claude implement T013 "Write extension contract tests for UI state management"
```

### Models (can run simultaneously after database setup)
```bash  
# All model files are independent
claude implement T020 "Implement Repository model"
claude implement T021 "Implement Entity model with health tracking"  
claude implement T022 "Implement CommitAnalysis model"
```

## Task Validation Checklist
- [x] **All contract files have corresponding test tasks**
  - api-contracts.md → T008-T011
  - extension-contracts.md → T012-T013
- [x] **All entities have model creation tasks**
  - User → T019, Repository → T020, Entity → T021, CommitAnalysis → T022
- [x] **All major endpoints implemented**
  - Auth → T033, Repositories → T034, Entities → T035, Analysis → T036
- [x] **TDD approach maintained**
  - All tests (T008-T017) before implementation (T018+)
- [x] **Parallel execution maximized**
  - Independent files marked [P], dependent tasks sequential

---

**Total Tasks**: 62  
**Parallel Tasks**: 31  
**Critical Path**: T001 → T003 → T018 → T019 → T026 → T033 → T043  
**Estimated Completion**: 2-3 weeks for full implementation

Ready for task execution with `/implement` commands.