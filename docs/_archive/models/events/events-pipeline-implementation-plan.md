# Events Pipeline Implementation Plan — Phase 1 Foundation

**Version:** 1.0
**Date:** 2025-10-17
**Status:** Execution Plan
**Prerequisites:** Events model complete (✅), TimestampMixin ready (✅)

---

## Purpose

This document provides a step-by-step implementation plan to complete the **Events pipeline** in Elephantasm's Phase 1 Foundation. Upon completion, you will have a fully functional Events API that can ingest, store, retrieve, and manage event data—the atomic foundation of the LTAM system.

---

## Overview: What We're Building

```
External System
      ↓
POST /api/v1/events (FastAPI endpoint)
      ↓
EventOperations.create() (domain logic)
      ↓
PostgreSQL events table (via asyncpg)
      ↓
GET /api/v1/events (retrieval)
      ↓
EventRead DTO (response)
```

**End State:** A working Events API that accepts event ingestion, stores them in PostgreSQL with proper relationships, and retrieves them efficiently.

---

## Implementation Steps

### Step 1: Spirits Model (15 minutes)

**File:** `backend/app/models/database/spirits.py`

**Purpose:** Create the Spirit entity that represents an agent/owner. Events are owned by Spirits via `agent_id` foreign key.

**Current State:** File exists but is empty (1 line)

#### 1.1 Design Decisions

**Naming:** "Spirit" not "Agent"
- Aligns with Elephantasm's conceptual framework
- `spirit_id` is the owner identifier throughout the system
- Table name: `spirits`

**Minimal Alpha Scope:**
- `id` (UUID, primary key)
- `name` (string, required) - Human-readable identifier
- `description` (text, optional) - Brief description of the spirit
- `metadata` (JSONB, optional) - Flexible structured data
- `created_at`, `updated_at` (from TimestampMixin)
- `is_deleted` (boolean, soft delete)

**No Organization/User FK Yet:**
- Simplifying multi-tenancy for alpha
- Phase 2 will add `organization_id` when adding user auth
- For now: each Spirit is independent

#### 1.2 Implementation

```python
"""Spirits model - the agent/owner entity in Elephantasm."""

from uuid import UUID
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel, Relationship

from backend.app.models.database.mixins.timestamp import TimestampMixin


class SpiritBase(SQLModel):
    """Shared fields for Spirit model."""
    name: str = Field(max_length=255, description="Human-readable spirit name")
    description: str | None = Field(default=None, nullable=True, description="Brief description")
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB))


class Spirit(SpiritBase, TimestampMixin, table=True):
    """Spirit entity - represents an agent/owner of memories."""
    __tablename__ = "spirits"

    id: UUID = Field(default=None, primary_key=True, sa_column_kwargs={"server_default": text("gen_random_uuid()")})
    is_deleted: bool = Field(default=False)

    # Relationships (will be populated as we add models)
    # events: list["Event"] = Relationship(back_populates="spirit")
    # memories: list["Memory"] = Relationship(back_populates="spirit")


class SpiritCreate(SpiritBase):
    """Data required to create a Spirit."""
    pass


class SpiritRead(SpiritBase):
    """Data returned when reading a Spirit."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class SpiritUpdate(SQLModel):
    """Fields that can be updated."""
    name: str | None = None
    description: str | None = None
    metadata: dict | None = None
    is_deleted: bool | None = None
```

**Key Patterns Applied:**
- ✅ DB-level UUID generation (same as Events)
- ✅ TimestampMixin integration
- ✅ Base + Table + DTOs pattern
- ✅ JSONB metadata for flexibility
- ✅ Soft deletes
- ✅ Relationships commented out (Events model exists but relationship not yet wired)

#### 1.3 Update Events Model

Once Spirit model exists, update `backend/app/models/database/events.py` to reference it:

```python
# At top, add import
from backend.app.models.database.spirits import Spirit

# In EventBase, update foreign key
agent_id: UUID = Field(foreign_key="spirits.id", index=True, description="Owner spirit ID")

# In Event class, uncomment/add relationship
spirit: Spirit = Relationship(back_populates="events")
```

