# Spirit API Routes Implementation Plan

**Version:** 1.0
**Date:** 2025-10-17
**Status:** Planning
**Estimated Time:** 30-45 minutes

---

## Overview

Implement Spirit REST API endpoints following the established architectural patterns from Events API routes. This creates the HTTP adapter layer connecting SpiritOperations domain logic to the FastAPI application.

**Goal:** Provide complete CRUD REST API for Spirit management with proper validation, error handling, and OpenAPI documentation.

---

## Reference Architecture

### Pattern to Follow: Events API Routes

**Key Characteristics:**
- Thin route handlers (pure HTTP adapters)
- Dependency injection via `Depends(get_db)`
- DTOs for request/response serialization
- HTTP status code semantics (201, 200, 204, 404, 409)
- OpenAPI metadata (summary, descriptions)
- Type hints on all parameters
- Error propagation from domain layer

**File Location:**
- Reference: `backend/app/api/routes/events.py`
- New File: `backend/app/api/routes/spirits.py`

---

## SpiritOperations Method Mapping

### Available Domain Methods (9 total)

| Domain Method | API Endpoint | HTTP Method | Status Code |
|---------------|--------------|-------------|-------------|
| `create()` | `/api/spirits` | POST | 201 Created |
| `get_by_id()` | `/api/spirits/{spirit_id}` | GET | 200 OK |
| `get_all()` | `/api/spirits` | GET | 200 OK |
| `search_by_name()` | `/api/spirits/search` | GET | 200 OK |
| `get_with_events()` | `/api/spirits/{spirit_id}/with-events` | GET | 200 OK |
| `update()` | `/api/spirits/{spirit_id}` | PATCH | 200 OK |
| `soft_delete()` | `/api/spirits/{spirit_id}` | DELETE | 204 No Content |
| `restore()` | `/api/spirits/{spirit_id}/restore` | POST | 200 OK |
| `count_all()` | *(not exposed as endpoint)* | - | - |

**Note:** `count_all()` is reserved for future pagination metadata. Not needed for MVP.

---

## Endpoint Specifications

### 1. POST `/api/spirits` - Create Spirit

**Purpose:** Create new spirit with name, optional description, and metadata.

**Request:**
```python
{
    "name": "alice-assistant",
    "description": "Personal productivity assistant",  # optional
    "meta": {"role": "assistant", "version": "1.0"}   # optional
}
```

**Response:** `201 Created`
```python
{
    "id": "uuid",
    "name": "alice-assistant",
    "description": "Personal productivity assistant",
    "meta": {"role": "assistant", "version": "1.0"},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:00:00Z",
    "is_deleted": false
}
```

**Error Handling:**
- `400 Bad Request` - Validation errors (Pydantic)
- `422 Unprocessable Entity` - Invalid JSON

**Implementation:**
```python
@router.post(
    "/",
    response_model=SpiritRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create spirit"
)
async def create_spirit(
    data: SpiritCreate,
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    """Create new spirit. Name required, description and meta optional."""
    spirit = await SpiritOperations.create(db, data)
    return SpiritRead.model_validate(spirit)
```

**Notes:**
- No FK validation needed (root entity)
- Simpler than Events create (no dedupe_key collision handling)
- No IntegrityError catch needed (no unique constraints beyond PK)

---

### 2. GET `/api/spirits` - List Spirits

**Purpose:** List all spirits with pagination, ordered newest first.

**Query Parameters:**
- `limit: int` (default: 50, range: 1-200) - Max results to return
- `offset: int` (default: 0, min: 0) - Pagination offset
- `include_deleted: bool` (default: false) - Include soft-deleted spirits

**Response:** `200 OK`
```python
[
    {
        "id": "uuid",
        "name": "alice-assistant",
        "description": "...",
        "meta": {...},
        "created_at": "2025-10-17T12:00:00Z",
        "updated_at": "2025-10-17T12:00:00Z",
        "is_deleted": false
    },
    ...
]
```

**Implementation:**
```python
@router.get(
    "/",
    response_model=List[SpiritRead],
    summary="List spirits"
)
async def list_spirits(
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    include_deleted: bool = Query(False, description="Include soft-deleted spirits"),
    db: AsyncSession = Depends(get_db)
) -> List[SpiritRead]:
    """List all spirits, paginated, ordered DESC (newest first)."""
    spirits = await SpiritOperations.get_all(db, limit, offset, include_deleted)
    return [SpiritRead.model_validate(spirit) for spirit in spirits]
```

