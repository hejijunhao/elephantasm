"""Events API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_db
from backend.app.domain.event_operations import EventOperations
from backend.app.models.database.events import EventCreate, EventRead, EventUpdate


router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "/",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create event"
)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Create new event. Validates Spirit FK, auto-defaults occurred_at, generates dedupe_key if needed."""
    try:
        event = await EventOperations.create(db, data)
        return EventRead.model_validate(event)
    except HTTPException:
        raise
    except IntegrityError as e:
        # Likely duplicate dedupe_key
        if "dedupe_key" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate event (dedupe_key conflict)"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error"
        )


@router.get(
    "/",
    response_model=List[EventRead],
    summary="List events"
)
async def list_events(
    spirit_id: UUID = Query(..., description="Spirit UUID to filter by"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    min_importance: Optional[float] = Query(None, ge=0.0, le=1.0, description="Min importance score"),
    include_deleted: bool = Query(False, description="Include soft-deleted events"),
    db: AsyncSession = Depends(get_db)
) -> List[EventRead]:
    """List events with filters. If session_id provided, returns chronological order (ASC), otherwise recent-first (DESC)."""
    if session_id:
        # Session-specific: chronological order
        events = await EventOperations.get_by_session(
            db, spirit_id, session_id, include_deleted
        )
    else:
        # General query: recent-first order
        events = await EventOperations.get_recent(
            db, spirit_id, limit, offset, event_type, session_id, min_importance, include_deleted
        )

    return [EventRead.model_validate(event) for event in events]


@router.get(
    "/{event_id}",
    response_model=EventRead,
    summary="Get event by ID"
)
async def get_event(
    event_id: UUID,
    include_deleted: bool = Query(False, description="Include soft-deleted events"),
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Get specific event by UUID."""
    event = await EventOperations.get_by_id(db, event_id, include_deleted)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    return EventRead.model_validate(event)


@router.patch(
    "/{event_id}",
    response_model=EventRead,
    summary="Update event"
)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db)
) -> EventRead:
    """Update event (partial). Can update meta_summary, importance_score, metadata, is_deleted."""
    try:
        event = await EventOperations.update(db, event_id, data)
        return EventRead.model_validate(event)
    except HTTPException:
        raise


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete event"
)
async def delete_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Soft delete event (mark as deleted, preserve for provenance)."""
    try:
        await EventOperations.soft_delete(db, event_id)
    except HTTPException:
        raise
