# Async Driver + pgBouncer Compatibility Issue

**Status:** Issue Identified - Resolution Pending
**Date:** 2025-10-17
**Component:** Database Layer
**Severity:** Blocking (prevents migrations from running)

---

## Problem Statement

When attempting to run Alembic migrations against Supabase's transaction pooler (port 6543), we encountered the following error:

```
asyncpg.exceptions.DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_3__" already exists
HINT: pgbouncer with pool_mode set to "transaction" or "statement" does not support prepared statements properly.
```

**Root Cause:** `asyncpg` (our async PostgreSQL driver) uses prepared statements by default for performance optimization. Supabase's pgBouncer in **transaction pooling mode** does not support prepared statements because each transaction may be routed to a different backend PostgreSQL server.

---

## Technical Background

### What Are Prepared Statements?

Prepared statements are a database optimization where the query is parsed and compiled once, then reused multiple times with different parameters:

```python
# asyncpg automatically does this:
# 1. PREPARE stmt AS SELECT * FROM users WHERE id = $1
# 2. EXECUTE stmt(123)
# 3. EXECUTE stmt(456)  # Reuses prepared statement
```

### Why pgBouncer Transaction Pooling Breaks This

**Transaction Pooling Mode:**
- Connection is assigned to a client only for the duration of a transaction
- After `COMMIT`/`ROLLBACK`, connection returns to pool and may go to another client
- Prepared statements are **per-connection**, not per-transaction
- Next transaction on same connection may belong to different client but see old prepared statements
- Result: "prepared statement already exists" errors

**Session Pooling Mode (port 5432):**
- Connection stays with client for entire session
- Prepared statements work fine
- But: fewer available connections, less efficient for API workloads

---

## Why This Matters for Elephantasm

**Our Current Setup:**
- Driver: `asyncpg==0.30.0`
- Database: Supabase PostgreSQL
- Pooler: pgBouncer Transaction Mode (port 6543)
- DATABASE_URL: `postgresql+asyncpg://...@db.xxx.supabase.co:6543/postgres`

**Impact:**
- ❌ Cannot run Alembic migrations
- ❌ Will hit same issue in production API requests
- ❌ Workarounds (`statement_cache_size=0`) are unreliable

---

## Why We Chose Async in the First Place

**Comparison with Previous Application:**

The user's previous application (`admin_database.py` reference) used:
- **Synchronous SQLAlchemy** (`create_engine`)
- **psycopg2** driver (implicit)
- **QueuePool** (local connection pooling)
- **No pgBouncer** (direct PostgreSQL connection or different pooling strategy)

**Why Elephantasm Needs Async:**
1. **Concurrency:** FastAPI async routes can handle multiple requests without blocking threads
2. **Scalability:** Non-blocking I/O for database operations improves throughput
3. **Modern Architecture:** Aligns with async/await patterns throughout the codebase
4. **Resource Efficiency:** Better CPU utilization during I/O-bound operations

---

## Options Evaluated

### Option 1: Switch to psycopg3 (async) ✅ **RECOMMENDED**

**Overview:**
Use `psycopg` (version 3) with async support instead of `asyncpg`.

**Implementation:**
```python
# requirements.txt
psycopg[binary]==3.2.3  # Instead of asyncpg==0.30.0

# .env
DATABASE_URL="postgresql+psycopg://postgres:...@db.xxx.supabase.co:6543/postgres"

# database.py (simplified)
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
)
# No special connect_args needed!
```

**Pros:**
- ✅ Fully async (non-blocking like asyncpg)
- ✅ **Works perfectly with pgBouncer transaction pooling**
- ✅ Modern, actively maintained (successor to psycopg2)
- ✅ Officially recommended by Supabase for transaction pooling
- ✅ No prepared statement caching by default
- ✅ Drop-in replacement for asyncpg in SQLAlchemy 2.0
- ✅ Clean implementation (no workarounds needed)

**Cons:**
- Slightly slower than asyncpg in micro-benchmarks (~10-15%)
- But: negligible for real-world API workloads with network latency

**Verdict:** This is the industry-standard solution for async + pgBouncer.

---

### Option 2: Use Supabase Session Pooler (port 5432) with asyncpg

**Implementation:**
```python
DATABASE_URL="postgresql+asyncpg://...@db.xxx.supabase.co:5432/postgres"
```

**Pros:**
- ✅ asyncpg works perfectly with session pooling
- ✅ Prepared statements work as designed
- ✅ Minimal code changes

**Cons:**
- ⚠️ Session pooling holds connections for entire client session (inefficient)
- ⚠️ Fewer available connections (session pool has lower limits)
- ⚠️ Not recommended for stateless API workloads
- ⚠️ Supabase charges more for session pooler at scale

**Verdict:** Suboptimal for FastAPI/REST API architecture.

---

### Option 3: Disable asyncpg Prepared Statements ❌ **NOT WORKING**

**Attempted Implementation:**
```python
# What we tried
connect_args={
    "statement_cache_size": 0,
    "server_settings": {"jit": "off"},
}
```

**Issues:**
- ❌ Settings not reliably passed to asyncpg connection
- ❌ SQLAlchemy's `async_engine_from_config` doesn't always honor connect_args
- ❌ Still got prepared statement errors during migrations
- ❌ Brittle workaround that may break in future versions

**Verdict:** Theoretically possible but unreliable in practice.

---

### Option 4: Switch to Synchronous SQLAlchemy ❌ **REJECTED**

**Implementation:**
Use `psycopg2` with synchronous `create_engine` (like previous app).

