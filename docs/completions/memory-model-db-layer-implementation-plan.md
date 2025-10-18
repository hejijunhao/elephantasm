# Memory Model - Database Layer Implementation Plan

**Version**: 0.0.10
**Focus**: Database schema + SQLModel only (no domain operations, no API routes)
**Estimated Time**: 45-60 minutes
**Pattern**: Base + Table + DTOs (consistent with Events/Spirits models)

---

## 1. Overview

Implement the **Memory** model as the second cognitive layer in Elephantasm's hierarchy:

```
Events (raw experience) → Memories (subjective interpretation) → Lessons → Knowledge → Identity
```

This implementation focuses **exclusively** on the database layer:
- ✅ SQLModel definition (`backend/app/models/database/memories.py`)
- ✅ Alembic migration (new table: `memories`)
- ✅ Schema verification in Supabase
- ❌ Domain operations (deferred to v0.0.11)
- ❌ API routes (deferred to v0.0.11)
- ❌ Junction table `memory_event_link` (deferred to v0.0.11)

---

## 2. Conceptual Context

### What is a Memory?

A **Memory** is a *subjective interpretation or condensation* of one or more Events. It transforms "what happened" into "what it meant."

**Key Characteristics**:
- **Derived**, not raw — synthesized from Events (sometimes across time)
- **Subjective** — reflects what the Spirit considered meaningful
- **Compact** — holds distilled understanding, not full transcripts
- **Evolving** — can merge, split, decay, or be promoted into Lessons

### Four-Factor Recall System

Memory recall is driven by four floating-point scores (0.0-1.0):

1. **Importance** (static/semi-static): How significant the memory is
2. **Confidence** (static/semi-static): How stable/certain the memory is
3. **Recency** (auto-computed): Pure temporal distance from occurrence
4. **Decay** (auto-computed): Composite fading score (importance + confidence + recency)

**Verbal Model**: "High is good" for positive signals:
- High importance → stronger recall ✅
- High confidence → stronger recall ✅
- High recency → stronger recall ✅
- High decay → weaker recall ❌ (memory has faded)

---

## 3. Database Schema Design

### Table: `memories`

| Column          | Type         | Constraints                     | Description                                      |
| --------------- | ------------ | ------------------------------- | ------------------------------------------------ |
| `id`            | UUID         | PK, default: `gen_random_uuid()`| Primary key                                      |
| `spirit_id`     | UUID         | FK → `spirits.id`, NOT NULL, indexed | Owner/identity entity                     |
| `summary`       | TEXT         | NOT NULL                        | Compact narrative essence                        |
| `importance`    | FLOAT        | NOT NULL, CHECK (0.0 ≤ x ≤ 1.0) | Weight in recall/curation priority               |
| `confidence`    | FLOAT        | NOT NULL, CHECK (0.0 ≤ x ≤ 1.0) | Stability/certainty of the memory                |
| `recency_score` | FLOAT        | NULLABLE, CHECK (0.0 ≤ x ≤ 1.0) | Cached temporal freshness (optional)             |
| `decay_score`   | FLOAT        | NULLABLE, CHECK (0.0 ≤ x ≤ 1.0) | Cached fading score (optional)                   |
| `state`         | VARCHAR(20)  | NOT NULL, CHECK IN (...)        | Lifecycle: `active`, `decaying`, `archived`      |
| `time_start`    | TIMESTAMPTZ  | NULLABLE                        | When underlying events began                     |
| `time_end`      | TIMESTAMPTZ  | NULLABLE                        | When underlying events ended                     |
| `meta`          | JSONB        | NOT NULL, default: `{}`         | Topics, tags, curator signals (flexible)         |
| `created_at`    | TIMESTAMPTZ  | NOT NULL, auto-set              | When memory was created (via TimestampMixin)     |
| `updated_at`    | TIMESTAMPTZ  | NOT NULL, auto-update           | When memory was last modified (via TimestampMixin)|
| `is_deleted`    | BOOLEAN      | NOT NULL, default: `false`      | Soft delete flag (provenance preservation)       |