**Notes:**
- Simpler than Events list (no spirit_id filter, no dual query routing)
- No session_id or event_type filtering
- Returns empty list if no spirits exist (not 404)

---

### 3. GET `/api/spirits/search` - Search by Name

**Purpose:** Case-insensitive partial name search, alphabetically ordered.

**Query Parameters:**
- `name: str` (required) - Name query (partial match)
- `limit: int` (default: 50, range: 1-200) - Max results to return

**Response:** `200 OK`
```python
[
    {
        "id": "uuid",
        "name": "alice-assistant",
        ...
    },
    {
        "id": "uuid",
        "name": "alice-bot",
        ...
    }
]
```

**Implementation:**
```python
@router.get(
    "/search",
    response_model=List[SpiritRead],
    summary="Search spirits by name"
)
async def search_spirits(
    name: str = Query(..., description="Name query (partial match, case-insensitive)", min_length=1),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    db: AsyncSession = Depends(get_db)
) -> List[SpiritRead]:
    """Search spirits by name using partial matching (ILIKE). Ordered alphabetically."""
    spirits = await SpiritOperations.search_by_name(db, name, limit)
    return [SpiritRead.model_validate(spirit) for spirit in spirits]
```

**Notes:**
- Must come BEFORE `/{spirit_id}` route (FastAPI route ordering)
- Returns empty list if no matches (not 404)
- Always excludes soft-deleted spirits (no include_deleted flag)
- Uses SQL ILIKE for case-insensitive matching

**Route Ordering Issue:**
```python
# CORRECT ORDER:
@router.get("/search", ...)          # Must come first
@router.get("/{spirit_id}", ...)     # Must come after

# WRONG ORDER (will break):
@router.get("/{spirit_id}", ...)     # Catches "/search" as spirit_id
@router.get("/search", ...)          # Never reached
```

---

### 4. GET `/api/spirits/{spirit_id}` - Get by ID

**Purpose:** Fetch single spirit by UUID.

**Path Parameters:**
- `spirit_id: UUID` (required) - Spirit UUID

**Query Parameters:**
- `include_deleted: bool` (default: false) - Include if soft-deleted

**Response:** `200 OK`
```python
{
    "id": "uuid",
    "name": "alice-assistant",
    "description": "...",
    "meta": {...},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:00:00Z",
    "is_deleted": false
}
```

**Error Handling:**
- `404 Not Found` - Spirit doesn't exist or soft-deleted (unless flag set)

**Implementation:**
```python
@router.get(
    "/{spirit_id}",
    response_model=SpiritRead,
    summary="Get spirit by ID"
)
async def get_spirit(
    spirit_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted spirits"),
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    """Get specific spirit by UUID."""
    spirit = await SpiritOperations.get_by_id(db, spirit_id, include_deleted)
    if not spirit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spirit {spirit_id} not found"
        )

    return SpiritRead.model_validate(spirit)
```

**Notes:**
- Exact same pattern as Events get_by_id
- Converts None → 404 HTTPException

---

### 5. GET `/api/spirits/{spirit_id}/with-events` - Get with Events

**Purpose:** Fetch spirit with eager-loaded events relationship. Demonstrates relationship loading.

**Path Parameters:**
- `spirit_id: UUID` (required) - Spirit UUID

**Query Parameters:**
- `include_deleted: bool` (default: false) - Include if soft-deleted

**Response:** `200 OK`
```python
{
    "id": "uuid",
    "name": "alice-assistant",
    "description": "...",
    "meta": {...},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:00:00Z",
    "is_deleted": false,
    "events": [  // eager-loaded relationship
        {
            "id": "event-uuid",
            "spirit_id": "uuid",
            "event_type": "message.in",
            "content": "...",
            ...
        },
        ...
    ]
}
```

**Error Handling:**
- `404 Not Found` - Spirit doesn't exist or soft-deleted

