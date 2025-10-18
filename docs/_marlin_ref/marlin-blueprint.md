# Marlin Platform Architecture — Master Blueprint

This document is the definitive, end‑to‑end technical blueprint for Marlin. It maps the full repository, describes layers and responsibilities, and explains how data, auth, RLS, caching, and workflows connect. Follow this to replicate, reason about, and extend the platform.

Contents
- Overview & Principles
- Directory Map
- Backend Architecture
- Frontend Architecture
- Cross‑Cutting Concerns (Auth, RLS, Caching, Logging)
- End‑to‑End Flows
- Configuration, Deployment, Replication

---

## Overview & Principles

- Stack: FastAPI + SQLModel (PostgreSQL/Supabase), Next.js 15 App Router, Upstash Redis, MS Teams Bot Framework, OpenAI/Anthropic LLMs.
- Multi‑tenant, RLS‑first: All user‑visible DB operations run through a Postgres role that enforces RLS per‑request.
- Layering: Models (SQLModel) → Domain Operations (pure business logic, no commits) → API Routes (transactions, RLS) → Services/Workflows (orchestration, LLM, integrations).
- Dual DB connections: `SUPABASE_APP_URL` for user/RLS; `SUPABASE_URL`/service role for admin ops/migrations.
- Performance: Upstash Redis for API caching; eager‑loading + stable pagination; ETag on the frontend client; gzip; pgBouncer transaction pooling.
- Observability & Safety: Structured logging via Loguru; strict JWT verification; cache failures never break requests.

---

## Directory Map

- `backend/` – FastAPI app, business logic, workflows, migrations
  - `backend/main.py` – App entry, middleware, logging, route registration
  - `backend/api/` – Route modules grouped by resource
    - `backend/api/__init__.py` – `create_app()` + lifespan: connects/disconnects Redis
    - `backend/api/routes/` – REST by resource (offers, ships, users, trade_routes, ports, fixtures, positions, health, ms_teams)
  - `backend/core/` – Core infra: config, DB, auth, caching, logging
    - `config.py`, `database.py`, `admin_database.py`, `auth.py`, `auth_cache.py`, `upstash_cache.py`, `cache_config.py`, `logging_config.py`, `json_utils.py`, `supabase_client.py`, `connection_utils.py`
  - `backend/models/` – Data models & domain operations
    - `backend/models/database/` – SQLModel entities, Read/Create/Update DTOs, enums, mixins
    - `backend/models/domain_operations/` – Business logic (no commit/flush), validation
    - `backend/models/dto/` – Pure data DTOs for workflows
  - `backend/services/` – Reusable service helpers (e.g., trade route resolver)
  - `backend/workflows/` – LLM workflows for extraction/classification/persistence; registry
  - `backend/migrations/` – Alembic environment + versions (incl. RLS policy work)
  - `backend/tests/` – Infra/model/workflow tests
  - `backend/Dockerfile`, `backend/fly*.toml` – Containerization + Fly.io deploy

- `frontend/` – Next.js app, client and server code
  - `frontend/app/` – App Router routes; `(auth)` and main `(app)` segments
  - `frontend/api/services/` – Typed API client layer on top of `BaseAPIClient`
  - `frontend/lib/` – Supabase SSR/CSR clients, JWT verifier, utilities
  - `frontend/components/` – UI (shadcn) + feature components
  - `frontend/contexts/` – Auth/user contexts
  - `frontend/middleware.ts` – Edge auth verification + redirects

- `docs/` – Documentation (this file + domain‑specific docs)
- `.claude/` – Internal technical notes

---

## Backend Architecture

### App Composition & Lifecycle

- Factory: `backend/api/__init__.py: create_app()` sets FastAPI app, registers routers under `/api`, and wires lifespan for Redis cache connect/disconnect.
- Entry: `backend/main.py`
  - Logging: Loguru handlers (stdout + daily rotating JSON file), uvicorn intercept. Route list dumped on startup.
  - Middlewares: Proxy headers (`ProxyHeadersMiddleware`), GZip (`GZipMiddleware`), CORS (origins from env or defaults), configured early.
  - Health: Root and `/api` simple endpoints; DB connectivity test at startup.

