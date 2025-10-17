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
    async def create(
        session: AsyncSession,
        data: SpiritCreate
    ) -> Spirit:
        """Create spirit. No FK validation needed (root entity)."""
        # Create spirit instance
        spirit = Spirit(
            name=data.name,
            description=data.description,
            meta=data.meta or {}
        )

        session.add(spirit)
        await session.flush()  # Get generated ID

        return spirit

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        spirit_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Spirit]:
        """Get spirit by ID. Returns None if not found or soft-deleted (unless include_deleted=True)."""
        spirit = await session.get(Spirit, spirit_id)

        if spirit is None:
            return None

        if not include_deleted and spirit.is_deleted:
            return None

        return spirit

    @staticmethod
    async def get_all(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Spirit]:
        """Get all spirits (paginated). Ordered DESC (newest first)."""
        query = select(Spirit)

        # Filter out soft-deleted
        if not include_deleted:
            query = query.where(Spirit.is_deleted.is_(False))

        # Order by created_at (newest first)
        query = (
            query
            .order_by(Spirit.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        session: AsyncSession,
        spirit_id: UUID,
        data: SpiritUpdate
    ) -> Spirit:
        """Update spirit (partial). Raises HTTPException 404 (not found)."""
        spirit = await session.get(Spirit, spirit_id)
        if not spirit:
            raise HTTPException(
                status_code=404,
                detail=f"Spirit {spirit_id} not found"
            )

        # Update only provided fields
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(spirit, key, value)

        session.add(spirit)
        await session.flush()
        return spirit

    @staticmethod
    async def soft_delete(
        session: AsyncSession,
        spirit_id: UUID
    ) -> Spirit:
        """Soft delete spirit (mark as deleted, preserve for provenance)."""
        return await SpiritOperations.update(
            session,
            spirit_id,
            SpiritUpdate(is_deleted=True)
        )

    @staticmethod
    async def restore(
        session: AsyncSession,
        spirit_id: UUID
    ) -> Spirit:
        """Restore soft-deleted spirit."""
        return await SpiritOperations.update(
            session,
            spirit_id,
            SpiritUpdate(is_deleted=False)
        )

    @staticmethod
    async def search_by_name(
        session: AsyncSession,
        name_query: str,
        limit: int = 50
    ) -> List[Spirit]:
        """Search spirits by name (partial match, case-insensitive). Excludes soft-deleted."""
        query = select(Spirit).where(
            and_(
                Spirit.name.ilike(f"%{name_query}%"),
                Spirit.is_deleted.is_(False)
            )
        ).order_by(Spirit.name.asc()).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_all(
        session: AsyncSession,
        include_deleted: bool = False
    ) -> int:
        """Count total spirits. Useful for pagination metadata."""
        query = select(func.count()).select_from(Spirit)

        if not include_deleted:
            query = query.where(Spirit.is_deleted.is_(False))

        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_with_events(
        session: AsyncSession,
        spirit_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Spirit]:
        """Get spirit with eager-loaded events relationship. Avoids N+1 query problem."""
        query = (
            select(Spirit)
            .where(Spirit.id == spirit_id)
            .options(selectinload(Spirit.events))
        )

        if not include_deleted:
            query = query.where(Spirit.is_deleted.is_(False))

        result = await session.execute(query)
        return result.scalar_one_or_none()