**Implementation:**
```python
@router.get(
    "/{spirit_id}/with-events",
    response_model=SpiritRead,
    summary="Get spirit with events"
)
async def get_spirit_with_events(
    spirit_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted spirits"),
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    """Get spirit with eager-loaded events relationship. Avoids N+1 queries."""
    spirit = await SpiritOperations.get_with_events(db, spirit_id, include_deleted)
    if not spirit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spirit {spirit_id} not found"
        )

    return SpiritRead.model_validate(spirit)
```

**Notes:**
- Demonstrates eager loading pattern for future models
- SpiritRead DTO must include events relationship field
- May need to check if SpiritRead currently includes events field

---

### 6. PATCH `/api/spirits/{spirit_id}` - Update Spirit

**Purpose:** Partial update of spirit (name, description, meta).

**Path Parameters:**
- `spirit_id: UUID` (required) - Spirit UUID

**Request:**
```python
{
    "name": "alice-v2",              # optional
    "description": "Updated desc",    # optional
    "meta": {"version": "2.0"}       # optional
}
```

**Response:** `200 OK`
```python
{
    "id": "uuid",
    "name": "alice-v2",
    "description": "Updated desc",
    "meta": {"version": "2.0"},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:05:00Z",  // updated
    "is_deleted": false
}
```

**Error Handling:**
- `404 Not Found` - Spirit doesn't exist
- `422 Unprocessable Entity` - Invalid field types

**Implementation:**
```python
@router.patch(
    "/{spirit_id}",
    response_model=SpiritRead,
    summary="Update spirit"
)
async def update_spirit(
    spirit_id: UUID,
    data: SpiritUpdate,
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    """Update spirit (partial). Can update name, description, meta, is_deleted."""
    try:
        spirit = await SpiritOperations.update(db, spirit_id, data)
        return SpiritRead.model_validate(spirit)
    except HTTPException:
        raise
```

**Notes:**
- Simpler than Events update (no importance_score validation)
- HTTPException from domain layer propagates directly
- `model_dump(exclude_unset=True)` handled in domain layer

---

### 7. DELETE `/api/spirits/{spirit_id}` - Soft Delete

**Purpose:** Mark spirit as deleted (preserve for provenance).

**Path Parameters:**
- `spirit_id: UUID` (required) - Spirit UUID

**Response:** `204 No Content` (empty body)

**Error Handling:**
- `404 Not Found` - Spirit doesn't exist

**Implementation:**
```python
@router.delete(
    "/{spirit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete spirit"
)
async def delete_spirit(
    spirit_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Soft delete spirit (mark as deleted, preserve for provenance)."""
    try:
        await SpiritOperations.soft_delete(db, spirit_id)
    except HTTPException:
        raise
```

**Notes:**
- Exact same pattern as Events delete
- No response body (204 No Content semantics)
- Does NOT cascade to events (future enhancement)

---

### 8. POST `/api/spirits/{spirit_id}/restore` - Restore Spirit

**Purpose:** Undelete soft-deleted spirit.

**Path Parameters:**
- `spirit_id: UUID` (required) - Spirit UUID

**Response:** `200 OK`
```python
{
    "id": "uuid",
    "name": "alice-assistant",
    "description": "...",
    "meta": {...},
    "created_at": "2025-10-17T12:00:00Z",
    "updated_at": "2025-10-17T12:10:00Z",
    "is_deleted": false  // changed from true
}
```

**Error Handling:**
- `404 Not Found` - Spirit doesn't exist

**Implementation:**
```python
@router.post(
    "/{spirit_id}/restore",
    response_model=SpiritRead,
    summary="Restore soft-deleted spirit"
)
async def restore_spirit(
    spirit_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    """Restore soft-deleted spirit (undelete)."""
    try:
        spirit = await SpiritOperations.restore(db, spirit_id)
        return SpiritRead.model_validate(spirit)
    except HTTPException:
        raise
```

**Notes:**
- POST (not PATCH) because it's a specific action, not a partial update
- Provides explicit restore capability (clearer than PATCH with is_deleted: false)
- Events API doesn't have this endpoint (could be added for consistency)

---

## File Structure

### Complete Route File

**File:** `backend/app/api/routes/spirits.py`

**Estimated Size:** ~180-200 lines