### Indexes

1. **`ix_memories_spirit_id`** — Query memories by owner (FK index)
2. **`ix_memories_state`** — Filter by lifecycle state (`active`, `decaying`, `archived`)
3. **`ix_memories_importance`** — Order by importance for high-priority recall
4. **`ix_memories_time_end`** — Order by recency (most recent first)

### Foreign Key

- `memories.spirit_id → spirits.id` (CASCADE behavior TBD — likely RESTRICT for safety)

---

## 4. Model Implementation

### File: `backend/app/models/database/memories.py`

**Pattern**: Base + Table + DTOs (100% consistent with Events/Spirits)

#### 4.1 MemoryState Enum

```python
from enum import Enum

class MemoryState(str, Enum):
    """Lifecycle states for memory recall and curation."""
    ACTIVE = "active"         # Actively recalled, high attention
    DECAYING = "decaying"     # Fading from active recall
    ARCHIVED = "archived"     # Preserved but rarely recalled
```

#### 4.2 MemoryBase (Shared Fields)

**Required Fields**:
- `spirit_id: UUID` — Owner entity (FK to spirits.id)
- `summary: str` — Compact narrative
- `importance: float` — 0.0-1.0, weight in recall
- `confidence: float` — 0.0-1.0, stability/certainty
- `state: MemoryState` — Lifecycle state

**Optional Fields** (nullable for flexibility):
- `recency_score: float | None` — Cached temporal freshness
- `decay_score: float | None` — Cached fading score
- `time_start: datetime | None` — When underlying events began
- `time_end: datetime | None` — When underlying events ended
- `meta: dict` — JSONB for topics, tags, curator signals

**Validation**:
- `importance`: `Field(ge=0.0, le=1.0)` (range constraint)
- `confidence`: `Field(ge=0.0, le=1.0)` (range constraint)
- `recency_score`: `Field(ge=0.0, le=1.0, default=None)` (optional, range constraint)
- `decay_score`: `Field(ge=0.0, le=1.0, default=None)` (optional, range constraint)
- `meta`: `Field(default_factory=dict)` (avoid mutable default bug)

#### 4.3 Memory (Table Entity)

```python
class Memory(MemoryBase, TimestampMixin, table=True):
    """
    Memory table entity. Subjective interpretation of Events.
    Inherits created_at, updated_at from TimestampMixin.
    """
    __tablename__ = "memories"

    id: UUID = Field(
        default=None,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()")
        )
    )

    spirit_id: UUID = Field(
        foreign_key="spirits.id",
        index=True,
        description="Owner spirit ID"
    )

    state: MemoryState = Field(
        index=True,
        description="Lifecycle state (active/decaying/archived)"
    )

    importance: float = Field(
        index=True,
        description="Weight in recall/curation (0.0-1.0)"
    )

    time_end: datetime | None = Field(
        default=None,
        index=True,
        description="When underlying events ended (for recency calculation)"
    )

    is_deleted: bool = Field(
        default=False,
        description="Soft delete flag (provenance preservation)"
    )
```

#### 4.4 DTOs (Data Transfer Objects)

**MemoryCreate** — Ingestion payload (client → server):
```python
class MemoryCreate(MemoryBase):
    """Create a new memory (inherits all MemoryBase fields)."""
    pass
```

**MemoryRead** — Response model (server → client):
```python
class MemoryRead(MemoryBase):
    """Memory response with readonly fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
```

**MemoryUpdate** — Partial update (PATCH):
```python
class MemoryUpdate(SQLModel):
    """Partial update for mutable fields only."""
    summary: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    recency_score: float | None = Field(default=None, ge=0.0, le=1.0)
    decay_score: float | None = Field(default=None, ge=0.0, le=1.0)
    state: MemoryState | None = None
    time_start: datetime | None = None
    time_end: datetime | None = None
    meta: dict | None = None
    is_deleted: bool | None = None
```

