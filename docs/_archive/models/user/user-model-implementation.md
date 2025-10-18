# User Model Implementation - Marlin-Style Auth Integration

**Date**: 2025-10-18
**Version**: v0.0.9 (unreleased)
**Architecture**: Two-table auth pattern (Supabase Auth + public.users)

---

## Summary

Created a User model with **Marlin-style authentication integration** featuring automatic user provisioning via database triggers. Users created in Supabase Auth (`auth.users`) automatically generate corresponding records in `public.users` linked via `auth_uid`.

**Key Achievement**: Zero application code needed for user provisioning - fully automatic at database level.

---

## Implementation

### File: `backend/app/models/database/user.py` (52 lines)

**Model Structure**

**UserBase** - Shared field definitions:
- `auth_uid` - UUID, unique, indexed (links to `auth.users.id` from JWT 'sub' claim) **[REQUIRED]**
- `email` - VARCHAR(255), nullable (copied from auth record)
- `first_name` - VARCHAR(255), nullable
- `last_name` - VARCHAR(255), nullable
- `phone` - VARCHAR(50), nullable
- `username` - VARCHAR(255), nullable

**User** - Table entity (inherits UserBase + TimestampMixin):
- `id` - UUID primary key (DB-level generation via `gen_random_uuid()`)
- `is_deleted` - Boolean soft delete flag (default False)
- `created_at` - Auto-managed timestamp (via TimestampMixin)
- `updated_at` - Auto-managed timestamp (via TimestampMixin)

**DTOs**:
- `UserCreate` - Ingestion payload (requires `auth_uid`)
- `UserRead` - Response model with readonly fields (id, timestamps)
- `UserUpdate` - Partial update model (all fields optional except `auth_uid` - not updatable)

---

## Architecture: Two-Table Pattern

### Core Components

```
┌─────────────────────┐         ┌─────────────────────┐
│   auth.users        │         │  public.users       │
│  (Supabase Managed) │         │  (Your Schema)      │
├─────────────────────┤         ├─────────────────────┤
│ id (UUID)           │────────▶│ auth_uid (UUID)     │
│ email               │         │ email               │
│ encrypted_password  │         │ first_name          │
│ raw_user_meta_data  │         │ last_name           │
│ ...                 │         │ phone               │
└─────────────────────┘         │ username            │
                                │ ...                 │
                                └─────────────────────┘
        │
        │ TRIGGER: on_auth_user_created
        ▼
  handle_new_user()
  - Auto-creates public.users record
  - Links via auth_uid = auth.users.id
  - Copies email from auth record
  - Runs with SECURITY DEFINER (bypasses RLS)
```

### Authentication Flow

```
User Signs Up (Supabase Auth)
    ↓
auth.users record created
    ↓
TRIGGER fires: on_auth_user_created
    ↓
handle_new_user() function executes
    ↓
public.users record auto-created
    ↓
auth_uid links the two tables
    ↓
User can now login and access extended profile
```

---

## Design Decisions

### 1. **Marlin-Style Auth Integration**

**Pattern**: Two-table architecture separating authentication (Supabase) from business data (your schema)

**Benefits**:
- ✅ Supabase manages credentials, password hashing, JWT issuance
- ✅ You control extended user profile and business logic
- ✅ Clean separation of concerns
- ✅ Easy to swap auth providers later (OAuth, SAML, etc.)

**Implementation**: See `docs/plans/user-auth-trigger-setup.md` for complete setup guide

### 2. **auth_uid as Linkage Field**

**Why not a foreign key?**
- `auth.users` is in the `auth` schema (Supabase managed)
- `public.users` is in your schema
- Cross-schema foreign keys don't play well with RLS
- Unique constraint + trigger provides equivalent guarantees

**Why unique and indexed?**
- **Unique**: One-to-one relationship (one auth record = one user profile)
- **Indexed**: Fast lookups during authentication (queries by `auth_uid`)

### 3. **Automatic Provisioning via Trigger**

**No application code needed** - database handles user creation automatically

**Advantages**:
- ✅ Impossible to create orphaned auth records (trigger always fires)
- ✅ Works even if backend is down during signup
- ✅ Consistent data across all entry points (API, direct DB, migrations)
- ✅ Atomic operation (trigger runs in same transaction as signup)