### Configuration & Environment

- `backend/core/config.py` – Pydantic Settings. Key vars:
  - Supabase: `SUPABASE_API_URL`, `SUPABASE_URL`, `SUPABASE_APP_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
  - Redis (Upstash): `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
  - LLMs: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
  - MS Teams: `MS_BOT_*`
  - Logging flags: `VERBOSE_LOGGING`, `LOG_SQL`

### Database Layer

- RLS User Engine: `backend/core/database.py`
  - Uses `SUPABASE_APP_URL` (marlin_app role, BYPASSRLS disabled). Required.
  - Engine: `create_engine(..., poolclass=NullPool, pool_pre_ping=True)`; rely on pgBouncer transaction pooling.
  - Session factory: `SessionLocal` with `expire_on_commit=False`, `autoflush=False`, `autocommit=False`.
  - `get_db()` yields a session, commits on success, rollbacks on error; closes always.
  - RLS context: `set_rls_context(db_session, jwt_payload)` sets `app.*` session vars; `get_db_with_rls` (in `auth.py`) depends on token → sets context.
  - Transaction helper: `rls_transaction(db, ctx)` wraps `db.begin()` and configures context for the transaction duration.

- Admin Engine: `backend/core/admin_database.py`
  - Uses `DATABASE_URL_SERVICE_ROLE` or fallback `SUPABASE_URL` for BYPASSRLS ops (maintenance/migrations only). Pooling via `QueuePool`.
  - Context: `get_admin_db()` for one‑off admin blocks; helpers for stats/cleanup/bulk updates. Not used in user‑facing APIs.

- Connection Utilities: `backend/core/connection_utils.py`
  - Patterns for “acquire, do, release fast” (sync/async) with admin engine; batch transaction helper; decorators to measure connection hold time. Intended for background/admin workflows, not request paths.

### Models (SQLModel)

- Location: `backend/models/database/`
  - Pattern per entity: `EntityBase` (shared fields) + `Entity(table=True)` with PK and relationships + `EntityCreate`/`EntityRead`/`EntityUpdate` DTOs.
  - Multi‑tenancy: most domain rows carry `enterprise_id` and `created_by_user_id` (UUID) where applicable.
  - Soft‑delete: `is_deleted`, `deleted_at` across entities.
  - Timestamps: `TimestampMixin` sets `created_at`, `updated_at` via server defaults.
  - Example: `offers.py`
    - Enums: `RateType`, `OfferType`, `OfferClassificationEnum`, `OfferDeliveryBasisEnum`.
    - `Offer` with FKs to cargo/ship positions, trade route, teams message; relationships with joined/selected loading in ops.
    - DTOs: `OfferCreate`, `OfferRead`, `OfferUpdate` mirror the API payloads.
  - Other key entities: `users`, `enterprises`, `ships`, `ship_positions`, `ports`, `trade_routes`, `fixtures`, `tonnage_sections`, `teams_messages`.

- DTOs for Workflows: `backend/models/dto/workflow_data.py` – pure dataclasses for ships, ports, positions, offers, fixtures used to pass data across LLM/IO boundaries without holding DB sessions.

- Migrations: `backend/migrations/` – Alembic env + versioned scripts. Includes policies and RLS hardening (e.g., `007_rls_complete_all_tables.py`, `ab9214345e00_update_rls_policies_for_dual_path_*.py`, etc.).

### AuthN + AuthZ + RLS