---

## 5. Implementation Steps

### Step 1: Create Memory Model File (~20 minutes)

**File**: `backend/app/models/database/memories.py`

1. Import dependencies:
   ```python
   from datetime import datetime
   from enum import Enum
   from uuid import UUID

   from sqlalchemy import Column, text
   from sqlalchemy.dialects.postgresql import UUID as PGUUID
   from sqlmodel import Field, SQLModel

   from backend.app.models.database.mixins import TimestampMixin
   ```

2. Define `MemoryState` enum
3. Define `MemoryBase` with all shared fields + validation
4. Define `Memory` table entity with DB-specific configs
5. Define DTOs: `MemoryCreate`, `MemoryRead`, `MemoryUpdate`

**Validation Checklist**:
- ✅ All float scores have `ge=0.0, le=1.0` constraints
- ✅ `meta` uses `Field(default_factory=dict)` (not `default={}`)
- ✅ `spirit_id` has `foreign_key="spirits.id"` and `index=True`
- ✅ `state` has `index=True`
- ✅ `importance` has `index=True`
- ✅ `time_end` has `index=True` (for recency queries)
- ✅ `id` uses `gen_random_uuid()` for DB-level generation
- ✅ TimestampMixin inherited for `created_at`, `updated_at`

### Step 2: Update Migration Environment (~5 minutes)

**File**: `backend/migrations/env.py`

Add Memory model import for autogenerate detection:

```python
# Import all models for Alembic autogenerate
from backend.app.models.database.events import Event
from backend.app.models.database.mixins import TimestampMixin
from backend.app.models.database.spirits import Spirit
from backend.app.models.database.users import User
from backend.app.models.database.memories import Memory  # Add this line
```

### Step 3: Generate Migration (~5 minutes)

```bash
cd backend
alembic revision --autogenerate -m "add memories table"
```

**Review Generated Migration**:
- ✅ `memories` table created with all columns
- ✅ Indexes: `spirit_id`, `state`, `importance`, `time_end`
- ✅ Foreign key: `memories.spirit_id → spirits.id`
- ✅ CHECK constraints for float ranges (0.0-1.0)
- ✅ ENUM values for `state` field (active, decaying, archived)

### Step 4: Execute Migration (~2 minutes)

```bash
alembic upgrade head
```

### Step 5: Verify Schema in Supabase (~5 minutes)

**Via Supabase Dashboard** → Table Editor:
1. ✅ `memories` table exists
2. ✅ Columns match schema design (id, spirit_id, summary, importance, confidence, etc.)
3. ✅ Indexes created correctly
4. ✅ Foreign key constraint: `memories.spirit_id → spirits.id`
5. ✅ UUID generation works: `gen_random_uuid()`
6. ✅ JSONB field `meta` created successfully
7. ✅ Timestamp defaults (`created_at`, `updated_at`) functional

### Step 6: Test Model Import (~2 minutes)

```bash
cd backend
python3 -c "from backend.app.models.database.memories import Memory, MemoryCreate, MemoryRead, MemoryUpdate, MemoryState; print('✅ Memory model imports successfully')"
```

---

## 6. Design Decisions & Rationale

### 6.1 Why Nullable `recency_score` and `decay_score`?

**Option A** (chosen): Store as nullable, compute on-the-fly
- **Pro**: Always accurate (no staleness)
- **Pro**: Simpler initial implementation
- **Pro**: No periodic update job needed yet
- **Con**: Slight compute overhead during retrieval

**Option B**: Store as required, update via Dreamer
- **Pro**: Faster retrieval (pre-computed)
- **Con**: Can become stale between Dreamer runs
- **Con**: Requires background job infrastructure

**Decision**: Start with **Option A**, migrate to **Option B** when Dreamer is implemented (v0.1.x).