**Structure:**
```python
"""Spirits API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.domain.spirit_operations import SpiritOperations
from backend.app.models.database.spirits import SpiritCreate, SpiritRead, SpiritUpdate


router = APIRouter(prefix="/spirits", tags=["spirits"])


# POST /api/spirits - Create
@router.post("/", response_model=SpiritRead, status_code=status.HTTP_201_CREATED, summary="Create spirit")
async def create_spirit(...) -> SpiritRead:
    ...

# GET /api/spirits/search - Search (MUST come before /{spirit_id})
@router.get("/search", response_model=List[SpiritRead], summary="Search spirits by name")
async def search_spirits(...) -> List[SpiritRead]:
    ...

# GET /api/spirits - List
@router.get("/", response_model=List[SpiritRead], summary="List spirits")
async def list_spirits(...) -> List[SpiritRead]:
    ...

# GET /api/spirits/{spirit_id}/with-events - Get with events (MUST come before /{spirit_id})
@router.get("/{spirit_id}/with-events", response_model=SpiritRead, summary="Get spirit with events")
async def get_spirit_with_events(...) -> SpiritRead:
    ...

# GET /api/spirits/{spirit_id} - Get by ID
@router.get("/{spirit_id}", response_model=SpiritRead, summary="Get spirit by ID")
async def get_spirit(...) -> SpiritRead:
    ...

# PATCH /api/spirits/{spirit_id} - Update
@router.patch("/{spirit_id}", response_model=SpiritRead, summary="Update spirit")
async def update_spirit(...) -> SpiritRead:
    ...

# POST /api/spirits/{spirit_id}/restore - Restore
@router.post("/{spirit_id}/restore", response_model=SpiritRead, summary="Restore soft-deleted spirit")
async def restore_spirit(...) -> SpiritRead:
    ...

# DELETE /api/spirits/{spirit_id} - Soft delete
@router.delete("/{spirit_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete spirit")
async def delete_spirit(...) -> None:
    ...
```

**Total Endpoints:** 8 (vs Events: 5)

---

## Router Integration

### Update Router Aggregator

**File:** `backend/app/api/router.py`

**Current State:**
```python
from fastapi import APIRouter
from backend.app.api.routes import events

api_router = APIRouter()

api_router.include_router(events.router)
```

**Updated State:**
```python
from fastapi import APIRouter
from backend.app.api.routes import events, spirits

api_router = APIRouter()

api_router.include_router(events.router)
api_router.include_router(spirits.router)  # Add this line
```

**Result:**
- Events routes: `/api/events/*`
- Spirits routes: `/api/spirits/*`

---

## Key Design Decisions

### 1. Route Ordering Matters

**Critical:** Place specific routes BEFORE parameterized routes:

```python
# CORRECT:
@router.get("/search", ...)                      # Specific route first
@router.get("/{spirit_id}/with-events", ...)     # Specific route first
@router.get("/{spirit_id}", ...)                 # Parameterized route last

# WRONG (will break):
@router.get("/{spirit_id}", ...)                 # Catches everything
@router.get("/search", ...)                      # Never reached
@router.get("/{spirit_id}/with-events", ...)     # Never reached
```

### 2. Restore Endpoint (New Pattern)

**Decision:** Add `POST /{spirit_id}/restore` endpoint.

**Rationale:**
- Clearer intent than `PATCH` with `is_deleted: false`
- Provides explicit restore action
- Follows REST conventions (POST for actions)
- Not present in Events API (could be added for consistency)

**Alternative Considered:** Use `PATCH` with `SpiritUpdate(is_deleted=False)`
- **Pros:** Fewer endpoints, reuses update
- **Cons:** Less explicit, requires understanding is_deleted semantics

**Chosen:** Explicit restore endpoint for better API ergonomics.

### 3. Eager Loading Endpoint

**Decision:** Add `GET /{spirit_id}/with-events` endpoint.

**Rationale:**
- Demonstrates relationship loading pattern
- Avoids N+1 queries for client use case: "show spirit + all events"
- Optional optimization (clients can still use separate endpoints)
- Educational value for future models (Memories, Lessons)

**Alternative Considered:** Always eager-load in `GET /{spirit_id}`
- **Pros:** Simpler API (one endpoint)
- **Cons:** Performance penalty for clients who don't need events

**Chosen:** Separate endpoint for explicit control.

### 4. No Count Endpoint

**Decision:** Do NOT expose `count_all()` as endpoint (yet).

