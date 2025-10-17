# Events Model Design — Elephantasm Alpha

**Version:** 1.1 (Alpha - Message-Only, Refined)
**Date:** 2025-10-17
**Status:** Design Document

**Changelog:**
- v1.1: Added nullable non-critical fields, optional occurred_at, meta_summary field
- v1.0: Initial design

---

## Purpose

This document defines the **Event** model for Elephantasm's alpha release. Events are the atomic foundation of the Long-Term Agentic Memory (LTAM) system—the smallest meaningful "this happened" units from which all higher-order memory structures are derived.

---

## Conceptual Understanding

### What is an Event?

**Events are the atoms of experience.**

An Event represents a single, discrete occurrence that happened at a specific point in time. Think of it as the smallest unit of interaction or observation worth preserving for later reasoning.

```
Event (atom)
    ↓
Memory (structured reflection)
    ↓
Lesson (extracted pattern)
    ↓
Knowledge (canonicalized truth)
    ↓
Identity (behavioral fingerprint)
```

### Key Characteristics

1. **Atomic** — One Event = one occurrence (not a conversation, but a single message)
2. **Temporal** — Has both `occurred_at` (when it happened) and `received_at` (when we saw it)
3. **Typed** — Has a `kind` that categorizes what type of event it is
4. **Idempotent** — Can be deduplicated via `dedupe_key`
5. **Traceable** — Links back to its source via provenance metadata
6. **Grouped** — Optionally belongs to a `session_id` for conversation grouping
7. **Owner-Scoped** — Always tied to an agent/spirit via `agent_id`

### Alpha Scope: Messages Only

For the initial alpha release, we're focusing on **conversational messages only**:

- `message.in` — Incoming message from user/system to agent
- `message.out` — Outgoing message from agent to user/system

**Not in alpha:**
- Tool calls/results
- File ingestions
- Decisions
- Errors
- Feedback events

We'll expand the event taxonomy in later phases once the core pipeline is validated.

---

## How Events Fit Into Elephantasm

### 1. Ingestion Phase

External systems send raw data → API creates Event records → Events stored in database

```
User Message (external)
    ↓
POST /api/v1/events
    ↓
Event.create(agent_id, type=message.in, content="...")
    ↓
PostgreSQL events table
```

### 2. Selection Phase (Cortex)

The **Cortex** (selector) scans recent Events and identifies which ones merit transformation into Memories:

**Triggers:**
- Novelty (first time seeing this information)
- Contradiction (conflicts with existing knowledge)
- Outcome (decision + result pairing)
- Repetition (recurring theme)
- Feedback (explicit signals)
- Salience (high importance score)

### 3. Transformation Phase

Selected Events → LLM reflection → Memory creation → Transformation logged

```
Event[id=abc123, content="User prefers JSON over XML"]
    ↓
MemoryCreationWorkflow
    ↓
Memory[id=xyz789, content="User stated preference: JSON format preferred", event_id=abc123]
    ↓
TransformationLog[source=abc123, target=xyz789, type="reflection"]
```

### 4. Session Grouping

Events with the same `session_id` belong to the same conversational thread:

```
session_id: "conv_20251017_1234"
  ├── Event[message.in]: "What's the weather?"
  ├── Event[message.out]: "It's sunny, 72°F"
  ├── Event[message.in]: "Should I bring an umbrella?"
  └── Event[message.out]: "No, you won't need one today"
```

Sessions provide context for Memory compilation—the Pack Compiler can retrieve "all events from this session" to give the agent full conversation context.

---

## Data Model Design