**Deliverable:** ✅ `spirits.py` complete, Events model updated with FK reference

---

### Step 2: Database Configuration (20 minutes)

**Files:**
- `backend/app/core/config.py` - Environment settings
- `backend/app/core/database.py` - Async engine and session factory

#### 2.1 Configuration Settings

**File:** `backend/app/core/config.py`

```python
"""Application configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/elephantasm"
    DATABASE_ECHO: bool = False  # Set to True to log all SQL queries

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True  # Dev mode auto-reload

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]  # Frontend URL

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


# Global settings instance
settings = Settings()
```

**Environment Variables (.env):**
```bash
# Database (asyncpg driver for async SQLAlchemy)
DATABASE_URL=postgresql+asyncpg://elephantasm:dev_password@localhost:5432/elephantasm

# Development
DATABASE_ECHO=true
API_RELOAD=true
LOG_LEVEL=DEBUG

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

#### 2.2 Async Database Engine

**File:** `backend/app/core/database.py`

```python
"""Async database engine and session management."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,  # Log SQL if enabled
    poolclass=NullPool,  # Disable connection pooling (rely on pgBouncer if needed)
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Explicit flush control
    autocommit=False,  # Explicit commit control
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting an async database session.

    Usage in FastAPI routes:
        @router.post("/events")
        async def create_event(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on error
            raise
        finally:
            await session.close()
```

**Key Decisions:**

1. **NullPool** - Disable SQLAlchemy connection pooling
   - Rationale: If using pgBouncer (transaction pooling), SQLAlchemy pooling adds overhead
   - For local dev without pgBouncer, connections are short-lived anyway
   - Simplifies connection lifecycle

2. **expire_on_commit=False** - Keep objects accessible after commit
   - Rationale: Avoids lazy-load issues when returning objects from routes
   - Objects remain usable without re-querying

3. **autoflush=False, autocommit=False** - Explicit control
   - Rationale: Domain operations call `flush()` when needed for generated IDs
   - Routes handle `commit()` via dependency lifecycle
   - Prevents accidental commits in business logic

4. **Auto-commit in dependency** - Routes don't need to call `commit()`
   - Rationale: Success path commits automatically
   - Error path rolls back automatically
   - Cleaner route code

**Deliverable:** ✅ Config and database modules ready for use

---

### Step 3: Alembic Migrations (25 minutes)

**Purpose:** Create database schema for `spirits` and `events` tables with proper indexes.

#### 3.1 Alembic Setup

**File:** `backend/alembic.ini`

```ini
[alembic]
script_location = backend/migrations
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = postgresql+asyncpg://elephantasm:dev_password@localhost:5432/elephantasm

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**File:** `backend/migrations/env.py`

```python
"""Alembic environment configuration for async migrations."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import settings
from backend.app.core.config import settings

# Import all models for autogenerate
from backend.app.models.database.spirits import Spirit
from backend.app.models.database.events import Event
from backend.app.models.database.mixins.timestamp import TimestampMixin

# Import SQLModel's metadata
from sqlmodel import SQLModel

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL.replace("+asyncpg", "")  # Remove async driver for offline
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode (async)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

#### 3.2 Create Initial Migration

**Command:**
```bash
cd backend
alembic revision --autogenerate -m "initial schema - spirits and events"
```

**File:** `backend/migrations/versions/001_initial_schema.py` (generated, then enhanced)

```python
"""initial schema - spirits and events

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create spirits table
    op.create_table(
        'spirits',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_spirits_name', 'spirits', ['name'])

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('meta_summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('source_uri', sa.Text(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=255), nullable=True),
        sa.Column('importance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['agent_id'], ['spirits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('importance_score >= 0.0 AND importance_score <= 1.0', name='ck_events_importance_score')
    )

    # Indexes for events table
    op.create_index('idx_events_agent_id', 'events', ['agent_id'])
    op.create_index('idx_events_event_type', 'events', ['event_type'])
    op.create_index('idx_events_session_id', 'events', ['session_id'], postgresql_where=sa.text('session_id IS NOT NULL'))
    op.create_index('idx_events_dedupe_key', 'events', ['dedupe_key'], unique=True, postgresql_where=sa.text('dedupe_key IS NOT NULL'))
    op.create_index('idx_events_occurred_at', 'events', [sa.text('occurred_at DESC')], postgresql_where=sa.text('occurred_at IS NOT NULL'))
    op.create_index('idx_events_created_at', 'events', [sa.text('created_at DESC')])


def downgrade() -> None:
    op.drop_table('events')
    op.drop_table('spirits')
```