### 6.2 Why Separate `time_start` and `time_end`?

Memories can span multiple Events across time:
- **Single Event**: `time_start = time_end = event.occurred_at`
- **Event Cluster**: `time_start = earliest_event.occurred_at`, `time_end = latest_event.occurred_at`
- **Windowed Synthesis**: e.g., "session from 2pm-4pm" → span = 2 hours

This enables accurate recency calculation: `age = now - time_end`

### 6.3 Why `state` as String Enum (not Integer)?

Following Events model precedent (`event_type` as string enum):
- **Pro**: Self-documenting in queries (`WHERE state = 'active'` vs `WHERE state = 1`)
- **Pro**: Easier debugging (raw SQL shows readable values)
- **Pro**: JSON serialization is cleaner
- **Con**: Slightly more storage (negligible for 3 values)

### 6.4 Why Index on `importance` and `time_end`?

**Common Query Patterns**:
1. "Get top N most important memories" → `ORDER BY importance DESC LIMIT N` (uses `ix_memories_importance`)
2. "Get most recent memories" → `ORDER BY time_end DESC LIMIT N` (uses `ix_memories_time_end`)
3. "Get active memories for spirit" → `WHERE spirit_id = X AND state = 'active'` (uses `ix_memories_spirit_id` + `ix_memories_state`)

These indexes optimize pack compiler retrieval.

### 6.5 Why JSONB for `meta` (not Separate Tables)?

**Use Case**: Topics, tags, curator signals (e.g., `{"topics": ["api-errors", "retry-logic"], "merged_from": [uuid1, uuid2]}`)

**Rationale**:
- **Flexible schema** — can evolve without migrations
- **Fast queries** — GIN indexes support `WHERE meta @> '{"topics": ["api-errors"]}'`
- **Simple storage** — no JOIN complexity for tags
- **Phase 1 scope** — structured tags can be promoted to separate table in Phase 2 if needed

---

## 7. Known Limitations (MVP Scope)

### Deferred to v0.0.11+:
- ❌ `memory_event_link` junction table (Event → Memory provenance)
- ❌ Domain operations (`MemoryOperations` class)
- ❌ API routes (`POST /api/memories`, `GET /api/memories`, etc.)
- ❌ Memory synthesis logic (Cortex integration)

### Deferred to Phase 2:
- ❌ Vector embeddings (`memory_embedding` table)
- ❌ Semantic search / similarity retrieval
- ❌ Automatic recency/decay score updates (Dreamer)
- ❌ Memory merging, splitting, promotion to Lessons

### Intentional Omissions:
- No bidirectional relationship to Spirits yet (prevents circular imports)
- No relationship to Events yet (junction table not created)
- No composite indexes yet (wait for real query patterns to emerge)

---

## 8. Testing Checklist

### Syntax & Import Validation:
- [ ] `memories.py` file created with no syntax errors
- [ ] `python3 -c "from backend.app.models.database.memories import Memory"` succeeds
- [ ] All DTOs importable (`MemoryCreate`, `MemoryRead`, `MemoryUpdate`)
- [ ] `MemoryState` enum accessible

### Migration Validation:
- [ ] `alembic revision --autogenerate` generates migration successfully
- [ ] Migration file contains `memories` table creation
- [ ] Migration file contains all indexes
- [ ] Migration file contains FK constraint to `spirits`
- [ ] `alembic upgrade head` executes without errors

### Schema Validation (Supabase):
- [ ] `memories` table visible in Table Editor
- [ ] All columns present with correct types
- [ ] Indexes present: `spirit_id`, `state`, `importance`, `time_end`
- [ ] FK constraint exists: `memories.spirit_id → spirits.id`
- [ ] `gen_random_uuid()` works for `id` field
- [ ] JSONB `meta` field created