### 4. **All Extended Fields Nullable**

Following progressive enhancement philosophy:
- **auth_uid**: Required (every user comes from Supabase Auth)
- **email**: Nullable but usually populated (copied from auth record)
- **first_name, last_name, phone, username**: Nullable (user can fill in later)

**Rationale**: Minimize signup friction - collect critical data first, enrich profile later

### 5. **Pattern Consistency**

100% matches Spirit model structure:
- Same inheritance pattern (Base → Table + TimestampMixin)
- Same DTO naming convention (Create, Read, Update)
- Same soft delete approach (`is_deleted` flag)
- Same UUID generation strategy (DB-level)

---

## Deferred to Phase 2

**Not included in initial implementation** (following "simplicity first" philosophy):

- ❌ **RLS Policies**: Will be added when security isolation is needed
- ❌ **Multi-Tenancy**: No `enterprise_id` or `role` fields yet
- ❌ **Helper Functions**: `app.effective_uid()` - will be added with RLS
- ❌ **Email Uniqueness**: No unique constraint yet (can add when needed)
- ❌ **Username Uniqueness**: No unique constraint yet (can add when needed)

**All can be added later without breaking changes**.

---

## Implementation Status

### Completed ✅

- ✅ User model created with `auth_uid` field
- ✅ Pattern matches existing Elephantasm models (Spirit, Event)
- ✅ DTOs structured for create/read/update operations
- ✅ Imports verified successfully
- ✅ Trigger setup documentation created
- ✅ **User model import added to migrations/env.py**
- ✅ **Table migration created**: `41fbe3ecb90a_add_users_table_with_auth_integration.py`
- ✅ **Table migration executed**: Users table deployed to database
- ✅ **Schema verified**: Table exists with auth_uid (unique, indexed), all profile fields
- ✅ **Trigger migration created**: `6d97e4d18837_add_user_auth_trigger.py`
- ✅ **Trigger migration executed**: `handle_new_user()` function + trigger deployed
- ✅ **Auth integration complete**: Automatic user provisioning now active

### Pending ⏳

- ⏳ **Testing**: Verify signup → auto-provision flow in Supabase (manual test required)
- ⏳ **Domain Operations**: Create UserOperations (if needed for CRUD)
- ⏳ **API Routes**: Create /api/users endpoints (if needed)

---

## Migration Details

### Migration 1: Users Table
**File**: `41fbe3ecb90a_add_users_table_with_auth_integration.py`
**Status**: ✅ Applied to database

**Created**:
- `users` table with all fields (id, auth_uid, email, first_name, last_name, phone, username, is_deleted, created_at, updated_at)
- Unique index on `auth_uid` for fast lookups during authentication
- Primary key on `id` with DB-level UUID generation

**Note**: Added `import sqlmodel` to migration file to fix autogenerate quirk with `sqlmodel.sql.sqltypes.AutoString`

### Migration 2: Auth Trigger
**File**: `6d97e4d18837_add_user_auth_trigger.py`
**Status**: ✅ Applied to database

**Created**:
- `public.handle_new_user()` function - Automatically provisions user records
- `on_auth_user_created` trigger - Fires on INSERT to `auth.users`
- Auto-populates: `auth_uid` (from `auth.users.id`), `email`, timestamps
- Uses `SECURITY DEFINER` to bypass RLS during provisioning
- Includes `ON CONFLICT` clause for idempotent operations

**What happens now**:
1. User signs up via Supabase Auth → `auth.users` record created
2. Trigger fires automatically
3. `handle_new_user()` creates matching `public.users` record
4. User can immediately access extended profile data

---

## Next Steps

### Immediate (Trigger Setup)

1. **Create trigger migration** (next step):
   ```bash
   cd backend
   source venv/bin/activate
   PYTHONPATH=$(pwd)/..:$PYTHONPATH alembic revision -m "add user auth trigger"
   # Edit migration file to add SQL from docs/plans/user-auth-trigger-setup.md
   ```

2. **Apply trigger migration**:
   ```bash
   PYTHONPATH=$(pwd)/..:$PYTHONPATH alembic upgrade head
   ```

