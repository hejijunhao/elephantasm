# Spirit Operations Implementation Plan

**Version:** 1.0
**Date:** 2025-10-17
**Status:** Planning
**Estimated Time:** 30-45 minutes

---

## Overview

Implement `SpiritOperations` domain logic layer for Spirit CRUD operations, following the same architectural patterns established in `EventOperations`.

**Goal:** Provide business logic layer for Spirit management with FK validation, soft deletes, and async operations.

---

## Reference Architecture

### Pattern to Follow: EventOperations

**Key Characteristics:**
- Static methods (no instance state)
- Async session-based operations
- No transaction management (routes handle commits)
- FK validation before mutations
- Soft delete support
- HTTPException for error handling
- Type hints on all methods
- Condensed docstrings

**File Location:**
- Reference: `backend/app/domain/event_operations.py`
- New File: `backend/app/domain/spirit_operations.py`

---

## Spirit Model Analysis

### Current Structure (`backend/app/models/database/spirits.py`)

**Fields:**
- `id: UUID` - Primary key (DB-generated via `gen_random_uuid()`)
- `name: str` - Human-readable spirit name (max 255 chars, required)
- `description: str | None` - Optional description
- `meta: dict[str, Any] | None` - JSONB metadata
- `created_at: datetime` - Auto-managed (TimestampMixin)
- `updated_at: datetime` - Auto-managed (TimestampMixin)
- `is_deleted: bool` - Soft delete flag (default False)

**Relationships:**
- `events: list[Event]` - One-to-many with Events

**DTOs:**
- `SpiritCreate` - Ingestion (name required, description/meta optional)
- `SpiritRead` - Response (includes id, timestamps)
- `SpiritUpdate` - Partial update (all fields optional)

### Differences from Events

**Simpler Model:**
- No foreign keys to validate (Spirit is the root entity)
- No complex metadata fields (meta_summary, occurred_at, session_id, dedupe_key, importance_score)
- No auto-generation logic (dedupe_key equivalent)
- Fewer optional fields

**Implications:**
- Simpler validation logic
- No FK checks in create()
- No custom key generation
- More straightforward CRUD

---

## Required Operations

### Core CRUD

#### 1. `create(session, data: SpiritCreate) -> Spirit`
**Purpose:** Create new spirit

**Logic:**
- Validate name is not empty (Pydantic handles this)
- No FK validation needed (root entity)
- Create Spirit instance
- Add to session, flush to get ID
- Return created spirit

**Errors:**
- 400 Bad Request - Validation errors (if any custom validation added)

#### 2. `get_by_id(session, spirit_id: UUID, include_deleted: bool = False) -> Optional[Spirit]`
**Purpose:** Fetch spirit by ID

**Logic:**
- Query Spirit by primary key
- Return None if not found
- Return None if soft-deleted (unless include_deleted=True)

**Returns:** Spirit or None

#### 3. `get_all(session, limit: int = 50, offset: int = 0, include_deleted: bool = False) -> List[Spirit]`
**Purpose:** List all spirits (paginated)

**Logic:**
- Select all spirits
- Filter out soft-deleted (unless include_deleted=True)
- Order by created_at DESC (newest first)
- Apply pagination (limit/offset)

**Returns:** List of Spirits

#### 4. `update(session, spirit_id: UUID, data: SpiritUpdate) -> Spirit`
**Purpose:** Update spirit (partial)

**Logic:**
- Fetch spirit by ID
- Raise 404 if not found
- Apply partial update via model_dump(exclude_unset=True)
- Flush and return updated spirit

**Errors:**
- 404 Not Found - Spirit doesn't exist

#### 5. `soft_delete(session, spirit_id: UUID) -> Spirit`
**Purpose:** Mark spirit as deleted

**Logic:**
- Use update() with is_deleted=True
- Preserve spirit data for provenance

**Errors:**
- 404 Not Found - Spirit doesn't exist

#### 6. `restore(session, spirit_id: UUID) -> Spirit`
**Purpose:** Restore soft-deleted spirit

**Logic:**
- Use update() with is_deleted=False

**Errors:**
- 404 Not Found - Spirit doesn't exist

### Query Operations

#### 7. `search_by_name(session, name_query: str, limit: int = 50) -> List[Spirit]`
**Purpose:** Search spirits by name (partial match, case-insensitive)

**Logic:**
- Use SQL ILIKE for partial matching
- Filter out soft-deleted
- Order by name ASC (alphabetical)
- Limit results

**Returns:** List of matching Spirits

**Implementation:**
```python
query = select(Spirit).where(
    and_(
        Spirit.name.ilike(f"%{name_query}%"),
        Spirit.is_deleted.is_(False)
    )
).order_by(Spirit.name.asc()).limit(limit)
```