- `backend/core/auth.py`
  - HTTP Bearer; Supabase JWKS fetched via `SUPABASE_API_URL` (`get_jwks` with caching). Strict ES256 verification.
  - JWT payload cache: `backend/core/auth_cache.py` (5‑min TTL) to avoid repeat verifications.
  - `get_current_user`: minimal RLS bootstrap sets `app.auth_uid`, then loads active `User` via RLS bootstrap policy.
  - Enterprise context: `get_current_membership` returns simplified membership object (user_id, enterprise_id, role). Type aliases: `CurrentUser`, `CurrentMembership`.
  - Role guards: `require_member/admin/owner` and factory `require_role`.
  - RLS session: `get_db_with_rls` applies `set_rls_context` for route handlers → type alias `RLSSession` for dependency injection.

### API Routes (Resource Layer)

- Location: `backend/api/routes/` – routers import:
  - Auth/Context: `CurrentUser`, `CurrentMembership`, `RLSSession`
  - DB: `get_db` (health), or `RLSSession` (RLS‑aware ops)
  - Domain ops and models per resource
  - Cache: `core/upstash_cache.py` + TTL via `core/cache_config.py`
  - JSON serialization: `core/json_utils.JSONResponse` (proper date/datetime encoding)

- Conventions
  - Mutations: set `enterprise_id` and `created_by_user_id` from auth context server‑side before constructing `*Create` DTOs.
  - Use domain operations to build/update entities (no commit); route calls `db.flush()` to persist within the RLS transaction; final commit handled by dependency (`get_db` or `RLSSession`).
  - Cache invalidation after writes using key‑pattern deletes.
  - Filtering & pagination parameters surfaced explicitly, with validation.

- Examples
  - Offers: `backend/api/routes/offers.py`
    - `POST /api/offers`, `/api/offers/offers|/bids` → build DTO, call `OfferOperations.create_*`, `db.flush()`, invalidate caches.
    - `GET /api/offers` → rich filters (trade routes, classification, tonnage sections, date guards), fieldsets (`minimal|default|full` eager loading strategies) and stable pagination (ID subquery) via `OfferOperations`.
  - Trade Routes: `backend/api/routes/trade_routes.py` – cached route lists, “last done fixtures” aggregation, manual assignment; reference data is global (no enterprise attribution).
  - Users: `backend/api/routes/users.py` – profile, list, update, role change (with RBAC), all via domain ops + RLS.
  - Ports/Ships/Cargo/Positions/Fixtures: similar pattern, with reference data caching for read‑heavy endpoints.
  - Health: `/api/health` (with DB SELECT 1) and `/api/healthz` (liveness‑only).
  - MS Teams: `/api/msteamsbot/messages` – BotFramework adapter integration.

### Domain Operations (Business Logic)

- Location: `backend/models/domain_operations/`
  - Contract: Pure business logic; must NOT call `commit()`, and only call `flush()` where explicitly needed inside ops that return generated IDs mid‑transaction. Route layer manages transaction and RLS.
  - Base: `base.py` defines the pattern, helpers for soft delete and existence validation.
  - Offers: `offer_operations.py` – filtering helpers, eager loading strategies, stable pagination, latest‑batch selection logic, joins to ship/position/trade route.
  - Users, Ports, Fixtures, Ships, Positions: corresponding `*_operations.py` implement validate/update/list semantics.

### Services

- Location: `backend/services/`
  - `trade_routes/trade_route_resolver.py` – expand umbrella groups and resolve market/subregion filters into concrete TradeRoute IDs. Used by offers listing and other features.
  - Additional service helpers live beside domain‑specific code (e.g., section headers/fixture sections).

### Workflows (LLM + Orchestration)

- Location: `backend/workflows/`
  - Registry: `workflows/registry.py` maps canonical names to lazy‑loaded orchestrators (avoid import cycles).
  - Offer Creation: `offer_creation/orchestrator.py` – parse inputs → extract offers (OpenAI/Anthropic) → standardize voyage → normalize → resolve ship/position → persist → optional trade route classification. Uses a `db_session_factory` (admin engine) for non‑request workflows.
  - Fixture, Ex‑Our‑CP, Ship, Position, Port creation workflows mirror the pattern, with reusable nodes under `workflows/.../nodes` and helpers in `workflows/utils/*`.
  - Adapters: `workflows/adapters/llm_adapter.py` + provider implementations for OpenAI/Anthropic.

