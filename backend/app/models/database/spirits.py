"""Spirits model - the owner entity in Elephantasm."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from backend.app.models.database.mixins.timestamp import TimestampMixin


class SpiritBase(SQLModel):
    """Shared fields for Spirit model."""
    name: str = Field(max_length=255, description="Human-readable spirit name")
    description: str | None = Field(default=None, nullable=True, description="Brief description")
    meta: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))


class Spirit(SpiritBase, TimestampMixin, table=True):
    """Spirit entity - represents an owner of memories."""
    __tablename__ = "spirits"

    id: UUID = Field(default=None, primary_key=True, sa_column_kwargs={"server_default": text("gen_random_uuid()")})
    is_deleted: bool = Field(default=False)

    # Relationships (will be populated as we add models)
    # events: list["Event"] = Relationship(back_populates="spirit")
    # memories: list["Memory"] = Relationship(back_populates="spirit")


class SpiritCreate(SpiritBase):
    """Data required to create a Spirit."""
    pass


class SpiritRead(SpiritBase):
    """Data returned when reading a Spirit."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class SpiritUpdate(SQLModel):
    """Fields that can be updated."""
    name: str | None = None
    description: str | None = None
    meta: dict[str, Any] | None = None
    is_deleted: bool | None = None