**Run Migration:**
```bash
alembic upgrade head
```

**Deliverable:** ✅ Database tables created with proper indexes

---

### Step 4: EventOperations - Domain Logic (30 minutes)

**File:** `backend/app/domain/event_operations.py`

**Purpose:** Business logic for Event CRUD operations. No commits—routes handle transactions.

```python
"""Domain operations for Events - business logic layer."""

from datetime import datetime, timezone
from uuid import UUID
import hashlib

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.database.events import Event, EventCreate, EventUpdate, EventType
from backend.app.models.database.spirits import Spirit


class EntityNotFoundError(Exception):
    """Raised when an entity is not found."""
    pass


class EventOperations:
    """Business logic for Event operations."""

    @staticmethod
    async def create(db: AsyncSession, data: EventCreate) -> Event:
        """
        Create a new event.

        Args:
            db: Database session
            data: Event creation data

        Returns:
            Created Event instance

        Raises:
            EntityNotFoundError: If spirit doesn't exist
        """
        # Validate spirit exists
        spirit = await db.get(Spirit, data.agent_id)
        if not spirit:
            raise EntityNotFoundError(f"Spirit {data.agent_id} not found")

        # Default occurred_at to current time if not provided
        if not data.occurred_at:
            data.occurred_at = datetime.now(timezone.utc)

        # Auto-generate dedupe_key if source_uri provided but no dedupe_key
        if data.source_uri and not data.dedupe_key:
            data.dedupe_key = EventOperations._generate_dedupe_key(data)

        # Create event
        event = Event.model_validate(data)
        db.add(event)
        await db.flush()  # Get generated ID

        return event

    @staticmethod
    async def get_by_id(db: AsyncSession, event_id: UUID) -> Event | None:
        """Get an event by ID."""
        return await db.get(Event, event_id)

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
        include_deleted: bool = False
    ) -> list[Event]:
        """
        Get recent events for a spirit.

        Args:
            db: Database session
            agent_id: Spirit UUID
            limit: Maximum number of results
            offset: Pagination offset
            event_type: Optional filter by event type
            include_deleted: Whether to include soft-deleted events

        Returns:
            List of Event instances, ordered by occurred_at DESC
        """
        query = select(Event).where(Event.agent_id == agent_id)

        if not include_deleted:
            query = query.where(Event.is_deleted == False)

        if event_type:
            query = query.where(Event.event_type == event_type)

        query = (
            query
            .order_by(Event.occurred_at.desc(), Event.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        agent_id: UUID,
        session_id: str,
        include_deleted: bool = False
    ) -> list[Event]:
        """
        Get all events in a session, chronologically ordered.

        Args:
            db: Database session
            agent_id: Spirit UUID
            session_id: Session identifier
            include_deleted: Whether to include soft-deleted events

        Returns:
            List of Event instances, ordered chronologically (ASC)
        """
        conditions = [
            Event.agent_id == agent_id,
            Event.session_id == session_id
        ]

        if not include_deleted:
            conditions.append(Event.is_deleted == False)

        result = await db.execute(
            select(Event)
            .where(and_(*conditions))
            .order_by(Event.occurred_at.asc(), Event.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_by_agent(
        db: AsyncSession,
        agent_id: UUID,
        event_type: str | None = None,
        include_deleted: bool = False
    ) -> int:
        """Count events for a spirit."""
        query = select(func.count()).select_from(Event).where(Event.agent_id == agent_id)

        if not include_deleted:
            query = query.where(Event.is_deleted == False)

        if event_type:
            query = query.where(Event.event_type == event_type)

        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def update(db: AsyncSession, event_id: UUID, data: EventUpdate) -> Event:
        """
        Update an event.

        Args:
            db: Database session
            event_id: Event UUID
            data: Update data

        Returns:
            Updated Event instance

        Raises:
            EntityNotFoundError: If event doesn't exist
        """
        event = await db.get(Event, event_id)
        if not event:
            raise EntityNotFoundError(f"Event {event_id} not found")

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)

        await db.flush()
        return event

    @staticmethod
    async def update_meta_summary(
        db: AsyncSession,
        event_id: UUID,
        meta_summary: str
    ) -> Event:
        """Update meta_summary for an event (populated by Cortex)."""
        return await EventOperations.update(
            db,
            event_id,
            EventUpdate(meta_summary=meta_summary)
        )

    @staticmethod
    async def update_importance(
        db: AsyncSession,
        event_id: UUID,
        importance_score: float
    ) -> Event:
        """Update importance_score for an event."""
        return await EventOperations.update(
            db,
            event_id,
            EventUpdate(importance_score=importance_score)
        )

    @staticmethod
    async def soft_delete(db: AsyncSession, event_id: UUID) -> Event:
        """Soft delete an event."""
        return await EventOperations.update(
            db,
            event_id,
            EventUpdate(is_deleted=True)
        )

    @staticmethod
    def _generate_dedupe_key(data: EventCreate) -> str:
        """
        Generate idempotent dedupe key from event data.

        Uses first 100 chars of content + metadata to avoid hashing huge strings.
        """
        parts = [
            str(data.agent_id),
            data.event_type,
            data.content[:100],  # First 100 chars
            str(data.occurred_at),
            data.source_uri or ""
        ]
        hash_input = "|".join(parts).encode()
        return hashlib.sha256(hash_input).hexdigest()[:32]
```

