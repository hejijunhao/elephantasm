# Elephantasm Architecture & Implementation Plan

**Version:** 1.0
**Date:** 2025-10-17
**Status:** Draft

---

## Executive Summary

This document outlines the comprehensive architecture and implementation plan for Elephantasm, a Long-Term Agentic Memory (LTAM) framework. The plan is informed by proven patterns from the Marlin platform while adapting and modernizing them for Elephantasm's unique requirements.

**Key Decisions:**
- Adopt Marlin's domain-driven layering (Models → Domain Ops → API Routes)
- Simplify multi-tenancy approach for initial MVP
- Add event sourcing for memory transformation tracking
- Build async-first where beneficial
- Include background job system from the start (for Dreamer)
- Integrate vector embeddings alongside structured queries

---

## Table of Contents

1. [Architecture Principles](#architecture-principles)
2. [What We're Adopting from Marlin](#what-were-adopting-from-marlin)
3. [What We're Changing or Simplifying](#what-were-changing-or-simplifying)
4. [Modern Enhancements](#modern-enhancements)
5. [System Architecture](#system-architecture)
6. [Backend Architecture](#backend-architecture)
7. [Frontend Architecture](#frontend-architecture)
8. [Database Design](#database-design)
9. [Implementation Roadmap](#implementation-roadmap)
10. [File Structure](#file-structure)

---

## Architecture Principles

### Core Principles (from Elephantasm Vision)

1. **Continuity + Context** — Short-term awareness meets long-term memory
2. **Structure + Similarity** — Relational metadata + vector embeddings
3. **Determinism with Flexibility** — Clear transformation rules, adaptive prioritization
4. **Curation post-Accumulation** — Save everything first, refine later
5. **Composability over Complexity** — Easy integration into any agentic system
6. **Identity as Emergence** — Behavioral fingerprint evolves from aggregated Lessons/Knowledge

### Engineering Principles (from Marlin + Modern Best Practices)

1. **Layered Architecture** — Clear separation of concerns
2. **Domain-Driven Design** — Business logic isolated from infrastructure
3. **Async-First** — Non-blocking operations for LLM calls, background jobs
4. **Type Safety** — TypeScript frontend, Pydantic/SQLModel backend
5. **Observability** — Structured logging, tracing, metrics from day one
6. **Testability** — Design for testing; comprehensive test coverage
7. **API-First** — Well-documented, versioned REST API
8. **Developer Experience** — Easy local setup, clear documentation

---

## What We're Adopting from Marlin

### ✅ Core Patterns

| Pattern | Rationale | Implementation |
|---------|-----------|----------------|
| **Domain Operations** | Pure business logic without commits; routes manage transactions | `backend/app/domain/` |
| **SQLModel** | Combined validation + ORM in one model | All entity models |
| **Pydantic Settings** | Type-safe configuration management | `backend/app/core/config.py` |
| **Structured Logging** | Category-based logging (api, db, cache, workflow) | Loguru with custom formatters |
| **API Versioning** | `/api/v1/` prefix for future-proofing | Route organization |
| **DTO Pattern** | Separate Create/Read/Update DTOs per entity | All models |
| **Workflow Registry** | Lazy-loaded orchestrators to avoid import cycles | `backend/app/workflows/registry.py` |
| **Base API Client** | Unified frontend client with auth, error handling | `frontend/src/lib/api.ts` |
| **Type Mirroring** | Frontend TypeScript types match backend models | `frontend/src/types/` |

### ✅ Directory Structure Philosophy

```
backend/
├── app/
│   ├── api/v1/              # HTTP layer - routes by resource
│   ├── core/                # Config, database, auth, logging
│   ├── models/              # SQLModel entities + DTOs
│   ├── domain/              # Business logic operations
│   ├── services/            # External integrations, helpers
│   └── workflows/           # LLM workflows, orchestration
├── migrations/              # Alembic
├── tests/                   # Pytest
└── main.py                  # App entry point
```

This structure scales well and maintains clear boundaries.

### ✅ Development Practices

- Environment variables via `.env` with `.env.example`
- Alembic migrations for schema management
- Health check endpoints (`/health`, `/healthz`)
- Middleware for logging, CORS, gzip
- Comprehensive README per component

---

## What We're Changing or Simplifying

### 🔄 Multi-Tenancy Approach

**Marlin:** Heavy RLS (Row-Level Security) with dual database connections, per-request session variables, enterprise context everywhere.

**Elephantasm:** Simpler initial approach:
- **Phase 1 (MVP):** Single-tenant or namespace-based isolation via `agent_id` foreign key
- **Phase 2:** Introduce user accounts with basic RBAC (owner/member)
- **Phase 3:** Full multi-tenant with RLS if needed for cloud offering

**Rationale:** Elephantasm is primarily a framework/library first, SaaS second. Start simple, add complexity when validated.

**Implementation:**
- Models include `agent_id: UUID` (identifies which agent instance owns the data)
- No dual DB connections initially
- Standard SQLAlchemy session management
- Auth optional for MVP (can add JWT later)

### 🔄 Caching Strategy

**Marlin:** Upstash Redis with TTL configuration, cache invalidation patterns, ETag client caching.

**Elephantasm:** Progressive caching:
- **Phase 1:** No caching (premature optimization)
- **Phase 2:** In-memory LRU cache for read-heavy reference data (ports, trade routes equivalent)
- **Phase 3:** Redis for distributed caching if scaling requires it

**Rationale:** Memory operations are write-heavy during accumulation; caching less critical initially. Add when performance testing shows need.

### 🔄 Authentication

**Marlin:** Supabase JWT with JWKS verification, strict ES256, payload caching.

**Elephantasm:**
- **Phase 1:** Optional API key authentication (simple bearer token for programmatic access)
- **Phase 2:** JWT with simple secret (not JWKS initially)
- **Phase 3:** Full Supabase/Auth0 integration if building SaaS UI

**Rationale:** Framework-first means many users will self-host or use programmatically. Keep auth simple and pluggable.

### 🔄 Frontend Complexity

**Marlin:** Edge middleware, SSR/CSR dual clients, complex auth flow.

**Elephantasm:**
- **Phase 1:** Simple dashboard for observability (CSR only, no SSR complexity)
- **Phase 2:** Add server components for performance where beneficial

**Rationale:** UI is secondary to API/SDK. Build iteratively based on user needs.

---

## Modern Enhancements

### 🚀 Event Sourcing for Memory Transformations

**Addition:** Track the provenance and transformation of every memory layer.

**Implementation:**
- `transformation_log` table: tracks Event → Memory → Lesson → Knowledge → Identity transformations
- Each transformation stores:
  - `source_id` (what it came from)
  - `source_type` (Event, Memory, Lesson, etc.)
  - `target_id` (what it became)
  - `target_type`
  - `transformation_type` (e.g., "reflection", "consolidation", "promotion")
  - `metadata` JSONB (LLM prompts, scores, reasoning)
  - `created_at`, `created_by_workflow`

**Benefits:**
- Full auditability: "Why does the agent believe X?"
- Debuggability: Trace any piece of knowledge back to source events
- Visualization: Show transformation graphs in UI
- Evaluation: Measure quality of transformations over time

### 🚀 Background Job System (Dreamer)

**Addition:** Built-in job queue for async curation, not just cron.

**Options:**
1. **APScheduler** (simple, in-process, good for MVP)
2. **Celery + Redis** (distributed, scales well)
3. **Dramatiq + RabbitMQ** (simpler than Celery, fast)

**Recommendation:** Start with APScheduler, migrate to Celery when scaling.

**Implementation:**
```python
# backend/app/jobs/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Dreamer jobs:
scheduler.add_job(
    curate_memories,
    trigger="interval",
    hours=6,
    args=[agent_id]
)

scheduler.add_job(
    promote_to_lessons,
    trigger="cron",
    hour=2,  # 2 AM daily
    args=[agent_id]
)
```

**Jobs:**
- `curate_memories`: Review recent memories, mark duplicates, merge similar
- `promote_to_lessons`: Cluster memories, extract patterns → Lessons
- `consolidate_knowledge`: Promote stable Lessons → Knowledge
- `update_identity`: Aggregate Knowledge → Identity dispositions
- `archive_stale`: Move old, irrelevant items to archive

### 🚀 Vector Embeddings + Hybrid Search

**Addition:** pgvector extension for similarity search alongside structured queries.

**Implementation:**
- All text-heavy entities (Memory, Lesson, Knowledge) have `embedding: Vector(1536)` column
- Generate embeddings on creation (OpenAI `text-embedding-3-small` or local model)
- Hybrid retrieval:
  ```python
  # Structured filter + vector similarity
  memories = (
      select(Memory)
      .where(Memory.agent_id == agent_id)
      .where(Memory.created_at >= cutoff_date)
      .order_by(Memory.embedding.cosine_distance(query_embedding))
      .limit(10)
  )
  ```

**Benefits:**
- Fast associative recall: "What do I know about X?"
- Semantic clustering in Dreamer
- Relevance scoring for Memory Pack compilation

### 🚀 Async-First FastAPI

**Enhancement:** Use async/await throughout where beneficial.

**Marlin:** Mix of sync and async; mostly sync domain operations.

**Elephantasm:** Async for:
- LLM API calls (OpenAI, Anthropic)
- Database operations (use `asyncpg` driver)
- Background job triggers
- External service calls

**Implementation:**
```python
# All domain operations
async def create_memory(
    db: AsyncSession,
    event_id: UUID,
    reflection: str
) -> Memory:
    ...

# All API routes
@router.post("/memories")
async def create_memory_endpoint(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent)
) -> MemoryRead:
    ...
```

**Rationale:** LLM calls are I/O-bound; async allows concurrent processing of multiple requests.

### 🚀 Comprehensive Testing from Day One

**Enhancement:** Test infrastructure as first-class citizen.

**Setup:**
- Pytest with async support (`pytest-asyncio`)
- Test database with fixtures
- Factory pattern for test data (`factory_boy`)
- Integration tests for workflows
- Mocked LLM calls for deterministic tests

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures
├── factories/               # Test data factories
├── unit/
│   ├── test_models.py
│   ├── test_domain_ops.py
│   └── test_transformations.py
├── integration/
│   ├── test_api.py
│   ├── test_workflows.py
│   └── test_dreamer.py
└── e2e/
    └── test_event_to_knowledge.py
```

### 🚀 OpenAPI / Swagger Auto-Documentation

**Enhancement:** Leverage FastAPI's built-in OpenAPI generation.

**Implementation:**
- Rich docstrings on all routes
- Pydantic models generate JSON schemas automatically
- Custom examples for complex payloads
- Swagger UI at `/docs`, ReDoc at `/redoc`

**Example:**
```python
@router.post(
    "/memories",
    response_model=MemoryRead,
    summary="Create a new memory",
    description="Transforms an Event into a structured Memory through LLM reflection",
    responses={
        201: {"description": "Memory created successfully"},
        400: {"description": "Invalid input"},
        404: {"description": "Event not found"}
    }
)
async def create_memory(...):
    """
    Create a Memory from an Event.

    This endpoint:
    1. Retrieves the source Event
    2. Generates a structured reflection via LLM
    3. Stores the Memory with metadata and provenance
    4. Returns the created Memory

    Example:
        {
            "event_id": "123e4567-e89b-12d3-a456-426614174000",
            "reflection_prompt": "Summarize the key insight from this interaction"
        }
    """
```

### 🚀 Docker Compose for Local Development

**Enhancement:** One-command local setup.

**docker-compose.yml:**
```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: elephantasm
      POSTGRES_USER: elephantasm
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://elephantasm:dev_password@postgres:5432/elephantasm
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app

volumes:
  postgres_data:
```

**Benefits:**
- New developers: `docker-compose up` and everything works
- Consistent environments
- Easy integration testing

---

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      External Systems                        │
│  (Agentic Frameworks, User Apps, SDKs, Direct API Calls)   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     Elephantasm API                          │
│                  FastAPI + REST + GraphQL                    │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌──────────────┐    ┌──────────────┐
│   Ingestion  │    │   Retrieval  │
│   Pipeline   │    │   Pipeline   │
└──────┬───────┘    └───────┬──────┘
       │                    │
       ▼                    ▼
┌─────────────────────────────────────┐
│       Domain Operations Layer       │
│  (Business Logic, Transformations)  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│         Storage Layer               │
│  PostgreSQL + pgvector              │
│  (Events, Memories, Lessons,        │
│   Knowledge, Identity, Transforms)  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│      Background Jobs (Dreamer)      │
│  (Curation, Consolidation,          │
│   Promotion, Archival)              │
└─────────────────────────────────────┘
```

### Component Interaction

```
┌────────────┐     Events      ┌──────────────┐
│  External  │ ─────────────▶  │   Cortex     │
│   System   │                 │  (Selector)  │
└────────────┘                 └──────┬───────┘
                                      │
                                      ▼ Relevant Events
                              ┌──────────────────┐
                              │  Pack Compiler   │
                              │  (Deterministic) │
                              └────────┬─────────┘
                                       │
                                       ▼ Memory Pack
                              ┌──────────────────┐
                              │  Agent Runtime   │
                              │ (Plan, Execute)  │
                              └────────┬─────────┘
                                       │
                                       ▼ New Events
                              ┌──────────────────┐
                              │     Storage      │
                              └────────┬─────────┘
                                       │
                                       ▼ Periodic
                              ┌──────────────────┐
                              │     Dreamer      │
                              │ (Async Curation) │
                              └──────────────────┘
```

---

## Backend Architecture

### Layer Responsibilities

#### 1. API Layer (`app/api/v1/`)

**Responsibility:** HTTP interface, request validation, response formatting, transaction management.

**Rules:**
- Handle HTTP concerns (status codes, headers, CORS)
- Validate incoming requests via Pydantic models
- Call domain operations (no business logic in routes)
- Manage database transactions (commit/rollback)
- Format responses with proper DTOs
- Handle errors gracefully with structured error responses

**Example:**
```python
# app/api/v1/endpoints/memories.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.database.memories import MemoryCreate, MemoryRead
from app.domain.memory_operations import MemoryOperations

router = APIRouter()

@router.post("/", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    data: MemoryCreate,
    db: AsyncSession = Depends(get_db)
) -> MemoryRead:
    """Create a new memory from an event."""
    try:
        memory = await MemoryOperations.create(db, data)
        await db.commit()
        await db.refresh(memory)
        return memory
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### 2. Domain Layer (`app/domain/`)

**Responsibility:** Business logic, validation rules, entity operations (CRUD), transformation logic.

**Rules:**
- Pure business logic, no HTTP or database session management
- NO `db.commit()` or `db.rollback()` (caller manages transactions)
- Use `db.flush()` ONLY if need generated IDs mid-operation
- Return entities or raise domain exceptions
- Keep operations focused and composable

**Example:**
```python
# app/domain/memory_operations.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.database.memories import Memory, MemoryCreate
from app.models.database.events import Event

class MemoryOperations:
    @staticmethod
    async def create(db: AsyncSession, data: MemoryCreate) -> Memory:
        """Create a memory from an event."""
        # Validate event exists
        event = await db.get(Event, data.event_id)
        if not event:
            raise ValueError(f"Event {data.event_id} not found")

        # Business rule: don't duplicate memories for same event
        existing = await db.scalar(
            select(Memory).where(Memory.event_id == data.event_id)
        )
        if existing:
            raise ValueError(f"Memory already exists for event {data.event_id}")

        # Create memory
        memory = Memory.model_validate(data)
        db.add(memory)
        await db.flush()  # Get generated ID

        return memory

    @staticmethod
    async def get_by_agent(
        db: AsyncSession,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> list[Memory]:
        """Retrieve memories for an agent."""
        result = await db.execute(
            select(Memory)
            .where(Memory.agent_id == agent_id)
            .where(Memory.is_deleted == False)
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
```

#### 3. Models Layer (`app/models/`)

**Responsibility:** Data schemas, validation, database mappings.

**Structure:**
```
app/models/
├── database/
│   ├── base.py          # Base model, mixins
│   ├── events.py        # Event model + DTOs
│   ├── memories.py      # Memory model + DTOs
│   ├── lessons.py       # Lesson model + DTOs
│   ├── knowledge.py     # Knowledge model + DTOs
│   ├── identity.py      # Identity model + DTOs
│   ├── transformations.py  # TransformationLog model
│   └── agents.py        # Agent model (if multi-agent)
└── dto/
    └── workflow_data.py # DTOs for passing data between workflows
```

**Pattern:**
```python
# app/models/database/memories.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from pgvector.sqlalchemy import Vector

class MemoryBase(SQLModel):
    """Shared fields for Memory."""
    agent_id: UUID = Field(foreign_key="agents.id", index=True)
    event_id: UUID | None = Field(default=None, foreign_key="events.id")
    content: str = Field(description="The reflected/structured content")
    metadata: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)

class Memory(MemoryBase, table=True):
    """Memory entity (table)."""
    __tablename__ = "memories"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)

    # Vector embedding for similarity search
    embedding: Vector | None = Field(default=None, sa_column_kwargs={"type_": Vector(1536)})

    # Relationships
    agent: "Agent" = Relationship(back_populates="memories")
    event: "Event | None" = Relationship(back_populates="memories")
    transformations_as_source: list["TransformationLog"] = Relationship(
        back_populates="source_memory",
        sa_relationship_kwargs={"foreign_keys": "TransformationLog.source_id"}
    )

class MemoryCreate(MemoryBase):
    """DTO for creating a memory."""
    pass

class MemoryRead(MemoryBase):
    """DTO for reading a memory."""
    id: UUID
    created_at: datetime
    updated_at: datetime

class MemoryUpdate(SQLModel):
    """DTO for updating a memory."""
    content: str | None = None
    metadata: dict | None = None
    importance_score: float | None = None
```

#### 4. Services Layer (`app/services/`)

**Responsibility:** External integrations, reusable utilities, complex helpers.

**Examples:**
- `llm_service.py` — Wrapper for OpenAI/Anthropic with retry logic
- `embedding_service.py` — Generate embeddings for text
- `similarity_service.py` — Vector search utilities
- `export_service.py` — Export Memory Packs to JSON/YAML

#### 5. Workflows Layer (`app/workflows/`)

**Responsibility:** Multi-step orchestration, LLM-driven transformations, business processes.

**Structure:**
```
app/workflows/
├── registry.py                  # Lazy-loaded workflow registry
├── memory_creation/
│   ├── orchestrator.py          # Main workflow
│   └── nodes/
│       ├── event_parser.py
│       ├── reflection_generator.py
│       └── memory_persister.py
├── lesson_extraction/
│   ├── orchestrator.py
│   └── nodes/
│       ├── memory_clusterer.py
│       ├── pattern_extractor.py
│       └── lesson_creator.py
└── dreamer/
    ├── curation_workflow.py
    ├── promotion_workflow.py
    └── consolidation_workflow.py
```

**Example:**
```python
# app/workflows/memory_creation/orchestrator.py
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.domain.memory_operations import MemoryOperations
from app.models.database.memories import MemoryCreate

class MemoryCreationWorkflow:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService()
        self.embedding = EmbeddingService()

    async def execute(self, event_id: UUID, agent_id: UUID) -> UUID:
        """Transform an Event into a Memory."""
        # 1. Load event
        event = await self.db.get(Event, event_id)

        # 2. Generate reflection via LLM
        reflection = await self.llm.generate_reflection(
            event_content=event.content,
            event_type=event.event_type
        )

        # 3. Generate embedding
        embedding_vector = await self.embedding.embed(reflection)

        # 4. Create memory
        memory_data = MemoryCreate(
            agent_id=agent_id,
            event_id=event_id,
            content=reflection,
            metadata={"source_event_type": event.event_type},
            embedding=embedding_vector
        )

        memory = await MemoryOperations.create(self.db, memory_data)
        await self.db.commit()

        # 5. Log transformation
        await self.log_transformation(
            source_id=event_id,
            source_type="Event",
            target_id=memory.id,
            target_type="Memory",
            transformation_type="reflection"
        )

        return memory.id
```

#### 6. Core Layer (`app/core/`)

**Responsibility:** Infrastructure concerns (config, database, logging, auth, caching).

**Key Files:**
- `config.py` — Pydantic Settings for environment variables
- `database.py` — SQLAlchemy async engine, session factory, dependencies
- `logging_config.py` — Structured logging setup (Loguru)
- `auth.py` — Optional: JWT verification, API key validation (if needed)
- `dependencies.py` — Common FastAPI dependencies

**Example:**
```python
# app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_SQL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

async def get_db() -> AsyncSession:
    """Dependency for getting a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Error Handling Strategy

**Domain Layer:** Raise specific exceptions
```python
class DomainException(Exception):
    """Base exception for domain errors."""
    pass

class EntityNotFoundError(DomainException):
    """Raised when an entity is not found."""
    pass

class DuplicateEntityError(DomainException):
    """Raised when trying to create a duplicate."""
    pass
```

**API Layer:** Catch and convert to HTTP errors
```python
@router.post("/memories")
async def create_memory(...):
    try:
        memory = await MemoryOperations.create(db, data)
        await db.commit()
        return memory
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateEntityError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Frontend Architecture

### Simplified Approach for Phase 1

**Goal:** Observability dashboard, not a full-featured app.

**Features:**
1. **Event Stream Viewer** — Real-time/recent events
2. **Memory Browser** — List/search memories
3. **Transformation Graph** — Visualize Event → Memory → Lesson → Knowledge lineage
4. **Dreamer Job Monitor** — Status of background curation jobs
5. **Agent Profile** — Identity summary, statistics

### Tech Stack

- **Next.js 15** with App Router (already set up)
- **TypeScript** for type safety
- **Tailwind CSS** for styling (already set up)
- **Recharts** or **D3.js** for visualization
- **React Query (TanStack Query)** for server state management
- **Zustand** for client state (minimal)

### Structure

```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Dashboard home
│   ├── events/
│   │   ├── page.tsx            # Events list
│   │   └── [id]/page.tsx       # Event detail
│   ├── memories/
│   │   ├── page.tsx            # Memories list
│   │   └── [id]/page.tsx       # Memory detail + lineage
│   ├── lessons/
│   │   └── page.tsx
│   ├── knowledge/
│   │   └── page.tsx
│   ├── identity/
│   │   └── page.tsx            # Agent identity/profile
│   └── dreamer/
│       └── page.tsx            # Job monitoring
├── components/
│   ├── ui/                     # shadcn components
│   ├── events/
│   │   ├── EventCard.tsx
│   │   └── EventList.tsx
│   ├── memories/
│   │   ├── MemoryCard.tsx
│   │   ├── MemoryList.tsx
│   │   └── TransformationGraph.tsx
│   └── shared/
│       ├── LoadingSpinner.tsx
│       └── ErrorBoundary.tsx
├── lib/
│   ├── api.ts                  # Base API client (from Marlin pattern)
│   ├── api-client/
│   │   ├── events.ts
│   │   ├── memories.ts
│   │   ├── lessons.ts
│   │   ├── knowledge.ts
│   │   └── identity.ts
│   └── utils.ts
├── types/
│   └── index.ts                # Mirror backend DTOs
└── hooks/
    ├── useEvents.ts
    ├── useMemories.ts
    └── useTransformationGraph.ts
```

### API Client Pattern (from Marlin)

```typescript
// frontend/src/lib/api.ts
class APIClient {
  private baseURL: string;
  private headers: Record<string, string>;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new APIError(response.status, error.detail || response.statusText);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ... put, patch, delete
}

export const apiClient = new APIClient();
```

```typescript
// frontend/src/lib/api-client/memories.ts
import { apiClient } from '../api';
import type { Memory, MemoryCreate } from '@/types';

export const memoriesAPI = {
  list: async (agentId: string, limit = 50, offset = 0): Promise<Memory[]> => {
    return apiClient.get(`/api/v1/memories?agent_id=${agentId}&limit=${limit}&offset=${offset}`);
  },

  get: async (id: string): Promise<Memory> => {
    return apiClient.get(`/api/v1/memories/${id}`);
  },

  create: async (data: MemoryCreate): Promise<Memory> => {
    return apiClient.post('/api/v1/memories', data);
  },

  getTransformations: async (id: string) => {
    return apiClient.get(`/api/v1/memories/${id}/transformations`);
  },
};
```

### React Query Integration

```typescript
// frontend/src/hooks/useMemories.ts
import { useQuery } from '@tanstack/react-query';
import { memoriesAPI } from '@/lib/api-client/memories';

export function useMemories(agentId: string, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['memories', agentId, limit, offset],
    queryFn: () => memoriesAPI.list(agentId, limit, offset),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useMemory(id: string) {
  return useQuery({
    queryKey: ['memory', id],
    queryFn: () => memoriesAPI.get(id),
  });
}

export function useTransformationGraph(memoryId: string) {
  return useQuery({
    queryKey: ['transformations', memoryId],
    queryFn: () => memoriesAPI.getTransformations(memoryId),
  });
}
```

---

## Database Design

### Core Tables

#### 1. `agents`
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_agents_name ON agents(name);
```

#### 2. `events`
```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    event_type VARCHAR(100) NOT NULL,  -- 'user_message', 'tool_call', 'api_response', etc.
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    importance_score FLOAT,  -- Optional: pre-computed importance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_events_agent_id ON events(agent_id);
CREATE INDEX idx_events_created_at ON events(created_at DESC);
CREATE INDEX idx_events_event_type ON events(event_type);
```

#### 3. `memories`
```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    event_id UUID REFERENCES events(id),  -- Nullable: some memories may be synthetic
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    importance_score FLOAT,
    embedding vector(1536),  -- pgvector for similarity search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_memories_agent_id ON memories(agent_id);
CREATE INDEX idx_memories_event_id ON memories(event_id);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);

-- Vector similarity index
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### 4. `lessons`
```sql
CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    pattern_type VARCHAR(100),  -- 'behavioral', 'preference', 'constraint', etc.
    confidence_score FLOAT,  -- How confident we are in this lesson
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP  -- When this lesson was retired/superseded
);

CREATE INDEX idx_lessons_agent_id ON lessons(agent_id);
CREATE INDEX idx_lessons_pattern_type ON lessons(pattern_type);
CREATE INDEX idx_lessons_created_at ON lessons(created_at DESC);
```

#### 5. `knowledge`
```sql
CREATE TABLE knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    category VARCHAR(100) NOT NULL,  -- 'fact', 'rule', 'belief', 'goal', etc.
    statement TEXT NOT NULL,  -- The canonical knowledge statement
    certainty FLOAT,  -- 0.0 to 1.0
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_knowledge_agent_id ON knowledge(agent_id);
CREATE INDEX idx_knowledge_category ON knowledge(category);
```

#### 6. `identity`
```sql
CREATE TABLE identity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) UNIQUE,  -- One identity per agent
    disposition_summary TEXT,  -- High-level identity description
    traits JSONB DEFAULT '{}',  -- {"cautious": 0.7, "curious": 0.9, ...}
    values JSONB DEFAULT '{}',  -- {"transparency": 0.95, "efficiency": 0.8, ...}
    preferences JSONB DEFAULT '{}',  -- Domain-specific preferences
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_identity_agent_id ON identity(agent_id);
```

#### 7. `transformation_log`
```sql
CREATE TABLE transformation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),

    -- Source
    source_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'Event', 'Memory', 'Lesson', etc.

    -- Target
    target_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,

    -- Transformation details
    transformation_type VARCHAR(100) NOT NULL,  -- 'reflection', 'consolidation', 'promotion', etc.
    workflow_name VARCHAR(255),

    -- Metadata
    metadata JSONB DEFAULT '{}',  -- LLM prompts, scores, reasoning, etc.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)  -- System/workflow identifier
);

CREATE INDEX idx_transformations_agent_id ON transformation_log(agent_id);
CREATE INDEX idx_transformations_source ON transformation_log(source_id, source_type);
CREATE INDEX idx_transformations_target ON transformation_log(target_id, target_type);
CREATE INDEX idx_transformations_created_at ON transformation_log(created_at DESC);
```

#### 8. `memory_packs` (optional, for pre-compiled packs)
```sql
CREATE TABLE memory_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Contents (references to included items)
    event_ids UUID[] DEFAULT '{}',
    memory_ids UUID[] DEFAULT '{}',
    lesson_ids UUID[] DEFAULT '{}',
    knowledge_ids UUID[] DEFAULT '{}',

    -- Compilation metadata
    compiled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    compiled_by VARCHAR(255),  -- Workflow or manual
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_memory_packs_agent_id ON memory_packs(agent_id);
```

### Alembic Migration Strategy

**Initial migration:** Create all tables with pgvector extension

```python
# backend/migrations/versions/001_initial_schema.py
"""Initial schema for Elephantasm LTAM

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-10-17

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Boolean(), server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agents_name', 'agents', ['name'])

    # ... create other tables

def downgrade() -> None:
    op.drop_table('agents')
    # ... drop other tables
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Core infrastructure + basic Event/Memory flow

**Tasks:**
1. **Backend Setup**
   - ✅ FastAPI structure (already done)
   - [ ] Async database layer with asyncpg
   - [ ] Alembic migrations (agents, events, memories, transformation_log)
   - [ ] Core models (Event, Memory, Agent)
   - [ ] Domain operations (EventOps, MemoryOps)
   - [ ] API endpoints (POST /events, POST /memories, GET /memories)
   - [ ] Structured logging setup

2. **Frontend Setup**
   - ✅ Next.js structure (already done)
   - [ ] API client layer
   - [ ] TypeScript types matching backend
   - [ ] React Query setup
   - [ ] Basic UI (event list, memory list)

3. **Services**
   - [ ] LLM service wrapper (OpenAI + Anthropic)
   - [ ] Embedding service

4. **Testing**
   - [ ] Test database setup
   - [ ] Factory fixtures
   - [ ] Unit tests for domain operations
   - [ ] Integration tests for API

**Deliverable:** Can ingest Events, create Memories via LLM, retrieve Memories via API.

---

### Phase 2: Transformation Pipeline (Weeks 3-4)

**Goal:** Memory → Lesson → Knowledge progression

**Tasks:**
1. **Backend**
   - [ ] Lesson model + operations
   - [ ] Knowledge model + operations
   - [ ] Transformation log operations
   - [ ] Lesson extraction workflow (cluster memories, extract patterns)
   - [ ] Knowledge consolidation workflow
   - [ ] API endpoints for Lessons, Knowledge, Transformations

2. **Frontend**
   - [ ] Lesson browser
   - [ ] Knowledge browser
   - [ ] Transformation graph visualization (D3.js or Recharts)

3. **Services**
   - [ ] Clustering service (vector similarity)
   - [ ] Pattern extraction via LLM

**Deliverable:** Complete Event → Memory → Lesson → Knowledge pipeline with full provenance tracking.

---

### Phase 3: Dreamer + Background Jobs (Weeks 5-6)

**Goal:** Automated curation and consolidation

**Tasks:**
1. **Backend**
   - [ ] APScheduler setup
   - [ ] Curation workflow (merge duplicates, archive stale)
   - [ ] Promotion workflow (Memory → Lesson, Lesson → Knowledge)
   - [ ] Job status tracking
   - [ ] API endpoints for job monitoring

2. **Frontend**
   - [ ] Dreamer job dashboard
   - [ ] Job logs viewer
   - [ ] Manual job triggers

3. **Testing**
   - [ ] Workflow integration tests
   - [ ] Job execution tests

**Deliverable:** Autonomous background curation running on schedule.

---

### Phase 4: Identity + Pack Compiler (Weeks 7-8)

**Goal:** Agent identity emergence + deterministic pack compilation

**Tasks:**
1. **Backend**
   - [ ] Identity model + operations
   - [ ] Identity update workflow (aggregate Knowledge → traits/values)
   - [ ] Pack compiler (select relevant context for query)
   - [ ] API endpoints for Identity, Memory Packs

2. **Frontend**
   - [ ] Identity profile page
   - [ ] Pack previewer

3. **Services**
   - [ ] Relevance scoring
   - [ ] Pack assembly logic

**Deliverable:** Full LTAM system with identity and context compilation.

---

### Phase 5: SDKs + Documentation (Weeks 9-10)

**Goal:** Developer experience and adoption

**Tasks:**
1. **Python SDK** (`elephantasm-py`)
   - [ ] Client library
   - [ ] Examples
   - [ ] PyPI package

2. **TypeScript SDK** (`@elephantasm/client`)
   - [ ] Client library
   - [ ] Examples
   - [ ] npm package

3. **Documentation**
   - [ ] Architecture docs
   - [ ] API reference (generated from OpenAPI)
   - [ ] User guides
   - [ ] Integration examples (LangChain, LlamaIndex, etc.)

4. **Docker Compose**
   - [ ] Full stack docker-compose.yml
   - [ ] One-command local setup

**Deliverable:** Production-ready framework with great DX.

---

### Phase 6: Polish + Performance (Weeks 11-12)

**Goal:** Production-ready hardening

**Tasks:**
1. **Performance**
   - [ ] Query optimization
   - [ ] Index tuning
   - [ ] Caching strategy (Redis if needed)
   - [ ] Load testing

2. **Security**
   - [ ] API key authentication
   - [ ] Rate limiting
   - [ ] Input validation hardening

3. **Observability**
   - [ ] Metrics (Prometheus)
   - [ ] Tracing (OpenTelemetry)
   - [ ] Dashboards (Grafana)

4. **Quality**
   - [ ] Code coverage > 80%
   - [ ] E2E tests
   - [ ] Security audit

**Deliverable:** Production-ready v0.1.0

---

## File Structure

### Final Directory Layout

```
elephantasm/
├── .claude/
│   ├── vision.md
│   ├── commands/
│   └── agents/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py          # create_app() + lifespan
│   │   │   └── v1/
│   │   │       ├── __init__.py      # API router aggregation
│   │   │       ├── api.py           # Main v1 router
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── health.py    # Health checks
│   │   │           ├── agents.py    # Agent CRUD
│   │   │           ├── events.py    # Event ingestion
│   │   │           ├── memories.py  # Memory CRUD + retrieval
│   │   │           ├── lessons.py   # Lesson CRUD
│   │   │           ├── knowledge.py # Knowledge CRUD
│   │   │           ├── identity.py  # Identity retrieval
│   │   │           ├── transformations.py  # Transformation logs
│   │   │           └── packs.py     # Memory pack compilation
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── database.py          # Async engine, session, dependencies
│   │   │   ├── logging_config.py    # Loguru setup
│   │   │   ├── auth.py              # Optional: API key/JWT
│   │   │   ├── dependencies.py      # Common dependencies
│   │   │   └── exceptions.py        # Custom exceptions
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # Base model, mixins
│   │   │   │   ├── agents.py        # Agent model + DTOs
│   │   │   │   ├── events.py        # Event model + DTOs
│   │   │   │   ├── memories.py      # Memory model + DTOs
│   │   │   │   ├── lessons.py       # Lesson model + DTOs
│   │   │   │   ├── knowledge.py     # Knowledge model + DTOs
│   │   │   │   ├── identity.py      # Identity model + DTOs
│   │   │   │   ├── transformations.py  # TransformationLog model
│   │   │   │   └── memory_packs.py  # MemoryPack model
│   │   │   └── dto/
│   │   │       └── workflow_data.py # DTOs for workflows
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── agent_operations.py
│   │   │   ├── event_operations.py
│   │   │   ├── memory_operations.py
│   │   │   ├── lesson_operations.py
│   │   │   ├── knowledge_operations.py
│   │   │   ├── identity_operations.py
│   │   │   ├── transformation_operations.py
│   │   │   └── pack_operations.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py       # OpenAI/Anthropic wrapper
│   │   │   ├── embedding_service.py # Generate embeddings
│   │   │   ├── similarity_service.py # Vector search
│   │   │   └── export_service.py    # Export packs
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py          # Lazy-loaded workflow registry
│   │   │   ├── memory_creation/
│   │   │   │   ├── orchestrator.py
│   │   │   │   └── nodes/
│   │   │   │       ├── event_parser.py
│   │   │   │       ├── reflection_generator.py
│   │   │   │       └── memory_persister.py
│   │   │   ├── lesson_extraction/
│   │   │   │   ├── orchestrator.py
│   │   │   │   └── nodes/
│   │   │   │       ├── memory_clusterer.py
│   │   │   │       ├── pattern_extractor.py
│   │   │   │       └── lesson_creator.py
│   │   │   ├── knowledge_consolidation/
│   │   │   │   └── orchestrator.py
│   │   │   ├── identity_update/
│   │   │   │   └── orchestrator.py
│   │   │   └── dreamer/
│   │   │       ├── curation_workflow.py
│   │   │       ├── promotion_workflow.py
│   │   │       └── consolidation_workflow.py
│   │   └── jobs/
│   │       ├── __init__.py
│   │       ├── scheduler.py         # APScheduler setup
│   │       └── tasks.py             # Job definitions
│   ├── migrations/
│   │   ├── env.py                   # Alembic environment
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 002_add_pgvector.py
│   │       └── 003_transformation_log.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Shared fixtures
│   │   ├── factories/
│   │   │   ├── __init__.py
│   │   │   ├── agent_factory.py
│   │   │   ├── event_factory.py
│   │   │   └── memory_factory.py
│   │   ├── unit/
│   │   │   ├── test_models.py
│   │   │   ├── test_domain_ops.py
│   │   │   └── test_transformations.py
│   │   ├── integration/
│   │   │   ├── test_api.py
│   │   │   ├── test_workflows.py
│   │   │   └── test_dreamer.py
│   │   └── e2e/
│   │       └── test_full_pipeline.py
│   ├── main.py                      # FastAPI app entry point
│   ├── requirements.txt
│   ├── requirements-dev.txt         # Dev dependencies
│   ├── .env.example
│   ├── .gitignore
│   ├── Dockerfile
│   ├── alembic.ini
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Dashboard home
│   │   │   ├── globals.css
│   │   │   ├── events/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── memories/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── lessons/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── knowledge/
│   │   │   │   └── page.tsx
│   │   │   ├── identity/
│   │   │   │   └── page.tsx
│   │   │   └── dreamer/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn components
│   │   │   ├── events/
│   │   │   │   ├── EventCard.tsx
│   │   │   │   └── EventList.tsx
│   │   │   ├── memories/
│   │   │   │   ├── MemoryCard.tsx
│   │   │   │   ├── MemoryList.tsx
│   │   │   │   └── TransformationGraph.tsx
│   │   │   ├── lessons/
│   │   │   │   └── LessonCard.tsx
│   │   │   ├── knowledge/
│   │   │   │   └── KnowledgeCard.tsx
│   │   │   └── shared/
│   │   │       ├── LoadingSpinner.tsx
│   │   │       └── ErrorBoundary.tsx
│   │   ├── lib/
│   │   │   ├── api.ts               # Base API client
│   │   │   ├── api-client/
│   │   │   │   ├── agents.ts
│   │   │   │   ├── events.ts
│   │   │   │   ├── memories.ts
│   │   │   │   ├── lessons.ts
│   │   │   │   ├── knowledge.ts
│   │   │   │   ├── identity.ts
│   │   │   │   └── transformations.ts
│   │   │   └── utils.ts
│   │   ├── types/
│   │   │   └── index.ts             # All TypeScript types
│   │   └── hooks/
│   │       ├── useEvents.ts
│   │       ├── useMemories.ts
│   │       ├── useLessons.ts
│   │       ├── useKnowledge.ts
│   │       └── useTransformationGraph.ts
│   ├── public/
│   ├── .env.example
│   ├── .env.local
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── README.md
├── docs/
│   ├── overview.md
│   ├── marlin-blueprint.md          # Reference architecture
│   ├── plans/
│   │   └── elephantasm-architecture-plan.md  # This document
│   ├── api/
│   │   └── openapi.yaml             # Generated from FastAPI
│   └── guides/
│       ├── getting-started.md
│       ├── integration-guide.md
│       └── deployment.md
├── sdks/
│   ├── python/
│   │   ├── elephantasm/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── models.py
│   │   ├── setup.py
│   │   └── README.md
│   └── typescript/
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   └── types.ts
│       ├── package.json
│       └── README.md
├── docker-compose.yml               # Full stack local dev
├── .gitignore
├── LICENSE
└── README.md                        # Main project README
```

---

## Summary: Adoption Strategy

### ✅ Adopt from Marlin

1. **Domain-driven layering** — Models → Domain Ops → API Routes
2. **SQLModel** — Combined validation + ORM
3. **Domain operations pattern** — No commits in business logic
4. **Pydantic Settings** — Type-safe config
5. **Structured logging** — Loguru with categories
6. **Workflow registry** — Lazy-loaded orchestrators
7. **Frontend API client pattern** — BaseAPIClient with error handling
8. **DTO separation** — Create/Read/Update DTOs per entity
9. **Alembic migrations** — Schema versioning
10. **Clear directory structure** — Separation of concerns

### 🔄 Simplify from Marlin

1. **Multi-tenancy** — Start with simple `agent_id` FK, not RLS
2. **Authentication** — Optional API keys initially, not heavy JWT/JWKS
3. **Caching** — Add later when needed, not upfront
4. **Database** — Single connection, not dual user/admin
5. **Frontend** — CSR-first dashboard, not complex SSR
6. **Middleware** — Minimal stack initially

### 🚀 Add Modern Enhancements

1. **Event sourcing** — Transformation log for full provenance
2. **Background jobs** — APScheduler for Dreamer from day one
3. **Vector embeddings** — pgvector for hybrid search
4. **Async-first** — FastAPI native async throughout
5. **Comprehensive testing** — Test infrastructure from start
6. **Docker Compose** — One-command local setup
7. **OpenAPI docs** — Auto-generated, comprehensive

---

## Next Steps

1. **Review this plan** — Validate architecture decisions
2. **Set up development environment** — PostgreSQL + pgvector locally
3. **Begin Phase 1** — Core infrastructure + Event/Memory flow
4. **Iterate based on feedback** — Adapt as we learn

---

*"Simplicity is the ultimate sophistication."* — Leonardo da Vinci
