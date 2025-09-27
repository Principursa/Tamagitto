# Phase 1: Data Model Design

**Feature**: Tamagitto Developer Monitoring Tamagotchi  
**Date**: 2025-09-27  
**Dependencies**: research.md technical decisions

## Entity Relationship Diagram

```
User ||--o{ Repository : monitors
Repository ||--|| Entity : has_one
Repository ||--o{ CommitAnalysis : generates
Entity ||--o{ HealthHistory : tracks
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    github_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    access_token_encrypted TEXT NOT NULL,  -- AES-256-GCM encrypted
    encryption_key_hash VARCHAR(64) NOT NULL,  -- For key derivation
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_users_last_active ON users(last_active);
```

### Repositories Table  
```sql
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    github_repo_id BIGINT NOT NULL,
    full_name VARCHAR(255) NOT NULL,  -- e.g., "username/repo-name"
    default_branch VARCHAR(100) DEFAULT 'main',
    language VARCHAR(50),  -- Primary language for entity type selection
    private BOOLEAN DEFAULT false,
    monitoring_active BOOLEAN DEFAULT true,
    webhook_id VARCHAR(50),  -- GitHub webhook ID if configured
    last_commit_sha VARCHAR(40),
    last_monitored_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_repositories_user_github ON repositories(user_id, github_repo_id);
CREATE INDEX idx_repositories_monitoring ON repositories(monitoring_active, last_monitored_at);
```

### Entities Table
```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- 'pet', 'plant', 'robot', 'golem', 'blob'
    name VARCHAR(100),  -- User-assigned or generated name
    health_score INTEGER DEFAULT 100 CHECK (health_score >= 0 AND health_score <= 100),
    visual_url TEXT NOT NULL,  -- URL to current entity image
    visual_urls_json JSON,  -- Different health state images
    status VARCHAR(20) DEFAULT 'alive',  -- 'alive', 'dying', 'dead'
    metadata_json JSON,  -- Entity-specific attributes, preferences
    death_date TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_entities_repository ON entities(repository_id);
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_entities_health ON entities(health_score);
```

### Commit Analyses Table
```sql
CREATE TABLE commit_analyses (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    commit_sha VARCHAR(40) NOT NULL,
    commit_message TEXT,
    author_login VARCHAR(100),
    committed_at TIMESTAMP NOT NULL,
    
    -- Quality metrics
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    complexity_score DECIMAL(5,2),
    test_coverage_delta DECIMAL(5,2),
    documentation_score DECIMAL(5,2),
    linting_violations INTEGER DEFAULT 0,
    security_issues INTEGER DEFAULT 0,
    
    -- Calculated scores
    overall_quality_score DECIMAL(5,2) NOT NULL,
    health_delta INTEGER NOT NULL,  -- Impact on entity health (-20 to +20)
    
    analysis_json JSON,  -- Detailed analysis from agents
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_commit_analyses_repo_sha ON commit_analyses(repository_id, commit_sha);
CREATE INDEX idx_commit_analyses_committed_at ON commit_analyses(repository_id, committed_at DESC);
CREATE INDEX idx_commit_analyses_quality ON commit_analyses(overall_quality_score);
```

### Health History Table
```sql
CREATE TABLE health_history (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    health_score INTEGER NOT NULL CHECK (health_score >= 0 AND health_score <= 100),
    change_reason VARCHAR(100),  -- 'commit_analysis', 'daily_decay', 'manual_reset'
    commit_analysis_id INTEGER REFERENCES commit_analyses(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_history_entity_time ON health_history(entity_id, created_at DESC);
CREATE INDEX idx_health_history_reason ON health_history(change_reason);
```

### User Sessions Table
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(128) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
```

## SQLAlchemy Models

### Base Model
```python
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### User Model
```python
from sqlalchemy import String, Text, Boolean
from cryptography.fernet import Fernet

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    github_id = Column(String(50), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(255))
    access_token_encrypted = Column(Text, nullable=False)
    encryption_key_hash = Column(String(64), nullable=False)
    avatar_url = Column(Text)
    last_active = Column(DateTime, default=func.now())
    
    # Relationships
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def encrypt_token(self, token: str, key: bytes) -> None:
        f = Fernet(key)
        self.access_token_encrypted = f.encrypt(token.encode()).decode()
    
    def decrypt_token(self, key: bytes) -> str:
        f = Fernet(key)
        return f.decrypt(self.access_token_encrypted.encode()).decode()
```