**Key Patterns:**

1. **No Commits** - Business logic doesn't commit; routes handle transactions
2. **Flush After Insert** - Get generated ID mid-transaction
3. **Validation** - Check FK references exist
4. **Defaults** - Apply occurred_at default if not provided
5. **Ordering** - DESC for recent, ASC for chronological sessions
6. **Soft Deletes** - Filter `is_deleted=False` by default

**Deliverable:** ✅ EventOperations class with full CRUD

---

### Step 5: API Endpoints (25 minutes)

**File:** `backend/app/api/v1/endpoints/events.py`

```python
"""API endpoints for Events."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_db
from backend.app.domain.event_operations import EventOperations, EntityNotFoundError
from backend.app.models.database.events import EventCreate, EventRead, EventUpdate


router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
    description="Ingest a new event into the system. Minimal requirements: agent_id, event_type, content."
)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Create a new event."""
    try:
        event = await EventOperations.create(db, data)
        # Commit handled by get_db dependency
        return EventRead.model_validate(event)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IntegrityError as e:
        # Likely duplicate dedupe_key
        raise HTTPException(status_code=409, detail="Duplicate event (dedupe_key conflict)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/",
    response_model=list[EventRead],
    summary="List events",
    description="Retrieve events for a spirit, with optional filters."
)
async def list_events(
    agent_id: UUID = Query(..., description="Spirit UUID to filter by"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: str | None = Query(None, description="Filter by event type"),
    session_id: str | None = Query(None, description="Filter by session ID"),
    db: AsyncSession = Depends(get_db)
) -> list[EventRead]:
    """List events with filters."""
    if session_id:
        # Session-specific query (chronological order)
        events = await EventOperations.get_by_session(db, agent_id, session_id)
    else:
        # General query (recent-first order)
        events = await EventOperations.get_recent(
            db, agent_id, limit, offset, event_type
        )

    return [EventRead.model_validate(event) for event in events]


@router.get(
    "/{event_id}",
    response_model=EventRead,
    summary="Get event by ID",
    description="Retrieve a specific event by its UUID."
)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Get a specific event."""
    event = await EventOperations.get_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    return EventRead.model_validate(event)


@router.patch(
    "/{event_id}",
    response_model=EventRead,
    summary="Update event",
    description="Update mutable fields on an event (metadata, importance_score, meta_summary, is_deleted)."
)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Update an event."""
    try:
        event = await EventOperations.update(db, event_id, data)
        return EventRead.model_validate(event)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete event",
    description="Mark an event as deleted (soft delete)."
)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Soft delete an event."""
    try:
        await EventOperations.soft_delete(db, event_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**Wire up in main router:**

**File:** `backend/app/api/v1/api.py`

```python
"""API v1 router aggregation."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import events

api_router = APIRouter()

api_router.include_router(events.router)
```

**File:** `backend/app/api/__init__.py` (or update existing)

```python
"""API module initialization."""

from fastapi import FastAPI
from backend.app.api.v1.api import api_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Elephantasm LTAM API",
        description="Long-Term Agentic Memory framework",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Include API v1 routes
    app.include_router(api_router, prefix="/api/v1")

    return app
```

**File:** `backend/main.py` (entry point)

```python
"""Main application entry point."""

import uvicorn
from backend.app.api import create_app

app = create_app()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Elephantasm LTAM API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

**Deliverable:** ✅ Full REST API for Events

---

### Step 6: Quick Test & Validation (15 minutes)

**Purpose:** Validate the entire pipeline works end-to-end.

#### 6.1 Manual API Test

**Start the server:**
```bash
cd backend
python main.py
```

**Visit Swagger UI:** http://localhost:8000/docs

**Test sequence:**

1. **Create a Spirit:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/spirits" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "TestSpirit",
       "description": "A test spirit for validation"
     }'
   ```
   Copy the returned `id` (spirit UUID)

2. **Create an Event:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/events" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "<SPIRIT_UUID>",
       "event_type": "message.in",
       "content": "Hello, Elephantasm!",
       "session_id": "test_session_001"
     }'
   ```

3. **List Events:**
   ```bash
   curl "http://localhost:8000/api/v1/events?agent_id=<SPIRIT_UUID>"
   ```

4. **Get Specific Event:**
   ```bash
   curl "http://localhost:8000/api/v1/events/<EVENT_UUID>"
   ```

5. **Update Event:**
   ```bash
   curl -X PATCH "http://localhost:8000/api/v1/events/<EVENT_UUID>" \
     -H "Content-Type: application/json" \
     -d '{
       "importance_score": 0.8,
       "meta_summary": "greeting message"
     }'
   ```

#### 6.2 Unit Test (Optional but Recommended)

**File:** `backend/tests/test_event_operations.py`

```python
"""Unit tests for EventOperations."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from backend.app.models.database.spirits import Spirit, SpiritCreate
from backend.app.models.database.events import Event, EventCreate
from backend.app.domain.event_operations import EventOperations, EntityNotFoundError