### Data Validation (Optional):
- [ ] Insert test memory via Supabase SQL Editor:
  ```sql
  INSERT INTO memories (spirit_id, summary, importance, confidence, state, meta)
  SELECT id, 'Test memory', 0.8, 0.9, 'active', '{}'::jsonb
  FROM spirits LIMIT 1;
  ```
- [ ] Verify `created_at`, `updated_at` auto-populated
- [ ] Verify `id` auto-generated as UUID
- [ ] Delete test memory

---

## 9. Success Criteria

**v0.0.10 is complete when**:

1. ✅ `backend/app/models/database/memories.py` exists with:
   - `MemoryState` enum
   - `MemoryBase` base class
   - `Memory` table entity
   - `MemoryCreate`, `MemoryRead`, `MemoryUpdate` DTOs

2. ✅ Migration executed successfully:
   - `memories` table created in Supabase
   - All columns, indexes, FK constraints present

3. ✅ Schema verification passed:
   - Visible in Supabase Table Editor
   - UUID generation works
   - Timestamps auto-populate

4. ✅ Model imports successfully:
   - `python3 -c "from backend.app.models.database.memories import Memory"` works
   - No import errors, no circular dependencies

**Documentation**:
- ✅ Completion summary added to `docs/completions/` (after implementation)
- ✅ Changelog updated with v0.0.10 entry

---

## 10. Next Steps (Post-Implementation)

### v0.0.11 — Memory Domain Operations:
- Implement `MemoryOperations` class (domain logic)
- Methods: `create()`, `get_by_id()`, `get_by_spirit()`, `update()`, `soft_delete()`, `restore()`
- Query helpers: `get_active()`, `get_by_state()`, `search_by_summary()`
- Recency/decay score computation utilities

### v0.0.12 — Memory API Routes:
- `POST /api/memories` — Create memory
- `GET /api/memories` — List memories (filter by spirit_id, state, importance)
- `GET /api/memories/{id}` — Get single memory
- `PATCH /api/memories/{id}` — Update memory
- `DELETE /api/memories/{id}` — Soft delete

### v0.0.13 — Memory-Event Junction Table:
- Create `memory_event_link` table (many-to-many)
- Add `weight` field (contribution weight of each Event to Memory)
- Migration + relationship models

### Phase 2 — Intelligence Layer:
- Pack Compiler (deterministic memory retrieval)
- Cortex (event enrichment + memory synthesis)
- Dreamer (curation loop: merge, decay, promote)

---

## 11. Architectural Consistency

This implementation maintains 100% pattern consistency with existing models:

| Pattern                     | Events | Spirits | Users | **Memories** |
| --------------------------- | ------ | ------- | ----- | ------------ |
| Base + Table + DTOs         | ✅      | ✅       | ✅     | ✅            |
| TimestampMixin              | ✅      | ✅       | ✅     | ✅            |
| DB-level UUID generation    | ✅      | ✅       | ✅     | ✅            |
| Soft deletes (`is_deleted`) | ✅      | ✅       | ✅     | ✅            |
| JSONB metadata              | ✅      | ✅       | —     | ✅            |
| Foreign key to Spirit       | ✅      | —       | —     | ✅            |
| String enum for type/state  | ✅      | —       | —     | ✅            |
| Float validation (0.0-1.0)  | ✅      | —       | —     | ✅            |

**Deviation**: None. This is the cleanest path forward.

---

## 12. File Checklist

**Files to Create**:
- [ ] `backend/app/models/database/memories.py` (new model)
- [ ] `backend/migrations/versions/<hash>_add_memories_table.py` (autogenerated)

**Files to Modify**:
- [ ] `backend/migrations/env.py` (add Memory import)

**Files to Verify** (no changes):
- [ ] `backend/app/core/database.py` (unchanged, already async-ready)
- [ ] `backend/app/core/config.py` (unchanged, DB config already set)

**Total Changes**: 1 new model file + 1 migration file + 1 import line

---

**End of Plan** — Ready for implementation when you are! 🐘