#### 8. `count_all(session, include_deleted: bool = False) -> int`
**Purpose:** Count total spirits

**Logic:**
- Count spirits with optional deleted filter
- Useful for pagination metadata

**Returns:** Integer count

### Relationship Helpers

#### 9. `get_with_events(session, spirit_id: UUID, include_deleted: bool = False) -> Optional[Spirit]`
**Purpose:** Fetch spirit with eager-loaded events relationship

**Logic:**
- Use selectinload() for events relationship
- Avoid N+1 query problem when accessing spirit.events

**Implementation:**
```python
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(Spirit)
    .where(Spirit.id == spirit_id)
    .options(selectinload(Spirit.events))
)
return result.scalar_one_or_none()
```

**Returns:** Spirit with events loaded, or None

---

## Implementation Checklist

### File Structure

```python
"""Domain operations for Spirits - business logic layer.

CRUD operations and business logic for Spirits.
No transaction management - routes handle commits/rollbacks.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from backend.app.models.database.spirits import Spirit, SpiritCreate, SpiritUpdate


class SpiritOperations:
    """Spirit business logic. Static methods, async session-based, no commits."""

    @staticmethod
    async def create(session: AsyncSession, data: SpiritCreate) -> Spirit:
        """Create spirit. No FK validation needed (root entity)."""
        ...

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        spirit_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Spirit]:
        """Get spirit by ID. Returns None if not found or soft-deleted."""
        ...

    # ... additional methods
```

### Method Signatures (Complete List)

```python
# Core CRUD
async def create(session: AsyncSession, data: SpiritCreate) -> Spirit
async def get_by_id(session: AsyncSession, spirit_id: UUID, include_deleted: bool = False) -> Optional[Spirit]
async def get_all(session: AsyncSession, limit: int = 50, offset: int = 0, include_deleted: bool = False) -> List[Spirit]
async def update(session: AsyncSession, spirit_id: UUID, data: SpiritUpdate) -> Spirit
async def soft_delete(session: AsyncSession, spirit_id: UUID) -> Spirit
async def restore(session: AsyncSession, spirit_id: UUID) -> Spirit

# Query operations
async def search_by_name(session: AsyncSession, name_query: str, limit: int = 50) -> List[Spirit]
async def count_all(session: AsyncSession, include_deleted: bool = False) -> int

# Relationship helpers
async def get_with_events(session: AsyncSession, spirit_id: UUID, include_deleted: bool = False) -> Optional[Spirit]
```

**Total Methods:** 9 (vs EventOperations: 10 methods)

---

## Key Differences from EventOperations

### Simpler Implementation

1. **No FK Validation:**
   - Events validate spirit_id FK → Spirit exists
   - Spirits have no parent entity → No validation needed

2. **No Auto-Generation Logic:**
   - Events auto-generate dedupe_key if source_uri provided
   - Spirits have no equivalent auto-generated fields

3. **No Range Validation:**
   - Events validate importance_score (0.0-1.0)
   - Spirits have no numeric range fields

4. **Simpler Queries:**
   - Events have complex filtering (event_type, session_id, min_importance, dual ordering)
   - Spirits primarily filter by name and deleted status

5. **Root Entity Semantics:**
   - Spirits are the "owner" of the hierarchy
   - Query patterns focus on listing/searching, not session-based grouping

### Additional Features

1. **Name Search:**
   - Events don't need content search (too broad)
   - Spirits benefit from name-based lookup (ILIKE query)

2. **Eager Loading Helper:**
   - Useful for "get spirit + all their events" use case
   - Demonstrates relationship loading pattern for future models

---

## Testing Strategy

### Unit Tests (`tests/unit/test_spirit_operations.py`)

**Test Cases:**
1. `test_create_spirit` - Basic creation
2. `test_create_spirit_minimal` - Only required fields (name)
3. `test_get_by_id_found` - Fetch existing spirit
4. `test_get_by_id_not_found` - Returns None
5. `test_get_by_id_soft_deleted` - Respects is_deleted flag
6. `test_get_all_pagination` - Limit/offset work correctly
7. `test_update_partial` - Partial update via SpiritUpdate
8. `test_soft_delete` - Mark as deleted
9. `test_restore` - Undelete spirit
10. `test_search_by_name` - ILIKE partial matching
11. `test_get_with_events` - Eager loading

### Integration Tests (if needed)
- Test with actual database
- Verify relationship loading works correctly

---

## Code Style Guidelines

### Docstrings (Condensed Format)

**Pattern:**
```python
async def method_name(...) -> ReturnType:
    """Single-line summary with key behaviors. Raises HTTPException XXX (condition)."""
```