### Repository Model
```python
class Repository(Base, TimestampMixin):
    __tablename__ = 'repositories'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    github_repo_id = Column(BigInteger, nullable=False)
    full_name = Column(String(255), nullable=False)
    default_branch = Column(String(100), default='main')
    language = Column(String(50))
    private = Column(Boolean, default=False)
    monitoring_active = Column(Boolean, default=True)
    webhook_id = Column(String(50))
    last_commit_sha = Column(String(40))
    last_monitored_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="repositories")
    entity = relationship("Entity", back_populates="repository", uselist=False)
    commit_analyses = relationship("CommitAnalysis", back_populates="repository")
```

### Entity Model
```python
from sqlalchemy.dialects.postgresql import JSON

class Entity(Base, TimestampMixin):
    __tablename__ = 'entities'
    
    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, ForeignKey('repositories.id'), nullable=False)
    entity_type = Column(String(50), nullable=False)
    name = Column(String(100))
    health_score = Column(Integer, default=100)
    visual_url = Column(Text, nullable=False)
    visual_urls_json = Column(JSON)
    status = Column(String(20), default='alive')
    metadata_json = Column(JSON, default={})
    death_date = Column(DateTime)
    
    # Relationships
    repository = relationship("Repository", back_populates="entity")
    health_history = relationship("HealthHistory", back_populates="entity")
    
    @property
    def is_alive(self) -> bool:
        return self.status == 'alive'
    
    @property  
    def health_status(self) -> str:
        if self.health_score >= 80:
            return 'thriving'
        elif self.health_score >= 60:
            return 'healthy' 
        elif self.health_score >= 40:
            return 'okay'
        elif self.health_score >= 20:
            return 'poor'
        else:
            return 'dying'
```

## Data Access Patterns

### Repository Queries
```python
# Get active repositories for monitoring
def get_active_repositories():
    return session.query(Repository)\
        .filter(Repository.monitoring_active == True)\
        .options(joinedload(Repository.entity))\
        .all()

# Get repository with latest commit analysis  
def get_repository_with_latest_analysis(repo_id: int):
    return session.query(Repository)\
        .filter(Repository.id == repo_id)\
        .options(
            joinedload(Repository.entity),
            joinedload(Repository.commit_analyses.limit(1))
        ).first()
```

### Health Tracking Queries
```python
# Get entity health trends (last 30 days)
def get_health_trends(entity_id: int, days: int = 30):
    cutoff = datetime.utcnow() - timedelta(days=days)
    return session.query(HealthHistory)\
        .filter(
            HealthHistory.entity_id == entity_id,
            HealthHistory.created_at >= cutoff
        )\
        .order_by(HealthHistory.created_at.desc())\
        .all()

# Get entities needing health decay
def get_entities_for_decay():
    cutoff = datetime.utcnow() - timedelta(days=3)  # Grace period
    return session.query(Entity)\
        .join(Repository)\
        .filter(
            Entity.status == 'alive',
            Repository.last_monitored_at < cutoff
        ).all()
```

## Data Validation Rules

### Business Logic Constraints
1. **One Entity Per Repository**: Enforced by unique index on repository_id
2. **Health Score Bounds**: 0-100 range enforced by CHECK constraint
3. **Entity Lifecycle**: Dead entities cannot have health updates
4. **Commit Uniqueness**: One analysis per commit SHA per repository
5. **Session Expiration**: Expired sessions automatically cleaned up

### Data Integrity
- **Foreign Key Cascades**: User deletion removes all related data
- **Enum Validation**: Entity status and types validated at application level
- **Timestamp Consistency**: All timestamps in UTC
- **Token Security**: GitHub tokens never stored in plain text

## Migration Strategy

### Initial Schema Creation
```python
# Alembic migration: create_initial_tables.py
def upgrade():
    # Create all tables with proper indexes and constraints
    # Set up initial data (entity types, default configurations)
    pass

def downgrade():
    # Safe rollback procedures
    # Preserve user data where possible
    pass
```

### Future Schema Changes
- **Additive Changes**: New columns with defaults, new optional tables
- **Breaking Changes**: Multi-step migrations with data preservation
- **Index Optimization**: Monitor query performance and add indexes as needed

## Phase 1 Data Model Complete

All entities, relationships, and access patterns defined. Ready for API contract design.