**Pros:**
- ✅ Simple, proven pattern
- ✅ Works with transaction pooling

**Cons:**
- ❌ Loses all async benefits (blocking I/O)
- ❌ FastAPI async routes become less efficient
- ❌ Worse concurrency under load
- ❌ Thread pool overhead instead of async event loop
- ❌ Step backward in architecture

**Verdict:** Defeats the purpose of using async FastAPI.

---

## Recommended Resolution

### **Switch to psycopg3 (psycopg[binary])**

This is the correct architectural choice for async FastAPI + Supabase transaction pooling.

---

## Implementation Steps

### Step 1: Update Dependencies

**File:** `backend/requirements.txt`

```diff
- asyncpg==0.30.0  # Async PostgreSQL driver
+ psycopg[binary]==3.2.3  # Async PostgreSQL driver (pgBouncer-compatible)
```

### Step 2: Update DATABASE_URL

**File:** `backend/.env`

```diff
- DATABASE_URL="postgresql+asyncpg://postgres:...@db.xxx.supabase.co:6543/postgres"
+ DATABASE_URL="postgresql+psycopg://postgres:...@db.xxx.supabase.co:6543/postgres"
```

### Step 3: Simplify Database Configuration

**File:** `backend/app/core/database.py`

```diff
# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
-   connect_args={
-       "server_settings": {"jit": "off"},
-       "statement_cache_size": 0,
-   },
)
```

Clean version:
```python
# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Supabase handles pooling
    pool_pre_ping=True,  # Verify connections before using
)
```

### Step 4: Simplify Alembic Configuration

**File:** `backend/migrations/env.py`

```diff
connectable = async_engine_from_config(
    configuration,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
-   connect_args={
-       "server_settings": {"jit": "off"},
-       "statement_cache_size": 0,
-   },
)
```

### Step 5: Reinstall Dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Step 6: Test Migration

```bash
# Generate migration (should work now)
alembic revision --autogenerate -m "initial schema - spirits and events"

# Run migration
alembic upgrade head
```

---

## Verification Checklist

After implementing the changes:

- [ ] Dependencies installed without errors
- [ ] Alembic can connect to database
- [ ] Migration generation works (`alembic revision --autogenerate`)
- [ ] Migration execution works (`alembic upgrade head`)
- [ ] No prepared statement errors in logs
- [ ] Tables created successfully in Supabase
- [ ] FastAPI can connect to database
- [ ] CRUD operations work in API endpoints

---

## Performance Comparison

| Driver | Async | pgBouncer TX | Benchmark Speed | Real-World Impact |
|--------|-------|--------------|-----------------|-------------------|
| asyncpg | ✅ | ❌ | Fastest | Blocked by errors |
| psycopg3 | ✅ | ✅ | Fast | **Recommended** |
| psycopg2 | ❌ | ✅ | N/A (sync) | Not suitable for async |

**Key Insight:** In production with network latency, the ~10% speed difference between asyncpg and psycopg3 is **negligible** compared to network I/O time. The ability to actually **run** without errors is infinitely more valuable than theoretical micro-benchmark gains.

---

## References

### Official Documentation

- [Supabase: Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [Supabase: Recommended Drivers](https://supabase.com/docs/guides/database/connecting-to-postgres#choosing-a-connection-method)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [SQLAlchemy: Async Support](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [pgBouncer: Pool Modes](https://www.pgbouncer.org/config.html#pool-mode)

### Related Issues

- [asyncpg + pgBouncer Incompatibility Discussion](https://github.com/MagicStack/asyncpg/issues/530)
- [SQLAlchemy async drivers comparison](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#postgresql-async-drivers)

---

## Decision Rationale

**Why psycopg3 over asyncpg?**

1. **Compatibility:** Works with pgBouncer transaction pooling (required for Supabase)
2. **Maturity:** Psycopg is the most mature PostgreSQL driver for Python
3. **Standards:** psycopg3 is the official successor to psycopg2
4. **Adoption:** Widely used in production (Django, Flask, FastAPI)
5. **Maintenance:** Actively developed, Python 3.11+ optimized
6. **Simplicity:** No workarounds or hacks needed

**When would asyncpg be better?**

- Direct PostgreSQL connection (no pgBouncer)
- Session pooling mode (not transaction pooling)
- Extreme performance requirements where every millisecond counts
- Benchmarking/testing scenarios

For Elephantasm's use case (Supabase with transaction pooling), **psycopg3 is the correct choice**.

---

## Timeline

| Date | Event |
|------|-------|
| 2025-10-17 | Issue discovered during migration execution |
| 2025-10-17 | Root cause identified (asyncpg + pgBouncer incompatibility) |
| 2025-10-17 | Options evaluated, psycopg3 recommended |
| **Next** | Implement driver switch and verify migrations work |

---

## Action Items

**Immediate (Blocking):**
1. [ ] Switch from asyncpg to psycopg3
2. [ ] Update DATABASE_URL driver prefix
3. [ ] Remove connect_args workarounds
4. [ ] Reinstall dependencies
5. [ ] Test migration execution
6. [ ] Verify tables created in Supabase

**Follow-up (Non-blocking):**
1. [ ] Update project documentation with driver choice rationale
2. [ ] Add connection troubleshooting guide
3. [ ] Document Supabase-specific configuration patterns
4. [ ] Consider adding database connection tests to CI/CD

---

**Status:** Ready for implementation
**Owner:** Development Team
**Priority:** P0 (Blocking migrations)

---

*This document serves as a reference for the architectural decision to use psycopg3 over asyncpg for async database operations with Supabase's pgBouncer transaction pooling.*