### Core Fields

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `id` | UUID | Primary key | Yes |
| `agent_id` | UUID | Owner/spirit (FK to agents) | Yes |
| `event_type` | String | Kind of event (message.in, message.out) | Yes |
| `content` | Text | Human-readable content | Yes |
| `occurred_at` | Timestamp | When it actually happened (source time) | No (defaults to received_at) |
| `received_at` | Timestamp | When we ingested it (system time) | Yes (auto) |
| `session_id` | String | Conversation/thread grouping handle | No |
| `metadata` | JSONB | Flexible structured data | No |
| `dedupe_key` | String | Idempotency key for deduplication | No |
| `importance_score` | Float | Pre-computed importance hint (0.0–1.0) | No |
| `source_uri` | String | Provenance pointer (e.g., slack://..., discord://...) | No |
| `meta_summary` | Text | Brief Cortex-generated summary (e.g., "user asks about X") | No |
| `is_deleted` | Boolean | Soft delete flag | Yes (default: false) |

### Design Decisions

#### 1. Two Timestamps: `occurred_at` vs `received_at`

**Why two?**

- **`occurred_at`** = Source truth (when the user sent the message, per their system clock)
- **`received_at`** = Ingest truth (when Elephantasm received it, per server clock)

**Use cases:**
- Batch imports: occurred_at = original timestamp, received_at = import time
- Clock skew: Source and server clocks may differ
- Ordering: Display by occurred_at, dedupe/process by received_at

**Flexibility:** `occurred_at` is **nullable**. If the source doesn't provide a timestamp, we fall back to using `received_at` at the application layer. This handles:
- Simple API calls without timestamp metadata
- Sources that don't track message timing
- Manual event creation where exact timing isn't critical

**Implementation:**
```python
# In domain operations
if not event_data.occurred_at:
    event_data.occurred_at = datetime.utcnow()  # Same as received_at
```

#### 2. `event_type` String (not Enum)

We're using a flexible string field rather than a strict database enum.

**Why?**
- Easy to extend (add new types without migrations)
- Alpha scope is tiny (message.in, message.out), but we know it'll grow
- Application-level validation via Pydantic provides type safety

**Validation:**
```python
class EventType(str, Enum):
    MESSAGE_IN = "message.in"
    MESSAGE_OUT = "message.out"
    # Future: TOOL_CALL = "tool.call", etc.
```

#### 3. `session_id` as String (not FK)

Sessions are lightweight grouping handles, not first-class entities in alpha.

**Why not a sessions table?**
- Overhead: Most sessions are ephemeral, don't need full CRUD
- Flexibility: Can derive sessions algorithmically (e.g., "events within 30-min window")
- External IDs: Many sources provide their own thread IDs (Slack channel, Discord thread)

**When to promote to table?**
- Phase 2+: If we add session metadata (title, summary, tags)
- Phase 2+: If we want session-level operations (archive, export)

For now: just a string column.

#### 4. `dedupe_key` for Idempotency

Events can arrive multiple times (retries, webhooks, imports). The dedupe_key prevents duplicates.

**Generation strategy:**
```python
dedupe_key = hash(agent_id + event_type + content + str(occurred_at) + source_uri)
```

**Enforcement:**
- Unique index on `dedupe_key` (nullable, partial index where dedupe_key IS NOT NULL)
- Client optionally provides dedupe_key
- System can auto-generate if not provided

#### 5. `metadata` JSONB for Flexibility

Stores structured data that varies by event type:

**Examples:**
```json
// message.in
{
  "source": "slack",
  "channel_id": "C12345",
  "user_id": "U67890",
  "thread_ts": "1697558400.123456"
}

// message.out
{
  "model": "claude-sonnet-4",
  "latency_ms": 1250,
  "tokens": 345
}
```

No strict schema enforced at DB level—application validates per event_type.

#### 6. `importance_score` (Optional)

A simple 0.0–1.0 float to hint at event significance.

**Who sets it?**
- Selector (Cortex) during ingestion
- LLM-based scoring ("rate importance of this message")
- Rule-based heuristics (e.g., "errors = 0.8, casual chat = 0.2")

**Use cases:**
- Prioritize which Events to transform into Memories first
- Filter low-importance Events from Memory Pack compilation
- Analytics/reporting

Not required in alpha—can be null.

#### 7. `meta_summary` — Cortex-Generated Summary (NEW)

A brief, human-readable summary of the event's content, generated by the Cortex (selector) during processing.

**Purpose:**
- Quick scanning without reading full content
- Index-friendly for search/filtering
- Semantic compression for Memory Pack compilation
- Helps Dreamer identify patterns across Events

**Examples:**
```
content: "Hey, I was wondering if you could help me understand how async/await works in Python?"
meta_summary: "user asks for explanation of async/await in Python"

content: "That makes sense! I'll try implementing it that way."
meta_summary: "user confirms understanding and plans implementation"

content: "Actually, I think we should use JSON instead of XML for this."
meta_summary: "user expresses preference for JSON over XML"
```

**Generation Strategy:**
- Populated by Cortex after Event creation (asynchronous)
- LLM-based: "Summarize this message in 5-10 words: {content}"
- Stored in nullable field (null until Cortex processes it)
- Can be regenerated if Cortex logic improves

**Implementation:**
```python
# Cortex workflow
event = await EventOperations.create(db, event_data)
await db.commit()

# Asynchronously generate summary
meta_summary = await cortex.generate_summary(event.content, event.event_type)
await EventOperations.update_meta_summary(db, event.id, meta_summary)
await db.commit()
```

**Benefits:**
- Faster event browsing in UI
- Better search results (summary + content both indexed)
- Enables "show me events where user asked questions" queries
- Reduces token usage when passing event context to LLMs

#### 8. Soft Deletes (`is_deleted`)

Events are never hard-deleted—they're the source of truth for provenance.

**Why soft delete?**
- Transformation log still references Event IDs
- "Why does the agent believe X?" requires tracing back to original Events
- GDPR/privacy: can redact `content` while preserving structure

---

## SQLModel Implementation

### Pattern: Base + Table + DTOs

Following the Marlin blueprint pattern with **nullable=True for non-critical fields**:

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship

# Shared fields
class EventBase(SQLModel):
    # Critical fields (not nullable)
    agent_id: UUID = Field(foreign_key="agents.id", index=True)
    event_type: str = Field(max_length=100, index=True)
    content: str = Field(description="Human-readable message content")

    # Non-critical fields (nullable for flexibility)
    occurred_at: datetime | None = Field(
        default=None,
        description="When event occurred (source time); defaults to received_at if not provided",
        nullable=True
    )
    session_id: str | None = Field(default=None, max_length=255, index=True, nullable=True)
    metadata: dict = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    dedupe_key: str | None = Field(default=None, max_length=255, nullable=True)
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, nullable=True)
    source_uri: str | None = Field(default=None, nullable=True)
    meta_summary: str | None = Field(
        default=None,
        description="Brief Cortex-generated summary (e.g., 'user asks about X')",
        nullable=True
    )