**Rationale:**
- Not needed for MVP (pagination metadata deferred)
- Can add later: `GET /api/spirits/count`
- Simpler API surface initially

### 5. No Bulk Operations

**Decision:** No batch create/update/delete endpoints.

**Rationale:**
- MVP focus: single-resource operations
- Can add later: `POST /api/spirits/batch`
- Keeps implementation simple

---

## HTTP Status Code Semantics

| Endpoint | Success | Error Conditions |
|----------|---------|------------------|
| POST / | 201 Created | 400 Bad Request (validation) |
| GET / | 200 OK | (empty list if none exist) |
| GET /search | 200 OK | (empty list if no matches) |
| GET /{id} | 200 OK | 404 Not Found |
| GET /{id}/with-events | 200 OK | 404 Not Found |
| PATCH /{id} | 200 OK | 404 Not Found, 422 Invalid |
| POST /{id}/restore | 200 OK | 404 Not Found |
| DELETE /{id} | 204 No Content | 404 Not Found |

**Consistency with Events API:**
- ✅ 201 for POST (resource creation)
- ✅ 200 for GET/PATCH (success with body)
- ✅ 204 for DELETE (success without body)
- ✅ 404 for missing resources
- ❌ No 409 Conflict (no dedupe_key collisions)

---

## Error Handling Patterns

### From Domain Layer
```python
try:
    result = await SpiritOperations.method(db, ...)
    return SpiritRead.model_validate(result)
except HTTPException:
    raise  # Propagate domain errors (404)
```

**Domain errors propagate directly:**
- `HTTPException(404)` from `update()`, `soft_delete()`, `restore()`

### Route-Level Checks
```python
spirit = await SpiritOperations.get_by_id(db, spirit_id, include_deleted)
if not spirit:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Spirit {spirit_id} not found"
    )
```

**Route-level 404 handling:**
- `get_by_id()` returns `None` → convert to 404
- Consistent error message format

### Validation Errors
```python
# Pydantic handles automatically:
data: SpiritCreate  # 400 Bad Request if invalid
```

**No custom validation needed:**
- Pydantic DTOs handle type validation
- FastAPI returns 422 Unprocessable Entity for invalid JSON
- No range validation (unlike Events importance_score)

---

## Implementation Checklist

### Step 1: Create Route File (5 minutes)
- [ ] Create `backend/app/api/routes/spirits.py`
- [ ] Add module docstring
- [ ] Add imports (fastapi, domain ops, DTOs)
- [ ] Create router instance: `router = APIRouter(prefix="/spirits", tags=["spirits"])`

### Step 2: Core CRUD Endpoints (15 minutes)
- [ ] Implement `create_spirit()` - POST /
- [ ] Implement `list_spirits()` - GET /
- [ ] Implement `get_spirit()` - GET /{spirit_id}
- [ ] Implement `update_spirit()` - PATCH /{spirit_id}
- [ ] Implement `delete_spirit()` - DELETE /{spirit_id}

### Step 3: Query & Relationship Endpoints (10 minutes)
- [ ] Implement `search_spirits()` - GET /search
- [ ] Implement `get_spirit_with_events()` - GET /{spirit_id}/with-events
- [ ] Implement `restore_spirit()` - POST /{spirit_id}/restore

### Step 4: Router Integration (5 minutes)
- [ ] Update `backend/app/api/router.py` to include spirits router
- [ ] Verify import chain: `from backend.app.api.routes import spirits`

### Step 5: Verification (5 minutes)
- [ ] Run import test: `python3 -c "from backend.app.api.routes.spirits import router"`
- [ ] Check router aggregation: `python3 -c "from backend.app.api.router import api_router"`
- [ ] Verify no syntax errors

---

## Testing Strategy

### Manual Testing (via Swagger UI)

1. **Start dev server:**
   ```bash
   cd backend && python main.py
   ```

2. **Access Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

3. **Test flow:**
   - POST /api/spirits - Create spirit "alice-assistant"
   - GET /api/spirits - Verify in list
   - GET /api/spirits/search?name=alice - Verify search
   - GET /api/spirits/{id} - Verify retrieval
   - POST /api/events - Create event for spirit
   - GET /api/spirits/{id}/with-events - Verify eager loading
   - PATCH /api/spirits/{id} - Update name to "alice-v2"
   - DELETE /api/spirits/{id} - Soft delete
   - GET /api/spirits/{id} - Verify 404
   - GET /api/spirits?include_deleted=true - Verify still in list
   - POST /api/spirits/{id}/restore - Undelete
   - GET /api/spirits/{id} - Verify restored