### MS Teams Integration

- Route: `backend/api/routes/ms_teams.py` – BotFramework adapter; settings from `MS_BOT_APP_ID`, `MS_BOT_CLIENT_SECRET`, `MS_BOT_TENANT_ID`; logs channel, validates content type; forwards `Activity` to `MarlinBot` (`workflows/teams_workflow.py`).
- TeamsMessage model + operations: `models/database/teams_messages.py`, `models/domain_operations/team_msg_operations.py` – used to link created records back to Teams.
- Deploy note: `MS_BOT_MESSAGING_ENDPOINT` must match Azure bot channel config (production/staging URLs in `fly*.toml`).

### Caching & TTLs

- Upstash Redis: `backend/core/upstash_cache.py`
  - REST client via `upstash_redis`; safe by default (errors increment stats and return misses).
  - Key convention: `cache.make_key(prefix, enterprise_id?, user_id?, **params)` → `prefix:enterprise:u123:hash`.
  - Helpers: `get`, `set` (TTL), `get_many`, `set_many`, `delete_key`, `delete_pattern`.
- TTL Policy: `backend/core/cache_config.py` – declarative TTLs per data type (`offers`, `last_done`, `ports`, `trade_routes`, …).
- Route Integration: trade routes, offers, fixtures, ports use cache for hot paths; writes invalidate relevant prefixes.

### Logging & Observability

- Verbose logger: `backend/core/logging_config.py` – category helpers (`api`, `sql`, `cache`, `auth`, `workflow`, `performance`), colored console, JSON file logs with rotation/retention. Controlled by `VERBOSE_LOGGING` and `LOG_SQL`.
- Startup/route inventory: `backend/main.py` logs all registered paths; DB ping and table creation check early.

---

## Frontend Architecture

### App Structure

- App Router: `frontend/app/(auth)` (login/forgot/reset) and `frontend/app/(app)` (offers, fixtures, ships, clients, ports, tonnage, ex‑our‑cp, message‑log, organization, mapper, changelog). Uses server and client components as needed.
- Components: `frontend/components/ui/*` (shadcn), feature components in subfolders; minimal shared state via React hooks/contexts.
- Contexts: `frontend/contexts/auth-context.tsx`, `frontend/contexts/user-context.tsx` to provide user and org info to trees.

### Auth (Supabase)

- CSR client: `frontend/lib/supabase/client.ts`
- SSR client: `frontend/lib/supabase/server.ts`
- Edge Middleware: `frontend/middleware.ts`
  - Skips static/API routes; constructs SSR Supabase client; gets session; verifies user (`auth.getUser()`); caches verified users client‑side (`frontend/lib/auth-cache.ts`); redirects unauthenticated to `/login` with `redirect` param; refreshes tokens if expiring; sets `x-user-verified`, `x-user-id`, `x-user-email`, and optional `x-enterprise-id` headers.
- Local JWT verification (optional): `frontend/lib/jwt-verifier.ts` using JOSE and project‑specific JWKS URL.

### API Client Layer

- Base client: `frontend/api/services/base-client.ts`
  - Builds base URL from `NEXT_PUBLIC_API_URL` (already includes `/api`). Enforces HTTPS on secure sites/production.
  - Auth headers: CSR via Supabase session; SSR via injected `serverAuthFn` (`frontend/api/services/base-client-server.ts#getServerAuthHeaders`). Adds `X-Enterprise-ID` from selected enterprise (localStorage or server context).
  - ETag client cache (GET only, client‑side): 304 handling and LRU eviction.
  - Unified `request/get/post/put/patch/delete` with structured `APIResponse` and robust 401 handling (CSR refresh).
- Resource clients: `offers-api.ts`, `ships-api.ts`, `ship-pos-api.ts`, `cargo-pos-api.ts`, `fixtures-api.ts`, `ports-api.ts`, `trade-routes-api.ts`, `teams-messages-api.ts`, `user-api.ts`, etc. Paths are relative (e.g., `/offers`, not `/api/offers`).
- Hooks: `frontend/hooks/use-api.ts` wraps any async API function, injects enterprise id automatically, tracks loading/error/data.

