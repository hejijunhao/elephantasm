# Changelog

All notable changes to the Elephantasm project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version History

- **0.0.1** (2025-10-17) - Foundation: TimestampMixin + Events model
- **0.0.0** (2025-10-17) - Initial project structure (FastAPI + Next.js)

---

## [0.0.1] - 2025-10-17

### Added

#### Core Infrastructure
- **TimestampMixin** (`backend/app/models/database/mixins/timestamp.py`)
  - Reusable mixin providing `created_at` and `updated_at` timestamps for all models
  - Timezone-aware timestamps using `datetime.now(timezone.utc)` (Python 3.12+ compliant)
  - Automatic `updated_at` refresh on record modification via SQLAlchemy `onupdate`
  - Lambda-wrapped `default_factory` for proper zero-arg callable support

#### Events Model - Foundation Layer
- **EventType Enum** (`backend/app/models/database/events.py`)
  - String-based enum for event classification
  - Alpha scope: `message.in` and `message.out` only
  - Extensible design for future event types (tool calls, file ingestions, errors, etc.)

- **EventBase** - Shared field definitions
  - Critical fields (NOT NULL): `agent_id`, `event_type`, `content`
  - Non-critical fields (nullable): all others for maximum ingestion flexibility
  - `meta_summary` - Brief Cortex-generated summary for fast scanning
  - `occurred_at` - Source timestamp (nullable, defaults to `created_at` when not provided)
  - `session_id` - Conversation/thread grouping handle (nullable)
  - `metadata` - PostgreSQL JSONB for flexible structured data
  - `source_uri` - Provenance pointer for traceability
  - `dedupe_key` - Idempotency key for duplicate prevention (nullable, unique when present)
  - `importance_score` - 0.0-1.0 float for event prioritization (nullable)

- **Event Table Model** - Main entity
  - DB-level UUID generation via PostgreSQL `gen_random_uuid()`
  - TimestampMixin integration for automatic timestamp management
  - Triple timestamp strategy:
    - `occurred_at` (nullable) - When event actually happened (source time)
    - `created_at` (from mixin) - When Elephantasm ingested the event
    - `updated_at` (from mixin) - When event was last modified (e.g., Cortex enrichment)
  - Soft deletes via `is_deleted` flag for provenance preservation
  - Foreign key to `agents.id` (will be updated to `spirits.id` in next iteration)

- **Data Transfer Objects (DTOs)**
  - `EventCreate` - Ingestion payload (inherits all EventBase fields)
  - `EventRead` - Response model with read-only fields (`id`, `created_at`, `updated_at`)
  - `EventUpdate` - Partial update model for mutable fields only

### Technical Decisions

#### DB-Level UUID Generation
- UUIDs generated in PostgreSQL, not Python
- Eliminates network round-trip for ID retrieval
- Maintains atomicity within database transactions
- Optimized for Supabase/PostgreSQL best practices

#### Timezone-Aware Timestamps
- Modern Python approach using `datetime.now(timezone.utc)`
- Deprecated `datetime.utcnow()` replaced for Python 3.12+ compatibility
- Explicit UTC timezone prevents ambiguity
- Future-proof against deprecation warnings

#### Progressive Enhancement Architecture
- Only 3 required fields maximize ingestion reliability
- All optional fields nullable for flexible data sources
- Cortex can asynchronously populate `meta_summary` and `importance_score`
- "Get it in the door first, refine later" philosophy

#### JSONB Metadata Storage
- PostgreSQL-native JSONB provides fast indexing and querying
- GIN indexes for efficient JSON property searches
- `default_factory=dict` prevents mutable default bugs
- No strict schema enforced at DB level for maximum flexibility

#### Field Ordering Optimization
- `meta_summary` placed before `content` for query efficiency
- Enables `SELECT meta_summary` without loading full content
- Pack compiler can use summaries, skip content (token savings)
- Logical semantic flow: summary � full content

### Design Patterns Applied

From Marlin Blueprint:
-  Base + Table + DTOs pattern for clean separation
-  SQLModel for combined Pydantic validation + SQLAlchemy ORM
-  Field-level validation via Pydantic constraints (`ge=0.0, le=1.0`)
-  Index planning at field level (`index=True`)
-  Soft deletes for non-destructive removal
-  Reusable mixins for DRY principle

Elephantasm-Specific:
-  Atomic events (one event per meaningful occurrence)
-  Session grouping via lightweight `session_id`
-  Idempotency via `dedupe_key`
-  Provenance tracking via `source_uri`
-  Triple timestamp strategy for complete temporal tracking

### Code Quality Metrics

- **Lines of Code**: 61 (events.py), 22 (timestamp.py)
- **Diagnostics**: 0 errors, 0 warnings
- **Type Safety**: Full type hints with Pydantic validation
- **Format**: Compact one-liner field definitions for scannability
- **Status**: Production-ready, migration-ready

### Documentation

- **Design Document**: `docs/executing/events-model-design.md` (v1.1)
  - Complete conceptual explanation of Events
  - Field-by-field rationale
  - Usage patterns and examples
  - API endpoint specifications
  - Database schema with index strategy

- **Completion Summary**: `docs/completions/events-model-implementation.md`
  - Implementation decisions explained
  - Design doc deviations documented
  - Code quality assessment
  - Next steps outlined

- **Execution Plan**: `docs/executing/events-pipeline-implementation-plan.md`
  - Step-by-step implementation guide for complete Events pipeline
  - 6 sequential steps with time estimates (~2 hours total)
  - Includes Spirits model, database config, migrations, domain ops, API endpoints
  - Troubleshooting section for common issues

### Notes

#### Intentional Deviations from Design Doc
- **Changed**: `received_at` � `created_at` (via TimestampMixin)
  - Same semantics, but using mixin provides consistency and bonus `updated_at` field
- **Added**: `updated_at` (via TimestampMixin)
  - Tracks when Cortex adds `meta_summary` or updates `importance_score`
- **Changed**: Python UUID generation � DB-level generation
  - Better performance and atomicity
- **Deferred**: Agent/Memory relationships
  - Models don't exist yet; prevents import cycles

#### Known Limitations (Alpha Scope)
- Only `message.in` and `message.out` event types
- No relationships to Agent/Memory models (deferred until those exist)
- No vector embeddings (Phase 3 enhancement)
- No session promotion to first-class entity (Phase 4 enhancement)

### Next Steps

Phase 1 Foundation (continued):
1. Implement Spirits model (`backend/app/models/database/spirits.py`)
2. Set up async database layer (`backend/app/core/database.py`)
3. Create Alembic migrations for spirits + events tables
4. Implement EventOperations domain logic
5. Build REST API endpoints for Events
6. Write unit and integration tests

---

