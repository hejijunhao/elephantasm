# Events: The Foundation of Elephantasm Memory

## Table of Contents
1. [Philosophical Foundation](#philosophical-foundation)
2. [What is an Event?](#what-is-an-event)
3. [Technical Implementation](#technical-implementation)
4. [Event Granularity](#event-granularity)
5. [Sessions & Conversations](#sessions--conversations)
6. [Event Taxonomy](#event-taxonomy)
7. [Event Structure](#event-structure)
8. [From Events to Memories](#from-events-to-memories)
9. [API Operations](#api-operations)
10. [Practical Ingestion Rules](#practical-ingestion-rules)
11. [Storage & Indexing](#storage--indexing)
12. [Retention & Promotion](#retention--promotion)
13. [Examples](#examples)

---

## Philosophical Foundation

### Events as the First Compression of Reality

The world is continuous, but Elephantasm is discrete. **Events are how the system turns the unbroken flow of experience into knowable pieces.**

If Elephantasm were a mind:
- **Events** are **sensations** — each distinct stimulus or action
- **Memories** are **impressions** — the traces that remain
- **Lessons** are **interpretations** — how meaning is derived
- **Knowledge** is **structure** — meaning generalized into truth
- **Identity** is **continuity** — the story that ties it all together

### The Seven Dimensions of Events

| Dimension | Essence |
|-----------|---------|
| **Ontological** | The unit of being — the moment something enters existence |
| **Epistemological** | The unit of knowing — what makes knowledge traceable and true |
| **Temporal** | The unit of time — defines before/after, cause/effect |
| **Cognitive** | The unit of perception — the interface between sensing and understanding |
| **Narrative** | The unit of story — the seeds from which memory and meaning grow |
| **Systemic** | The unit of life — the pulse that keeps the system adaptive |
| **Empirical** | The ground truth — the only thing the system knows with certainty |

**Events are epistemic anchors** — the empirical core of Elephantasm's mind. Every Memory, Lesson, or piece of Knowledge must be able to say: *"I exist because of these Events."* If it can't, it becomes speculation — unanchored, dreamlike, unreliable.

---

## What is an Event?

An **Event** is an **atomic occurrence tied to a Spirit** (the agent/owner entity).

### Core Characteristics

✅ **Atomic** — Cannot be meaningfully subdivided
✅ **Timestamped** — Has `occurred_at` (source time) vs `created_at` (ingestion time)
✅ **Typed** — Has a kind (`message.in`, `message.out`, `tool.call`, etc.)
✅ **Normalized** — Carries human-readable content + minimal structured metadata
✅ **Idempotent** — Identified by `dedupe_key` to prevent duplicates
✅ **Traceable** — Contains provenance pointer (`source_uri`)
✅ **Owned** — Belongs to a specific Spirit (`spirit_id`)

**Rule of thumb:** If you can point to it and say *"that exact thing happened at that time,"* it's an Event.

### Events as Dual Interfaces

Events sit on the boundary between **perception and action**:
- **Incoming**: observations, messages, tool results
- **Outgoing**: decisions, utterances, tool invocations

This symmetry is deliberate — Elephantasm learns from both what it sees and what it does, understanding reality as transactional.

---

## Technical Implementation

### Database Model (`backend/app/models/database/events.py`)

```python
class Event(EventBase, TimestampMixin, table=True):
    """Event entity - atomic unit of experience."""

    # Identity
    id: UUID                    # PostgreSQL gen_random_uuid()
    spirit_id: UUID             # FK to spirits.id (indexed)

    # Classification
    event_type: str             # e.g., "message.in", "tool.call" (indexed)

    # Content
    meta_summary: str | None    # Brief Cortex-generated summary
    content: str                # Human-readable payload (required)

    # Temporal
    occurred_at: datetime | None   # When event happened (source time)
    created_at: datetime           # When ingested (auto, from TimestampMixin)
    updated_at: datetime           # Last modified (auto, from TimestampMixin)

    # Grouping
    session_id: str | None      # Conversation/thread handle (indexed)

    # Metadata
    meta: dict[str, Any]        # JSONB for structured data

    # Provenance
    source_uri: str | None      # Traceability pointer
    dedupe_key: str | None      # SHA256-based idempotency key (unique)

    # Importance
    importance_score: float | None  # 0.0-1.0 for prioritization

    # Lifecycle
    is_deleted: bool            # Soft delete flag
```

### Triple Timestamp Strategy

Events track three temporal dimensions:

1. **`occurred_at`** (nullable) — When the event *actually happened* in the source system
2. **`created_at`** (auto) — When Elephantasm *ingested* the event
3. **`updated_at`** (auto) — When the event was *last modified* (e.g., Cortex enrichment)

This separation is critical for:
- Replaying conversations in source order (use `occurred_at`)
- Tracking system ingestion lag (compare `occurred_at` vs `created_at`)
- Auditing enrichment cycles (via `updated_at`)

---

## Event Granularity

### The "Meaningful Atomics" Rule

Use **one Event per irreducible occurrence**:

| Scenario | Event Count | Events Created |
|----------|-------------|----------------|
| Single message from user | 1 | `message.in` |
| Agent response | 1 | `message.out` |
| Tool call + result | 2 | `tool.call`, `tool.result` |
| File ingestion | 1 per file | `file.ingested` |
| Error | 1 | `error` |
| User decision | 1 | `decision` |

**Why this matters:** Downstream reasoning becomes legible. A Memory like *"We tried X, it failed with Y"* can link precisely to the `tool.call` + `error` Events.

### Anti-Pattern: Don't store conversations as Events

❌ **Conversation as Event** — Too coarse, loses precision
✅ **Messages as Events** — Maintains granularity for linking

Conversations are *containers*; Events are *contents*. Storing only conversations blurs granularity and makes it harder to extract precise lessons.

---

## Sessions & Conversations

### Lightweight Grouping Handle

Introduce **one lightweight grouping field** and keep the rest derived:

**`session_id`** (or `thread_id`) on each Event:
- If your source provides a conversation/thread ID (Slack, Discord, email), map it here
- If not, derive sessions by inactivity windows (e.g., 30 minutes) and assign a generated `session_id`
- **Index this field** for fast chronological retrieval

**Conversations** are just named/semantic views over sessions (optional in MVP). You don't need a table — compute it if needed.

**Events are the atoms; `session_id` is the simple glue that says "these belong together."**

---

## Event Taxonomy

### Alpha Release (v0.0.x) — Messages Only

```python
class EventType(str, Enum):
    MESSAGE_IN = "message.in"
    MESSAGE_OUT = "message.out"
```

### Future Expansion (Roadmap)

Keep kinds to a handful; expand gradually:

- **Messages**: `message.in`, `message.out`
- **Tools**: `tool.call`, `tool.result`
- **Files**: `file.ingested`, `doc.seen`
- **Decisions**: `decision` (explicit choice or branch point)
- **Feedback**: `feedback` (thumbs up/down, rating, critique)
- **Errors**: `error` (exceptions, failed calls)
- **Notes**: `note` (freeform internal thought worth keeping)

**Design principle:** Start tiny, add only when patterns emerge that demand new types.

---

## Event Structure

### What Events Store (Conceptually)

| Layer | Fields | Purpose |
|-------|--------|---------|
| **Identity** | `spirit_id` | Owner/agent |
| **Clock** | `occurred_at`, `created_at`, `updated_at` | Triple timestamp strategy |
| **Kind** | `event_type` | From taxonomy |
| **Session** | `session_id` | Thread/conversation grouping |
| **Content** | `content` | Canonical text (human-legible) |
| **Summary** | `meta_summary` | Brief Cortex-generated overview |
| **Meta** | `meta` (JSONB) | Small blob: source app, tool name, latency, IDs, tags |
| **Provenance** | `source_uri` | Where it came from (URI, message ID, file hash) |
| **Idempotency** | `dedupe_key` | Hash of normalized content + metadata |
| **Importance** | `importance_score` | 0.0-1.0 quick triage score |
| **Lifecycle** | `is_deleted` | Soft delete (provenance preservation) |

### Field Ordering Optimization

**`meta_summary` is placed before `content`** in the schema for query efficiency:
- Enables `SELECT meta_summary` without loading full `content`
- Pack compiler can use summaries, skip content (token savings)
- Logical semantic flow: summary → full content

---

## From Events to Memories

### The Selector's Role

A **selector** (future component) scans recent Events and fires triggers:

| Trigger | Meaning | Example |
|---------|---------|---------|
| **Novelty** | First time this fact seen | "User mentioned new project 'Acme'" |
| **Contradiction** | Conflicts with prior knowledge | "User says they like Python (previously said they didn't)" |
| **Outcome** | Decision + result pairing | "Chose approach A → succeeded" |
| **Repetition** | Same theme recurring | "Third time user asked about authentication" |
| **Feedback** | Explicit human signals | "User marked this as important" |
| **Emotion/Salience** | Strong sentiment or high impact | "User expressed frustration with current workflow" |

### Memory Creation

When a trigger fires, the selector composes a **Memory**:
- Subjective summary (not chronological list)
- Links back to precise Event IDs
- Optional importance/confidence score
- Optionally seeds a **Lesson** (what/why/how/when) if pattern merits

**Relationship:** `Memory --[based_on]--> Events (many-to-many)`

---

## API Operations

### Domain Layer (`backend/app/domain/event_operations.py`)

All operations are **async** and **stateless** (static methods):

```python
class EventOperations:
    # Core CRUD
    async def create(session, data: EventCreate) -> Event
    async def get_by_id(session, event_id: UUID) -> Optional[Event]
    async def update(session, event_id: UUID, data: EventUpdate) -> Event
    async def soft_delete(session, event_id: UUID) -> Event
    async def restore(session, event_id: UUID) -> Event

    # Queries
    async def get_recent(session, spirit_id: UUID, ...) -> List[Event]
    async def get_by_session(session, spirit_id: UUID, session_id: str) -> List[Event]
    async def count_by_spirit(session, spirit_id: UUID, ...) -> int

    # Helpers
    async def update_meta_summary(session, event_id: UUID, summary: str) -> Event
    async def update_importance(session, event_id: UUID, score: float) -> Event
```

### REST API Endpoints (`backend/app/api/routes/events.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/events` | Create event (201 Created, 409 on duplicate `dedupe_key`) |
| `GET` | `/api/events` | List events with filters (smart routing: session vs recent) |
| `GET` | `/api/events/{id}` | Get single event (404 if not found) |
| `PATCH` | `/api/events/{id}` | Partial update (`meta_summary`, `importance_score`, `meta`, `is_deleted`) |
| `DELETE` | `/api/events/{id}` | Soft delete (204 No Content) |

### Smart List Behavior

The `GET /api/events` endpoint has **dual personality**:

- **If `session_id` provided** → `get_by_session()` → **chronological order (ASC)** for conversation replay
- **Otherwise** → `get_recent()` → **recent-first order (DESC)** for activity feed

This avoids endpoint proliferation while serving both use cases naturally.

---

## Practical Ingestion Rules

### 1. Normalize at the Door

Turn any modality into: `(event_type, occurred_at, content, meta, session_id, source_uri)`

**Example transforms:**
- Slack message → `message.in` with `source_uri: "slack://T123/C456/p789"`
- API error → `error` with `meta: {"status_code": 500, "endpoint": "/api/users"}`
- File upload → `file.ingested` with `source_uri: "s3://bucket/key"`

### 2. Keep It Small & Legible

- Prefer concise `content` over giant dumps
- Stash large blobs as artifacts elsewhere (S3, object storage) and link via `source_uri`
- Use `meta` for structured data, not prose

### 3. Be Idempotent

Compute `dedupe_key` before insertion:

```python
# Auto-generated in EventOperations.create()
dedupe_key = SHA256(spirit_id | event_type | content[:100] | occurred_at | source_uri)[:32]
```

- Database enforces uniqueness constraint
- Duplicate Events return 409 Conflict
- Prevents re-ingestion of same source data

### 4. Separate Clocks

**Never conflate `occurred_at` and `created_at`:**

- `occurred_at` — Source system timestamp (e.g., Slack message sent at 2:15 PM)
- `created_at` — Elephantasm ingestion timestamp (e.g., processed at 2:17 PM)

This separation enables:
- Lag analysis (ingestion delay)
- Accurate conversation replay
- Retroactive imports (historical data)

### 5. Tag Lightly

A few tags in `meta` go a long way:

```json
{
  "topic": "authentication",
  "tool": "web_search",
  "latency_ms": 342,
  "source_app": "slack"
}
```

Don't over-structure — let patterns emerge before formalizing schema.

---

## Storage & Indexing

### Database Indexes (Implemented)

```sql
-- Primary key
CREATE UNIQUE INDEX ON events (id);

-- Ownership + temporal queries
CREATE INDEX ix_events_spirit_id ON events (spirit_id);

-- Fast classification filtering
CREATE INDEX ix_events_event_type ON events (event_type);

-- Fast session/thread retrieval
CREATE INDEX ix_events_session_id ON events (session_id);

-- Idempotency enforcement
CREATE UNIQUE INDEX ON events (dedupe_key) WHERE dedupe_key IS NOT NULL;
```

### Common Query Patterns

**Timeline (recent first):**
```sql
SELECT * FROM events
WHERE spirit_id = ? AND is_deleted = FALSE
ORDER BY occurred_at DESC, created_at DESC
LIMIT 50;
```

**Session replay (chronological):**
```sql
SELECT * FROM events
WHERE spirit_id = ? AND session_id = ? AND is_deleted = FALSE
ORDER BY occurred_at ASC, created_at ASC;
```

**Type filtering:**
```sql
SELECT * FROM events
WHERE spirit_id = ? AND event_type = 'message.in' AND is_deleted = FALSE
ORDER BY occurred_at DESC;
```

---

## Retention & Promotion

### Keep MVP Simple

1. **Keep all Events** for a reasonable horizon (30-90 days)
2. **Promote important signals** into Memories and Lessons (durable, persist indefinitely)
3. **Apply decay to Events first** if storage trimming needed — Memories/Lessons persist longer

### Provenance Preservation

**Soft deletes only** — no hard deletes by default:
- `is_deleted = TRUE` marks Events as removed but keeps data
- Future: archive/purge endpoint for GDPR compliance
- Rationale: **provenance is core to LTAM philosophy**

---

## Examples

### Example 1: Simple Chat Exchange

**Scenario:** User asks a question, agent responds

**Events created:**
1. `message.in` — User: "What's the weather in SF?"
2. `message.out` — Agent: "Let me check that for you."

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "spirit_id": "123e4567-e89b-12d3-a456-426614174000",
    "event_type": "message.in",
    "content": "What's the weather in SF?",
    "occurred_at": "2025-10-17T14:23:15Z",
    "session_id": "conv_abc123",
    "meta": {"source_app": "web_chat"}
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "spirit_id": "123e4567-e89b-12d3-a456-426614174000",
    "event_type": "message.out",
    "content": "Let me check that for you.",
    "occurred_at": "2025-10-17T14:23:17Z",
    "session_id": "conv_abc123",
    "meta": {"latency_ms": 234}
  }
]
```

### Example 2: Tool Call with Error

**Scenario:** Agent attempts web search, encounters error, retries successfully

**Events created (4 total):**
1. `tool.call` — Initiated web search
2. `error` — API timeout
3. `tool.call` — Retry with different parameters
4. `tool.result` — Success

This granularity enables a Memory like:
> *"When the weather API timed out, we successfully retried with a shorter timeout parameter."*

**Links back to:** Events #1, #2, #3, #4 (precise causality)

### Example 3: Document Ingestion

**Scenario:** User uploads 3 PDF files

**Events created (3 total):**
```json
[
  {
    "event_type": "file.ingested",
    "content": "Uploaded: Q4_Financial_Report.pdf",
    "source_uri": "s3://elephantasm-docs/abc123.pdf",
    "meta": {"file_size": 2453900, "page_count": 45}
  },
  {
    "event_type": "file.ingested",
    "content": "Uploaded: Team_OKRs.pdf",
    "source_uri": "s3://elephantasm-docs/def456.pdf",
    "meta": {"file_size": 892100, "page_count": 12}
  },
  {
    "event_type": "file.ingested",
    "content": "Uploaded: Architecture_Diagram.pdf",
    "source_uri": "s3://elephantasm-docs/ghi789.pdf",
    "meta": {"file_size": 3201400, "page_count": 8}
  }
]
```

### Example 4: Six-Message Chat with Tool Call

**Conversation flow:**
1. User: "Can you help me debug this error?"
2. Agent: "Sure, let me analyze it."
3. User: "Here's the stack trace..."
4. Agent: "I'll search for solutions."
5. *[Agent calls web search tool]*
6. *[Tool returns results]*
7. Agent: "Found a fix! Try updating the dependency."
8. User: "That worked, thanks!"

**Events created (8 total):**
- 3× `message.in` (user messages 1, 3, 8)
- 3× `message.out` (agent messages 2, 4, 7)
- 1× `tool.call` (web search initiation)
- 1× `tool.result` (search results)

**Potential Memory formation:**
> *"Successfully resolved a dependency error by web-searching the stack trace. User confirmed fix worked."*

**Links to:** All 8 Events (complete conversation context)

---

## Summary: Why Events Matter

Events are the **heartbeat of Elephantasm** — each one marks that life is happening, experience is accumulating, time is flowing.

**Without Events:**
- No structure, only noise
- No causality, only correlation
- No proof, only speculation
- No growth, only stasis

**With Events:**
- **Structure** emerges from chaos
- **Causality** is traceable and auditable
- **Knowledge** is empirically grounded
- **Identity** evolves through real experience

Events are not just *what happened* — they are the system's **proof that it was there when it happened.**

They are the atomic substrate upon which all higher cognition rests: the sensation that becomes impression, the impression that becomes understanding, the understanding that becomes identity.

**Every Memory, Lesson, and fragment of Knowledge ultimately points back to Events and says:**
*"This is why I exist. This is what I learned. This is what was true."*

---

## References

- **Implementation**: `backend/app/models/database/events.py`
- **Domain Logic**: `backend/app/domain/event_operations.py`
- **API Endpoints**: `backend/app/api/routes/events.py`
- **Changelog**: `docs/changelog/changelog.md` (v0.0.1 - v0.0.7)
- **Architecture**: `.claude/vision.md`