### UI/Data Features

- Offers list: pagination + filtering in URL params; integrates “latest only” and sparse fieldsets (`fields=minimal|default|full`).
- Trade routes: cached lists and last‑done aggregation display; umbrella filtering.
- Profile/org: `/profile` uses `/api/users/me` to fetch unified profile + organization.

---

## Cross‑Cutting Concerns

### Authentication & RLS Bridge

1) Frontend gets Supabase session (access token). Middleware keeps it fresh.
2) API requests pass `Authorization: Bearer <token>` and `X-Enterprise-ID` (optional).
3) Backend `core/auth.py`: verify JWT via JWKS; cache payload; `get_current_user` does RLS bootstrap (`app.auth_uid`), returns `User` with `enterprise_id`/`role`.
4) `get_db_with_rls` sets full RLS context (auth_uid→user_id, enterprise_id, role) via `set_rls_context` so all queries are filtered by policies.
5) Route uses `RLSSession` + domain ops; final commit happens via dependency lifecycle; no accidental context loss.

### Caching

- Server cache (Upstash): configured per endpoint with TTL; keys include `enterprise_id` + normalized params; invalidation after writes.
- Client cache (ETag): Base client caches GET payloads per enterprise+URL; 304 short‑circuit; avoids React re‑renders by returning same object reference when 304.

### Performance

- DB: pgBouncer transaction pooling (use `:6543`), SQLAlchemy `NullPool`, eager loading tuned per fieldset, stable pagination via ID subqueries when joining.
- API: gzip, avoid logging noise, filter out routine health/polling, Upstash REST for low‑latency glob.

### Logging

- Categories: `api/sql/cache/auth/workflow/performance`; verbose toggle; daily JSON logs in `backend/logs/`.

---

## End‑to‑End Flows

### Create Offer (shipowner) – POST `/api/offers/offers`

- Frontend: `OffersApiService.createOffer()` → Base client adds auth + `X-Enterprise-ID`.
- Backend route: `backend/api/routes/offers.py` `create_offer()`
  - `CurrentUser` + `CurrentMembership` + `RLSSession` injected.
  - Enrich DTO with `enterprise_id` and `created_by_user_id`; call `OfferOperations.create_offer(db, dto)`; `db.flush()`; Upstash invalidation for `offers:*` keys; commit handled by dependency.
- Result: Offer row attributed to enterprise/user; RLS ensures isolation.

### Fetch Proposals – GET `/api/offers`

- Frontend: `OffersApiService.getProposals(params)`; Base client may set `If-None-Match` if cached.
- Backend: parameters parsed (trade route, market/subregion, classification, tonnage sections, show_past_items, latest_only, fieldsets). RLS filters by enterprise.
  - Cache check: Upstash by enterprise + filter hash; if hit → return JSON with `X-Cache: HIT`.
  - Else: `OfferOperations.get_all_proposals(...)` uses eager loading strategy per `fields`, stable pagination (ID subquery) and ordering; cache set with TTL; return `X-Cache: MISS`.

### Teams Message → Offers (Workflow)

- MS Teams posts to `/api/msteamsbot/messages`; BotFramework adapter validates + forwards to `MarlinBot`.
- Workflow: `workflows/offer_creation/orchestrator.py` (via registry) uses LLM adapters to extract offers; resolves/creates ships and positions; persists offers via admin `db_session_factory`; links `teams_message_id`; optional trade route classification.

---

## Configuration, Deployment, Replication

### Required Environment (backend)

