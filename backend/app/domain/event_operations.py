"""Domain operations for Events - business logic layer.

CRUD operations and business logic for Events.
No transaction management - routes handle commits/rollbacks.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
import hashlib

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from backend.app.models.database.events import Event, EventCreate, EventUpdate
from backend.app.models.database.spirits import Spirit


class EventOperations:
    """Event business logic. Static methods, async session-based, no commits."""

    @staticmethod
    async def create(
        session: AsyncSession,
        data: EventCreate
    ) -> Event:
        """Create event. Validates Spirit FK, auto-defaults occurred_at, generates dedupe_key if needed.

        Raises HTTPException 404 (Spirit not found) or 400 (validation failure).
        """
        # Validate spirit exists
        spirit = await session.get(Spirit, data.spirit_id)
        if not spirit or spirit.is_deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Spirit {data.spirit_id} not found or deleted"
            )

        # Default occurred_at to current time if not provided
        occurred_at = data.occurred_at if data.occurred_at else datetime.now(timezone.utc)

        # Auto-generate dedupe_key if source_uri provided but no dedupe_key
        dedupe_key = data.dedupe_key
        if data.source_uri and not dedupe_key:
            dedupe_key = EventOperations._generate_dedupe_key(
                spirit_id=data.spirit_id,
                event_type=data.event_type,
                content=data.content,
                occurred_at=occurred_at,
                source_uri=data.source_uri
            )

        # Validate importance_score if provided
        if data.importance_score is not None:
            if not (0.0 <= data.importance_score <= 1.0):
                raise HTTPException(
                    status_code=400,
                    detail="importance_score must be between 0.0 and 1.0"
                )

        # Create event instance
        event = Event(
            spirit_id=data.spirit_id,
            event_type=data.event_type,
            content=data.content,
            meta_summary=data.meta_summary,
            occurred_at=occurred_at,
            session_id=data.session_id,
            meta=data.meta or {},
            source_uri=data.source_uri,
            dedupe_key=dedupe_key,
            importance_score=data.importance_score
        )

        session.add(event)
        await session.flush()  # Get generated ID

        return event

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        event_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Event]:
        """Get event by ID. Returns None if not found or soft-deleted (unless include_deleted=True)."""
        event = await session.get(Event, event_id)

        if event is None:
            return None

        if not include_deleted and event.is_deleted:
            return None

        return event

    @staticmethod
    async def get_recent(
        session: AsyncSession,
        spirit_id: UUID,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        session_id: Optional[str] = None,
        min_importance: Optional[float] = None,
        include_deleted: bool = False
    ) -> List[Event]:
        """Get recent events for spirit with filters. Ordered DESC (newest first), paginated."""
        query = select(Event).where(Event.spirit_id == spirit_id)

        # Apply filters
        if not include_deleted:
            query = query.where(Event.is_deleted.is_(False))

        if event_type:
            query = query.where(Event.event_type == event_type)

        if session_id:
            query = query.where(Event.session_id == session_id)

        if min_importance is not None:
            query = query.where(Event.importance_score >= min_importance)

        # Order by occurred_at (most recent first), with created_at as tiebreaker
        query = (
            query
            .order_by(Event.occurred_at.desc(), Event.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_session(
        session: AsyncSession,
        spirit_id: UUID,
        session_id: str,
        include_deleted: bool = False
    ) -> List[Event]:
        """Get all events in session. Ordered ASC (chronological - oldest first)."""
        conditions = [
            Event.spirit_id == spirit_id,
            Event.session_id == session_id
        ]

        if not include_deleted:
            conditions.append(Event.is_deleted.is_(False))

        result = await session.execute(
            select(Event)
            .where(and_(*conditions))
            .order_by(Event.occurred_at.asc(), Event.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_by_spirit(
        session: AsyncSession,
        spirit_id: UUID,
        event_type: Optional[str] = None,
        session_id: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """Count events for spirit with optional filters."""
        query = select(func.count()).select_from(Event).where(Event.spirit_id == spirit_id)

        if not include_deleted:
            query = query.where(Event.is_deleted.is_(False))

        if event_type:
            query = query.where(Event.event_type == event_type)

        if session_id:
            query = query.where(Event.session_id == session_id)

        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def update(
        session: AsyncSession,
        event_id: UUID,
        data: EventUpdate
    ) -> Event:
        """Update event (partial). Validates importance_score range.

        Raises HTTPException 404 (not found) or 400 (validation failure).
        """
        event = await session.get(Event, event_id)
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"Event {event_id} not found"
            )

        # Validate importance_score if being updated
        if data.importance_score is not None:
            if not (0.0 <= data.importance_score <= 1.0):
                raise HTTPException(
                    status_code=400,
                    detail="importance_score must be between 0.0 and 1.0"
                )

        # Update only provided fields
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(event, key, value)

        session.add(event)
        await session.flush()
        return event

    @staticmethod
    async def update_meta_summary(
        session: AsyncSession,
        event_id: UUID,
        meta_summary: str
    ) -> Event:
        """Update meta_summary (typically populated by Cortex)."""
        return await EventOperations.update(
            session,
            event_id,
            EventUpdate(meta_summary=meta_summary)
        )

    @staticmethod
    async def update_importance(
        session: AsyncSession,
        event_id: UUID,
        importance_score: float
    ) -> Event:
        """Update importance_score (0.0-1.0 range validated)."""
        return await EventOperations.update(
            session,
            event_id,
            EventUpdate(importance_score=importance_score)
        )

    @staticmethod
    async def soft_delete(
        session: AsyncSession,
        event_id: UUID
    ) -> Event:
        """Soft delete event (mark as deleted, preserve for provenance)."""
        return await EventOperations.update(
            session,
            event_id,
            EventUpdate(is_deleted=True)
        )

    @staticmethod
    async def restore(
        session: AsyncSession,
        event_id: UUID
    ) -> Event:
        """Restore soft-deleted event."""
        return await EventOperations.update(
            session,
            event_id,
            EventUpdate(is_deleted=False)
        )

    @staticmethod
    def _generate_dedupe_key(
        spirit_id: UUID,
        event_type: str,
        content: str,
        occurred_at: datetime,
        source_uri: str
    ) -> str:
        """Generate dedupe key: SHA256 hash (first 100 chars of content) truncated to 32 chars."""
        parts = [
            str(spirit_id),
            event_type,
            content[:100],  # First 100 chars only
            occurred_at.isoformat(),
            source_uri
        ]
        hash_input = "|".join(parts).encode()
        return hashlib.sha256(hash_input).hexdigest()[:32]