### Integration Testing Checklist

- [ ] Create spirit with minimal fields (name only)
- [ ] Create spirit with all fields (name, description, meta)
- [ ] List spirits with pagination (limit=10, offset=0)
- [ ] Search by partial name (case-insensitive)
- [ ] Get spirit by ID
- [ ] Get spirit with events (verify eager loading)
- [ ] Update spirit (partial fields)
- [ ] Soft delete spirit
- [ ] Verify soft-deleted spirit excluded from list
- [ ] Restore spirit
- [ ] Verify error handling (404 for non-existent spirit)

---

## Code Quality Guidelines

### Type Hints
```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def get_spirit(
    spirit_id: UUID,
    include_deleted: bool = Query(False, ...),
    db: AsyncSession = Depends(get_db)
) -> SpiritRead:
    ...
```

### Docstrings (Condensed)
```python
"""Get specific spirit by UUID."""
```

**Pattern:** Single-line summary describing endpoint purpose.

### OpenAPI Metadata
```python
@router.get(
    "/{spirit_id}",
    response_model=SpiritRead,
    summary="Get spirit by ID"  # Shows in Swagger UI
)
```

### Query Parameter Descriptions
```python
limit: int = Query(50, ge=1, le=200, description="Max results to return")
```

---

## Differences from Events API

| Aspect | Events API | Spirits API |
|--------|-----------|-------------|
| **Endpoints** | 5 | 8 (3 additional) |
| **Create Complexity** | dedupe_key collision handling | Simple (no unique constraints) |
| **List Complexity** | Dual query routing (session-based) | Single query (recent-first) |
| **Search** | None | Name search (ILIKE) |
| **Eager Loading** | None | `/with-events` endpoint |
| **Restore** | None | `/restore` endpoint |
| **Required Filters** | spirit_id required | None (list all) |

---

## Expected File Size

**Estimate:** ~180-200 lines

**Breakdown:**
- Module docstring + imports: ~15 lines
- Router instance: ~2 lines
- create_spirit(): ~20 lines
- list_spirits(): ~20 lines
- search_spirits(): ~20 lines
- get_spirit(): ~25 lines
- get_spirit_with_events(): ~25 lines
- update_spirit(): ~20 lines
- restore_spirit(): ~20 lines
- delete_spirit(): ~15 lines

**Comparison:**
- Events API: ~130 lines
- Spirits API: ~180 lines (40% more due to 3 additional endpoints)

---

## Success Criteria

✅ **Completeness:**
- All 8 endpoints implemented
- Full type hints and OpenAPI metadata
- Proper error handling (404 propagation)

✅ **Consistency:**
- Matches Events API patterns exactly
- Same docstring style
- Same dependency injection approach
- Same HTTP status code semantics

✅ **Correctness:**
- Imports successfully
- No syntax errors
- Router integration works
- Swagger UI accessible

✅ **Testing:**
- Manual testing via Swagger UI
- All endpoints respond correctly
- Error cases handled properly

---

## Next Steps After Implementation

1. **Test E2E Flow:**
   - Create Spirit → Create Event → Get Spirit with Events
   - Verify relationship loading works correctly

2. **Update Changelog:**
   - Add v0.0.8 completion entry (or v0.0.9 if domain ops was v0.0.8)

3. **Optional Enhancements (Phase 2):**
   - Add pagination metadata (count, next/prev links)
   - Add restore endpoint to Events API (consistency)
   - Add bulk operations (batch create/update)
   - Add metadata filtering

---

## Estimated Effort

| Task | Time |
|------|------|
| File setup + router instance | 5 min |
| Core CRUD endpoints (5) | 15 min |
| Query & relationship endpoints (3) | 10 min |
| Router integration | 5 min |
| Testing imports | 5 min |
| **Total** | **40 min** |

---

**Status:** Ready to implement
**Dependencies:** SpiritOperations domain layer (✅ complete)
**Blocker:** None