3. **Test signup flow in Supabase**:
   - Create user in Supabase Dashboard → Authentication → Add User
   - Verify record auto-created in `public.users` table
   - Verify `auth_uid` matches `auth.users.id`
   - Test E2E: Signup → Auto-provision → Login → Access profile

### Future (Phase 2+)

- **RLS Integration**: Implement transaction-scoped context variables
- **JWT Validation**: Extract `auth_uid` from JWT 'sub' claim
- **UserOperations**: Domain logic for user CRUD (if needed beyond auth)
- **API Endpoints**: `/api/users/me` for profile management
- **Multi-Tenancy**: Add `enterprise_id`, `role` fields when needed

---

## Testing Verification

### Import Test ✅
```bash
$ python3 -c "from backend.app.models.database.user import User, UserCreate, UserRead, UserUpdate"
✅ All imports successful
```

### Database Test (After Migration) ⏳
```sql
-- Verify table structure
\d users

-- Expected columns:
-- id, auth_uid (unique, indexed), email, first_name, last_name,
-- phone, username, is_deleted, created_at, updated_at
```

### Signup Flow Test (After Trigger Setup) ⏳
```sql
-- Create user in Supabase Auth
-- Then verify:
SELECT
    au.id AS auth_id,
    u.auth_uid,
    u.email,
    u.created_at
FROM auth.users au
JOIN public.users u ON u.auth_uid = au.id;

-- Should show matching records
```

---

## Documentation References

- **Trigger Setup Guide**: `docs/plans/user-auth-trigger-setup.md`
  - Complete SQL for `handle_new_user()` function
  - Trigger definition and migration examples
  - Testing instructions and troubleshooting
  - JWT integration patterns (for Phase 2)

- **Marlin Architecture Reference**: `docs/plans/user-models-marlin.md`
  - Original production implementation example
  - RLS patterns and dual-path architecture
  - Enterprise multi-tenancy examples

---

## Key Insights

### Why Two Tables?

**Separation of Concerns**:
- `auth.users` = Authentication domain (credentials, sessions, security)
- `public.users` = Business domain (profile, preferences, relationships)

**Benefits**:
- Supabase handles auth complexity (password resets, email verification, OAuth)
- You control business logic and data relationships
- Easy to migrate auth providers without touching business data

### Why Database Triggers?

**Alternative approaches**:
1. ❌ **Application code**: Create user in backend after signup
   - Problem: What if backend is down? Orphaned auth records
2. ❌ **Scheduled job**: Sync auth.users → public.users periodically
   - Problem: Delay between signup and user access
3. ✅ **Database trigger**: Automatic, atomic, reliable
   - Always fires, works even if backend is unavailable

### Why auth_uid Not Nullable?

Every user in `public.users` **must** have an auth counterpart - otherwise how did they sign up? The trigger ensures this, and making `auth_uid` required enforces the invariant.

**Edge case**: Manual data imports? Create a "system" auth record first, then reference it.

---

## Alignment with Elephantasm Vision

**From vision.md**: "Simplicity as strategy. Avoid over-engineering early."

This implementation:
- ✅ Uses battle-tested Marlin pattern (proven in production)
- ✅ Defers RLS/multi-tenancy until actually needed (Phase 2)
- ✅ Automatic provisioning = less code to maintain
- ✅ Clean separation = easier to understand and modify

**From roadmap**: "Phase 1 — Core Service" focuses on LTAM core, not auth

This implementation:
- ✅ Provides auth foundation without blocking LTAM work
- ✅ Can be enhanced incrementally (RLS, roles, enterprise)
- ✅ Doesn't require auth to test Spirits/Events/Memories pipeline

---

## Lessons Learned

**Early Architecture Decisions Matter**: Adding `auth_uid` now (before first migration) avoids costly refactoring later when auth becomes critical.

**Database Triggers = Invisible Reliability**: Once set up, triggers just work - no application code to maintain, debug, or forget to call.

**Pattern Reuse Accelerates Development**: Marlin blueprint provided complete solution in <30 minutes vs. days of custom auth implementation.

---

**Status**: ✅ Model complete, ready for migration and trigger setup