- Copy `backend/.env.example` → `.env`. Fill:
  - Supabase: `SUPABASE_URL` (postgres URL), `SUPABASE_APP_URL` (marlin_app role; transaction pooling, port 6543), `SUPABASE_API_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`.
  - MS Teams: `MS_BOT_APP_ID`, `MS_BOT_CLIENT_SECRET`, `MS_BOT_TENANT_ID` (for single‑tenant), `MS_BOT_MESSAGING_ENDPOINT`.
  - Upstash: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.
  - LLM keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
  - Flags: `VERBOSE_LOGGING`, `LOG_SQL`.

### Local Development

- Backend
  - `cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  - Ensure Supabase project exists, roles configured, and `SUPABASE_APP_URL` points to transaction pooling (:6543).
  - Migrations: `alembic upgrade head`
  - Run: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

- Frontend
  - `cd frontend && npm install`
  - Set env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL` (already contains `/api`), optional `NEXT_PUBLIC_DEBUG=true`
  - Run: `npm run dev` → http://localhost:3000

### Deployment

- Backend (Fly.io)
  - Config: `backend/fly.toml`, `backend/fly.staging.toml` define env + `MS_BOT_MESSAGING_ENDPOINT` for Azure.
  - Dockerfile copies `workflows/` and validates module import at build.

- Frontend (Vercel)
  - Edge middleware regions tuned to match backend regions; HTTPS forced in API client for secure hosts.

### Security Model Summary

- JWT: Strict ES256 verification against Supabase JWKS; payload caching (5 min) to reduce JWKS traffic.
- RLS: Session vars set via `set_config('app.*')` in `set_rls_context` then policies gate data per enterprise/user/role. Bootstrap allows reading `users` by `auth_uid` only to establish context.
- Dual connections: Never use admin/service role in user‑facing code. Admin utilities reserved for migrations/maintenance/workflows.
- CORS: Allowed origins configured; GZip enabled; proxy headers accepted.

### Troubleshooting & Notes

- Double `/api` risk: Avoid in frontend; `NEXT_PUBLIC_API_URL` already includes `/api`; service endpoints should be relative (`/offers`, `/users/me`, …).
- pgBouncer: Use transaction pooling port 6543; SQLAlchemy pool disabled (`NullPool`).
- Cache safety: Upstash failures never break responses; cache keys always enterprise‑scoped.
- Domain Ops: Keep commits out of ops; handle in route dependency to preserve RLS context for entire request.

---

## Quick File Index (reference)

- App
  - backend/api/__init__.py:1 – `create_app()` + lifespan
  - backend/main.py:1 – logging, middleware, route registration
- Core
  - backend/core/config.py:1 – env settings
  - backend/core/database.py:1 – RLS engine, `get_db`, `set_rls_context`, `rls_transaction`
  - backend/core/admin_database.py:1 – service role engine/context
  - backend/core/auth.py:1 – JWKS verify, `CurrentUser`, `CurrentMembership`, `RLSSession`
  - backend/core/upstash_cache.py:1 – Upstash client
  - backend/core/cache_config.py:1 – TTLs
  - backend/core/logging_config.py:1 – Verbose logger
- Models
  - backend/models/database/offers.py:1 – Offer model + DTOs
  - backend/models/database/users.py:1 – User + roles, enterprise
  - backend/models/database/trade_routes.py:1 – TradeRoute
  - backend/models/database/ships.py:1 – Ship
  - backend/models/database/ports.py:1 – Port
  - backend/models/domain_operations/offer_operations.py:1 – Offer ops
  - backend/models/domain_operations/user_operations.py:1 – User ops
- Services & Workflows
  - backend/services/trade_routes/trade_route_resolver.py:1 – Umbrella resolver
  - backend/workflows/registry.py:1 – Workflow registry
  - backend/workflows/offer_creation/orchestrator.py:1 – Offer creation pipeline
- Frontend
  - frontend/api/services/base-client.ts:1 – API client (auth, HTTPS, ETag)
  - frontend/api/services/offers-api.ts:1 – Offers service
  - frontend/middleware.ts:1 – Edge auth middleware
  - frontend/lib/supabase/{client,server}.ts – Supabase clients
  - frontend/lib/jwt-verifier.ts:1 – Local JOSE verification

---