# Test database setup
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/elephantasm_test"

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_event(db_session):
    """Test creating an event."""
    # Create spirit first
    spirit = Spirit(name="TestSpirit")
    db_session.add(spirit)
    await db_session.commit()

    # Create event
    event_data = EventCreate(
        agent_id=spirit.id,
        event_type="message.in",
        content="Test message"
    )

    event = await EventOperations.create(db_session, event_data)
    await db_session.commit()

    assert event.id is not None
    assert event.agent_id == spirit.id
    assert event.content == "Test message"
    assert event.occurred_at is not None  # Should be defaulted


@pytest.mark.asyncio
async def test_create_event_invalid_spirit(db_session):
    """Test creating event with non-existent spirit."""
    event_data = EventCreate(
        agent_id=uuid4(),  # Random UUID
        event_type="message.in",
        content="Test"
    )

    with pytest.raises(EntityNotFoundError):
        await EventOperations.create(db_session, event_data)


@pytest.mark.asyncio
async def test_get_by_session(db_session):
    """Test retrieving events by session."""
    # Create spirit
    spirit = Spirit(name="TestSpirit")
    db_session.add(spirit)
    await db_session.commit()

    # Create multiple events in same session
    session_id = "test_session_001"
    for i in range(3):
        event_data = EventCreate(
            agent_id=spirit.id,
            event_type="message.in",
            content=f"Message {i}",
            session_id=session_id
        )
        await EventOperations.create(db_session, event_data)

    await db_session.commit()

    # Retrieve by session
    events = await EventOperations.get_by_session(db_session, spirit.id, session_id)

    assert len(events) == 3
    assert events[0].content == "Message 0"  # Chronological order
