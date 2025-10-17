"""Events model - atomic units of experience in Elephantasm."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel

from backend.app.models.database.mixins.timestamp import TimestampMixin
from backend.app.models.database.spirits import Spirit


class EventType(str, Enum):
    """Event types for alpha release (messages only)."""
    MESSAGE_IN = "message.in"
    MESSAGE_OUT = "message.out"
    # Future: TOOL_CALL, TOOL_RESULT, FILE_INGESTED, etc.


class EventBase(SQLModel):
    """Shared fields for Event model."""
    spirit_id: UUID = Field(foreign_key="spirits.id", index=True, description="Owner spirit ID")
    event_type: str = Field(max_length=100, index=True)
    meta_summary: str | None = Field(default=None, description="Brief Cortex-generated summary", nullable=True)
    content: str = Field(description="Human-readable message content")
    occurred_at: datetime | None = Field(default=None, description="When event occurred (source time)", nullable=True)
    session_id: str | None = Field(default=None, max_length=255, index=True, nullable=True)
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    source_uri: str | None = Field(default=None, nullable=True)
    dedupe_key: str | None = Field(default=None, max_length=255, nullable=True)
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0, nullable=True)


class Event(EventBase, TimestampMixin, table=True):
    """Event entity - atomic unit of experience."""
    __tablename__ = "events"

    id: UUID = Field(default=None, primary_key=True, sa_column_kwargs={"server_default": text("gen_random_uuid()")})
    is_deleted: bool = Field(default=False)

    # Relationship to Spirit (will be fully wired after migrations)
    # spirit: Spirit = Relationship(back_populates="events")


class EventCreate(EventBase):
    """Data required to create an Event."""
    pass


class EventRead(EventBase):
    """Data returned when reading an Event."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class EventUpdate(SQLModel):
    """Fields that can be updated."""
    metadata: dict | None = None
    importance_score: float | None = None
    meta_summary: str | None = None
    is_deleted: bool | None = None
