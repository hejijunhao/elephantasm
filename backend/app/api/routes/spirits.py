"""Spirits API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.domain.spirit_operations import SpiritOperations
from backend.app.models.database.spirits import SpiritCreate, SpiritRead, SpiritUpdate


router = APIRouter(prefix="/spirits", tags=["spirits"])


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