```

**Run tests:**
```bash
pytest backend/tests/ -v
```

**Deliverable:** ✅ Working Events API validated

---

## Success Criteria

### ✅ Step 1: Spirits Model
- [ ] `spirits.py` created with Base + Table + DTOs
- [ ] DB-level UUID generation
- [ ] TimestampMixin integrated
- [ ] Events model updated with FK reference

### ✅ Step 2: Database Config
- [ ] `config.py` with Pydantic Settings
- [ ] `database.py` with async engine and session factory
- [ ] `.env` file with DATABASE_URL

### ✅ Step 3: Migrations
- [ ] Alembic configured for async
- [ ] Initial migration created
- [ ] Migration run successfully (`alembic upgrade head`)
- [ ] Tables exist in PostgreSQL

### ✅ Step 4: EventOperations
- [ ] `event_operations.py` with full CRUD
- [ ] No commits in business logic
- [ ] Proper error handling
- [ ] Helper methods for common queries

### ✅ Step 5: API Endpoints
- [ ] `events.py` router created
- [ ] POST, GET, PATCH, DELETE endpoints
- [ ] Swagger docs accessible at `/docs`
- [ ] Proper HTTP status codes

### ✅ Step 6: Testing
- [ ] Manual API tests pass
- [ ] Can create spirit
- [ ] Can create event
- [ ] Can list events
- [ ] Can retrieve specific event
- [ ] Can update event

---

## Time Estimate

| Step | Task | Estimated Time |
|------|------|----------------|
| 1 | Spirits Model | 15 minutes |
| 2 | Database Config | 20 minutes |
| 3 | Alembic Migrations | 25 minutes |
| 4 | EventOperations | 30 minutes |
| 5 | API Endpoints | 25 minutes |
| 6 | Testing | 15 minutes |
| **Total** | | **~2 hours** |

**Note:** Time assumes familiarity with FastAPI, SQLAlchemy, and Alembic. First-time setup may take longer.

---

## Next Steps After Completion

Once the Events pipeline is complete, you have several options:

### Option A: Build Spirits API
Add full CRUD endpoints for Spirits (similar to Events)

### Option B: Add LLM Service
Create `backend/app/services/llm_service.py` for OpenAI/Anthropic integration

### Option C: Implement Memories Model
Move to the next layer: Event → Memory transformation

### Option D: Add Frontend Integration
Build UI components to visualize events

**Recommended:** Option C (Memories Model) - Completes the first transformation layer of the LTAM pipeline.

---

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/db`
- Ensure database exists: `createdb elephantasm`

### Import Errors
- Check `PYTHONPATH` includes project root
- Verify `__init__.py` files exist in all packages
- Use absolute imports: `from backend.app.models...`

### Migration Errors
- Drop and recreate database if schema is corrupted
- Check `alembic.ini` has correct database URL
- Verify all models are imported in `migrations/env.py`

### Async/Await Issues
- Ensure all database operations use `await`
- Use `AsyncSession`, not `Session`
- FastAPI route functions must be `async def`

---

## Summary

This plan provides a complete, step-by-step implementation guide for building the Events pipeline in Elephantasm. Upon completion, you will have:

✅ **Spirits model** - Owner/agent entity
✅ **Events model** - Atomic experience units (already done)
✅ **Async database layer** - PostgreSQL with asyncpg
✅ **Alembic migrations** - Schema management
✅ **EventOperations** - Domain logic
✅ **REST API** - Full CRUD endpoints
✅ **Working system** - Validated end-to-end

**Foundation complete.** Ready to build the transformation pipeline: Events → Memories → Lessons → Knowledge → Identity.

---

*"First make it work, then make it right, then make it fast."* — Kent Beck