# Table model
class Event(EventBase, table=True):
    __tablename__ = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When event was ingested (system time)"
    )
    is_deleted: bool = Field(default=False)

    # Relationships
    agent: "Agent" = Relationship(back_populates="events")
    memories: list["Memory"] = Relationship(back_populates="event")

# DTOs
class EventCreate(EventBase):
    """Data required to create an Event"""
    pass

class EventRead(EventBase):
    """Data returned when reading an Event"""
    id: UUID
    received_at: datetime

class EventUpdate(SQLModel):
    """Fields that can be updated"""
    metadata: dict | None = None
    importance_score: float | None = None
    meta_summary: str | None = None
    is_deleted: bool | None = None
```

### Key SQLModel Features

1. **Field Validation** — Pydantic validators ensure data integrity
2. **Default Factories** — `default_factory=dict` prevents mutable default bugs
3. **Constraints** — `ge=0.0, le=1.0` enforces importance_score range
4. **Relationships** — SQLModel handles FK/joins declaratively
5. **Optional Fields** — `str | None` makes fields nullable

---

## Database Schema (SQL)

```sql
CREATE TABLE events (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership (critical)
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,

    -- Classification (critical)
    event_type VARCHAR(100) NOT NULL,

    -- Content (critical)
    content TEXT NOT NULL,

    -- Temporal (received_at critical, occurred_at flexible)
    occurred_at TIMESTAMP,  -- Nullable: defaults to received_at if not provided
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Grouping (flexible)
    session_id VARCHAR(255),

    -- Metadata (flexible)
    metadata JSONB DEFAULT '{}',
    dedupe_key VARCHAR(255),
    importance_score FLOAT CHECK (importance_score >= 0.0 AND importance_score <= 1.0),
    source_uri TEXT,
    meta_summary TEXT,  -- NEW: Cortex-generated brief summary

    -- Soft Delete (critical)
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Indexes for common queries
CREATE INDEX idx_events_agent_id ON events(agent_id);
CREATE INDEX idx_events_occurred_at ON events(occurred_at DESC) WHERE occurred_at IS NOT NULL;
CREATE INDEX idx_events_received_at ON events(received_at DESC);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_session_id ON events(session_id) WHERE session_id IS NOT NULL;

-- Unique constraint for deduplication
CREATE UNIQUE INDEX idx_events_dedupe_key ON events(dedupe_key) WHERE dedupe_key IS NOT NULL;

-- Compound index for common filters
CREATE INDEX idx_events_agent_occurred ON events(agent_id, occurred_at DESC) WHERE occurred_at IS NOT NULL;
CREATE INDEX idx_events_agent_session ON events(agent_id, session_id) WHERE session_id IS NOT NULL;

-- Full-text search on meta_summary (for fast semantic filtering)
CREATE INDEX idx_events_meta_summary_gin ON events USING gin(to_tsvector('english', meta_summary)) WHERE meta_summary IS NOT NULL;
```

### Index Strategy

1. **`idx_events_agent_id`** — Most queries filter by agent
2. **`idx_events_occurred_at`** — Chronological ordering (DESC for recent-first), partial index where NOT NULL
3. **`idx_events_event_type`** — Filter by message.in vs message.out
4. **`idx_events_session_id`** — Retrieve all events in a conversation (partial index where NOT NULL)
5. **`idx_events_dedupe_key`** — Fast idempotency check (partial index where NOT NULL, unique)
6. **`idx_events_agent_occurred`** — Compound for "agent's recent events" (partial index where occurred_at NOT NULL)
7. **`idx_events_meta_summary_gin`** — Full-text search on summaries (GIN index for fast text search, partial index where NOT NULL)

**Note:** Partial indexes (`WHERE ... IS NOT NULL`) are used for nullable fields to:
- Save disk space (don't index NULL rows)
- Improve query performance (smaller indexes)
- Enable efficient queries on populated fields only

---

## Usage Patterns

### 1. Creating an Event

```python
from app.domain.event_operations import EventOperations
from app.models.database.events import EventCreate

# Incoming message
event_data = EventCreate(
    agent_id=agent.id,
    event_type="message.in",
    content="What's the weather in Tokyo?",
    occurred_at=datetime.utcnow(),
    session_id="conv_20251017_1234",
    metadata={
        "source": "api",
        "user_id": "user_abc123"
    }
)

event = await EventOperations.create(db, event_data)
await db.commit()
```

### 2. Retrieving Recent Events

```python
# Get last 50 events for an agent
events = await EventOperations.get_recent(
    db,
    agent_id=agent.id,
    limit=50
)

# Get events for a specific session
session_events = await EventOperations.get_by_session(
    db,
    agent_id=agent.id,
    session_id="conv_20251017_1234"
)
```

### 3. Deduplication

```python
# Client provides dedupe_key
event_data = EventCreate(
    agent_id=agent.id,
    event_type="message.in",
    content="Hello",
    occurred_at=datetime.utcnow(),
    dedupe_key="slack_msg_1697558400.123456"
)

try:
    event = await EventOperations.create(db, event_data)
except IntegrityError:
    # Duplicate detected, skip
    pass
```

### 4. Importance Scoring

```python
# System computes importance
importance = await compute_importance(event_data.content, event_data.event_type)

event_data = EventCreate(
    agent_id=agent.id,
    event_type="message.in",
    content="URGENT: Server down!",
    occurred_at=datetime.utcnow(),
    importance_score=0.95  # High importance
)
```

### 5. Meta Summary Population (Cortex)

```python
# Step 1: Create event without summary
event_data = EventCreate(
    agent_id=agent.id,
    event_type="message.in",
    content="Hey, I was wondering if you could help me understand how async/await works in Python?",
    occurred_at=datetime.utcnow(),
    session_id="conv_123"
)

event = await EventOperations.create(db, event_data)
await db.commit()

# Step 2: Cortex generates summary asynchronously
from app.services.llm_service import LLMService

llm = LLMService()
meta_summary = await llm.generate_summary(
    content=event.content,
    event_type=event.event_type,
    max_words=10
)
# Returns: "user asks for explanation of async/await in Python"

# Step 3: Update event with summary
await EventOperations.update_meta_summary(db, event.id, meta_summary)
await db.commit()
```

---

## API Endpoints (Phase 1)

### POST /api/v1/events

**Purpose:** Ingest a new event

**Request:**
```json
{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "event_type": "message.in",
  "content": "What's the weather in Tokyo?",
  "occurred_at": "2025-10-17T14:30:00Z",  // Optional: defaults to received_at if omitted
  "session_id": "conv_20251017_1234",     // Optional
  "metadata": {                            // Optional
    "source": "slack",
    "channel_id": "C12345"
  },
  "dedupe_key": "slack_msg_1697558400.123456"  // Optional
}
```

**Minimal request (only required fields):**
```json
{
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "event_type": "message.in",
  "content": "What's the weather in Tokyo?"
}
```

**Response:** `201 Created`
```json
{
  "id": "event_abc123",
  "agent_id": "123e4567-e89b-12d3-a456-426614174000",
  "event_type": "message.in",
  "content": "What's the weather in Tokyo?",
  "occurred_at": "2025-10-17T14:30:00Z",
  "received_at": "2025-10-17T14:30:01.234Z",
  "session_id": "conv_20251017_1234",
  "metadata": {...},
  "dedupe_key": "slack_msg_1697558400.123456",
  "importance_score": null,
  "meta_summary": null  // Populated later by Cortex
}
```

### GET /api/v1/events

**Purpose:** List events for an agent

**Query params:**
- `agent_id` (required)
- `limit` (default: 50, max: 200)
- `offset` (default: 0)
- `event_type` (optional filter)
- `session_id` (optional filter)
- `since` (optional: occurred_at >= timestamp)
- `until` (optional: occurred_at <= timestamp)

**Response:** `200 OK`
```json
{
  "events": [...],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/events/{event_id}

**Purpose:** Retrieve a specific event

**Response:** `200 OK` or `404 Not Found`

---

## Domain Operations (Business Logic)

Following the Marlin pattern: domain operations handle business logic, no commits.

```python
# app/domain/event_operations.py
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from app.models.database.events import Event, EventCreate, EventUpdate

class EventOperations:
    @staticmethod
    async def create(db: AsyncSession, data: EventCreate) -> Event:
        """Create a new event."""
        # Validate agent exists
        agent = await db.get(Agent, data.agent_id)
        if not agent:
            raise EntityNotFoundError(f"Agent {data.agent_id} not found")

        # Default occurred_at to current time if not provided
        if not data.occurred_at:
            data.occurred_at = datetime.utcnow()

        # Auto-generate dedupe_key if not provided
        if not data.dedupe_key and data.source_uri:
            data.dedupe_key = generate_dedupe_key(data)

        event = Event.model_validate(data)
        db.add(event)
        await db.flush()  # Get generated ID

        return event

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        agent_id: UUID,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None
    ) -> list[Event]:
        """Get recent events for an agent."""
        query = (
            select(Event)
            .where(Event.agent_id == agent_id)
            .where(Event.is_deleted == False)
        )

        if event_type:
            query = query.where(Event.event_type == event_type)

        query = (
            query
            .order_by(Event.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_session(
        db: AsyncSession,
        agent_id: UUID,
        session_id: str
    ) -> list[Event]:
        """Get all events in a session, chronologically ordered."""
        result = await db.execute(
            select(Event)
            .where(
                and_(
                    Event.agent_id == agent_id,
                    Event.session_id == session_id,
                    Event.is_deleted == False
                )
            )
            .order_by(Event.occurred_at.asc())  # Chronological for conversation
        )
        return result.scalars().all()

    @staticmethod
    async def update_importance(
        db: AsyncSession,
        event_id: UUID,
        importance_score: float
    ) -> Event:
        """Update importance score for an event."""
        event = await db.get(Event, event_id)
        if not event:
            raise EntityNotFoundError(f"Event {event_id} not found")

        event.importance_score = importance_score
        await db.flush()

        return event

    @staticmethod
    async def update_meta_summary(
        db: AsyncSession,
        event_id: UUID,
        meta_summary: str
    ) -> Event:
        """Update meta_summary for an event (populated by Cortex)."""
        event = await db.get(Event, event_id)
        if not event:
            raise EntityNotFoundError(f"Event {event_id} not found")

        event.meta_summary = meta_summary
        await db.flush()

        return event

def generate_dedupe_key(data: EventCreate) -> str:
    """Generate idempotent dedupe key."""
    import hashlib
    parts = [
        str(data.agent_id),
        data.event_type,
        data.content[:100],  # First 100 chars
        str(data.occurred_at),
        data.source_uri or ""
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_event_operations.py

async def test_create_event(db_session, agent_factory):
    agent = await agent_factory()

    event_data = EventCreate(
        agent_id=agent.id,
        event_type="message.in",
        content="Hello world",
        occurred_at=datetime.utcnow()
    )

    event = await EventOperations.create(db_session, event_data)

    assert event.id is not None
    assert event.agent_id == agent.id
    assert event.content == "Hello world"
    assert event.received_at is not None

async def test_dedupe_key_prevents_duplicates(db_session, agent_factory):
    agent = await agent_factory()

    event_data = EventCreate(
        agent_id=agent.id,
        event_type="message.in",
        content="Test",
        occurred_at=datetime.utcnow(),
        dedupe_key="unique_key_123"
    )

    # Create first event
    event1 = await EventOperations.create(db_session, event_data)
    await db_session.commit()

    # Attempt duplicate
    with pytest.raises(IntegrityError):
        event2 = await EventOperations.create(db_session, event_data)
        await db_session.commit()
```

### Integration Tests

```python
# tests/integration/test_events_api.py

async def test_create_event_endpoint(client, agent):
    response = await client.post(
        "/api/v1/events",
        json={
            "agent_id": str(agent.id),
            "event_type": "message.in",
            "content": "Test message",
            "occurred_at": "2025-10-17T14:30:00Z"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test message"
    assert data["event_type"] == "message.in"

async def test_list_events_by_session(client, agent, event_factory):
    # Create events in same session
    session_id = "conv_test_123"
    for i in range(3):
        await event_factory(
            agent_id=agent.id,
            session_id=session_id,
            content=f"Message {i}"
        )

    response = await client.get(
        f"/api/v1/events?agent_id={agent.id}&session_id={session_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 3
    # Should be chronologically ordered
    assert data["events"][0]["content"] == "Message 0"
```

---

## Future Enhancements (Post-Alpha)

### Phase 2: Expanded Event Types

```python
class EventType(str, Enum):
    # Messages (alpha)
    MESSAGE_IN = "message.in"
    MESSAGE_OUT = "message.out"

    # Tools (phase 2)
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"

    # Ingestion (phase 2)
    FILE_INGESTED = "file.ingested"
    DOC_SEEN = "doc.seen"

    # Meta (phase 2)
    DECISION = "decision"
    ERROR = "error"
    FEEDBACK = "feedback"
    NOTE = "note"
```

### Phase 3: Vector Embeddings

Add `embedding` column for similarity search:

```sql
ALTER TABLE events ADD COLUMN embedding vector(1536);
CREATE INDEX idx_events_embedding ON events USING ivfflat (embedding vector_cosine_ops);
```

### Phase 4: Session Promotion

If sessions become first-class entities:

```sql
CREATE TABLE sessions (
    id VARCHAR(255) PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id),
    title VARCHAR(255),
    summary TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

ALTER TABLE events ADD CONSTRAINT fk_events_session
    FOREIGN KEY (session_id) REFERENCES sessions(id);
```

---

## Summary

### Events in Elephantasm

✅ **Atomic units** of experience
✅ **Foundation layer** for all memory structures
✅ **Temporal precision** with dual timestamps (occurred_at optional, received_at required)
✅ **Idempotent** via dedupe_key
✅ **Session-grouped** for conversation context
✅ **Extensible** via metadata JSONB
✅ **Traceable** via provenance pointers
✅ **Summarized** via meta_summary (Cortex-generated)

### Alpha Implementation

✅ **Minimal scope:** message.in, message.out only
✅ **SQLModel pattern:** Base + Table + DTOs
✅ **Flexible nullable fields:** Only critical fields (agent_id, event_type, content) required
✅ **Domain operations:** No commits in business logic
✅ **Comprehensive indexes** for performance (including full-text search on meta_summary)
✅ **Soft deletes** for provenance preservation
✅ **API-first** with clear endpoints

### Key Design Refinements (v1.1)

🔄 **Nullable non-critical fields** — Maximum flexibility for varied ingestion sources
🔄 **Optional occurred_at** — Defaults to received_at when source doesn't provide timestamp
🆕 **meta_summary field** — Cortex-generated brief summary for fast scanning and semantic filtering

### Ready to Implement

With this design document as our guide, we can now:

1. Create the SQLModel class in `backend/app/models/database/events.py`
2. Create the domain operations in `backend/app/domain/event_operations.py`
3. Create the Alembic migration for the events table
4. Create the API endpoints in `backend/app/api/v1/endpoints/events.py`
5. Write tests in `backend/tests/`

---

*"Start with the atoms, and the molecules will follow."*