**Examples:**
```python
async def create(session: AsyncSession, data: SpiritCreate) -> Spirit:
    """Create spirit. No FK validation needed (root entity)."""

async def get_by_id(session: AsyncSession, spirit_id: UUID, include_deleted: bool = False) -> Optional[Spirit]:
    """Get spirit by ID. Returns None if not found or soft-deleted (unless include_deleted=True)."""

async def update(session: AsyncSession, spirit_id: UUID, data: SpiritUpdate) -> Spirit:
    """Update spirit (partial). Raises HTTPException 404 (not found)."""
```

### Type Hints

- Full type hints on all parameters and returns
- `Optional[Spirit]` for nullable returns
- `List[Spirit]` for collections
- `UUID` for IDs
- `AsyncSession` for database sessions

### Error Handling

```python
# 404 Not Found
if not spirit:
    raise HTTPException(
        status_code=404,
        detail=f"Spirit {spirit_id} not found"
    )

# 400 Bad Request (only if custom validation added)
raise HTTPException(
    status_code=400,
    detail="Validation error message"
)
```

---

## Implementation Steps

### Step 1: Create File (5 minutes)
1. Create `backend/app/domain/spirit_operations.py`
2. Add module docstring
3. Add imports
4. Create `SpiritOperations` class skeleton

### Step 2: Core CRUD Methods (15 minutes)
1. Implement `create()`
2. Implement `get_by_id()`
3. Implement `get_all()`
4. Implement `update()`
5. Implement `soft_delete()` (wrapper around update)
6. Implement `restore()` (wrapper around update)

### Step 3: Query Methods (10 minutes)
1. Implement `search_by_name()` with ILIKE
2. Implement `count_all()`

### Step 4: Relationship Helper (5 minutes)
1. Implement `get_with_events()` with selectinload()

### Step 5: Verification (5 minutes)
1. Run import test: `python3 -c "from backend.app.domain.spirit_operations import SpiritOperations"`
2. Check no syntax errors
3. Verify type hints with mypy (if configured)

---

## Expected File Size

**Estimate:** ~150-180 lines
- Shorter than EventOperations (283 lines)
- Simpler validation logic
- No complex dedupe key generation

**Breakdown:**
- Module docstring + imports: ~20 lines
- Class definition + docstring: ~5 lines
- create(): ~15 lines
- get_by_id(): ~10 lines
- get_all(): ~15 lines
- update(): ~15 lines
- soft_delete() + restore(): ~10 lines each (wrappers)
- search_by_name(): ~15 lines
- count_all(): ~10 lines
- get_with_events(): ~15 lines

---

## Future Enhancements (Not in MVP)

### Phase 2 Additions

1. **Metadata Validation:**
   - Schema validation for `meta` JSONB field
   - Enforce required keys if needed

2. **Bulk Operations:**
   - `create_many()` for batch spirit creation
   - `update_many()` for batch updates

3. **Statistics:**
   - `get_event_count(spirit_id)` - Count events per spirit
   - `get_most_active()` - Spirits with most events

4. **Advanced Search:**
   - Full-text search on description
   - Metadata-based filtering

5. **Cascade Operations:**
   - `delete_with_events()` - Soft delete spirit + all events
   - Requires careful consideration of provenance

---

## Success Criteria

✅ **Completeness:**
- All 9 methods implemented
- Full type hints
- Proper error handling

✅ **Consistency:**
- Matches EventOperations pattern
- Same docstring style
- Same static method approach

✅ **Correctness:**
- Imports successfully
- No syntax errors
- Follows soft delete semantics

✅ **Documentation:**
- Condensed docstrings on all methods
- Module-level documentation
- Inline comments where needed

---

## Next Steps After Implementation

1. **API Routes:** Create `backend/app/api/routes/spirits.py`
   - POST /api/spirits - Create spirit
   - GET /api/spirits - List spirits (paginated)
   - GET /api/spirits/search?name=query - Search by name
   - GET /api/spirits/{spirit_id} - Get by ID
   - PATCH /api/spirits/{spirit_id} - Update spirit
   - DELETE /api/spirits/{spirit_id} - Soft delete

2. **Tests:** Write unit tests for SpiritOperations

3. **Integration:** Test full flow: Create Spirit → Create Event → List Events for Spirit

4. **Documentation:** Update changelog with v0.0.8 entry

---

## Estimated Effort

| Task | Time |
|------|------|
| File setup + imports | 5 min |
| Core CRUD (6 methods) | 15 min |
| Query methods (2 methods) | 10 min |
| Relationship helper (1 method) | 5 min |
| Testing imports | 5 min |
| **Total** | **40 min** |

---

**Status:** Ready to implement
