# User Authentication Trigger Setup

**Purpose**: Automatically provision `public.users` records when users sign up via Supabase Auth

**Status**: 📋 Planned (to be implemented after users table migration)

**Architecture**: Marlin-style two-table pattern (see `docs/plans/user-models-marlin.md`)

---

## Overview

When a user signs up through Supabase Auth:
1. Supabase creates a record in `auth.users` (managed by Supabase)
2. Database trigger fires automatically
3. `handle_new_user()` function creates matching record in `public.users`
4. `auth_uid` field links the two tables (references `auth.users.id`)

**Key Benefit**: Zero application code needed for user provisioning - it's automatic at the database level.

---

## Implementation Steps

### Step 1: Create the `handle_new_user()` Function

This PostgreSQL function runs when the trigger fires.

```sql
-- To be run after users table migration
-- File: backend/migrations/versions/<timestamp>_add_user_auth_trigger.py

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER -- Bypass RLS during provisioning
AS $$
BEGIN
    -- Create public.users record from auth.users data
    INSERT INTO public.users (
        auth_uid,
        email,
        first_name,
        last_name,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,                    -- auth.users.id → public.users.auth_uid
        NEW.email,                 -- Copy email from auth record
        NULL,                      -- Will be populated by user later
        NULL,                      -- Will be populated by user later
        NOW(),
        NOW()
    )
    ON CONFLICT (auth_uid) DO UPDATE SET
        email = EXCLUDED.email,    -- Update email if changed
        updated_at = NOW();

    RETURN NEW;
END;
$$;
```

**Key Points**:
- `SECURITY DEFINER`: Runs with function creator's privileges (bypasses RLS)
- `ON CONFLICT (auth_uid) DO UPDATE`: Handles duplicate signups gracefully
- `NEW.id`: References the newly inserted `auth.users.id`
- `NEW.email`: Copies email from Supabase Auth record

### Step 2: Create the Trigger

```sql
-- Create trigger on auth.users table
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
```

**Key Points**:
- `AFTER INSERT`: Fires after `auth.users` record is created
- `FOR EACH ROW`: Executes once per signup
- Automatically calls `handle_new_user()` function

### Step 3: Apply via Alembic Migration

**Recommended Approach**: Create Alembic migration for version control

```python
# Example migration file structure
# backend/migrations/versions/<timestamp>_add_user_auth_trigger.py

def upgrade():
    # Create the function
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            INSERT INTO public.users (auth_uid, email, created_at, updated_at)
            VALUES (NEW.id, NEW.email, NOW(), NOW())
            ON CONFLICT (auth_uid) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = NOW();
            RETURN NEW;
        END;
        $$;
    """)

    # Create the trigger
    op.execute("""
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION public.handle_new_user();
    """)

def downgrade():
    # Drop trigger first (depends on function)
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user();")
```

### Step 4: Manual Application (Alternative)

If you prefer to run SQL directly in Supabase SQL Editor:

1. Go to Supabase Dashboard → SQL Editor
2. Run the `CREATE FUNCTION` statement
3. Run the `CREATE TRIGGER` statement
4. Verify with: `SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';`

---

## Testing

### Test 1: Signup Flow

```bash
# Sign up a new user via Supabase Auth
# (Use Supabase Dashboard → Authentication → Add User, or use Supabase JS client)

# Then verify in SQL Editor:
SELECT
    au.id AS auth_id,
    au.email AS auth_email,
    u.id AS user_id,
    u.auth_uid,
    u.email AS user_email,
    u.created_at
FROM auth.users au
LEFT JOIN public.users u ON u.auth_uid = au.id
ORDER BY au.created_at DESC
LIMIT 5;
```

**Expected Result**: Every `auth.users` record has a matching `public.users` record with `auth_uid = auth.users.id`

### Test 2: Duplicate Handling

```sql
-- Manually trigger the function (simulates duplicate signup)
INSERT INTO auth.users (email, encrypted_password)
VALUES ('test@example.com', 'dummy-hash-value');

-- Should NOT create duplicate in public.users
-- Should UPDATE existing record instead
```

### Test 3: Email Sync

```sql
-- Update email in auth.users
UPDATE auth.users SET email = 'newemail@example.com' WHERE email = 'oldemail@example.com';

-- Note: This won't auto-sync to public.users (trigger is INSERT only)
-- If you need email sync on UPDATE, add another trigger:
-- CREATE TRIGGER on_auth_user_updated AFTER UPDATE ON auth.users...
```

---

## JWT Integration (Future Phase 2)

Once RLS is implemented, the authentication flow will be:

1. **User logs in** → Supabase issues JWT
2. **JWT contains**:
   ```json
   {
     "sub": "<auth_uid>",           // Links to public.users.auth_uid
     "email": "user@example.com",
     "aud": "authenticated"
   }
   ```
3. **Backend validates JWT** → Extracts `auth_uid` from `sub` claim
4. **Set RLS context**:
   ```python
   # Phase 1: Set minimal context
   db.execute(text("SELECT set_config('app.auth_uid', :auth_uid, true)"), {"auth_uid": auth_uid})

   # Phase 2: Query user record (RLS allows self-read)
   user = db.exec(select(User).where(User.auth_uid == auth_uid)).first()

   # Phase 3: Set full context (if needed for multi-tenancy later)
   db.execute(text("SELECT set_config('app.user_id', :user_id, true)"), {"user_id": str(user.id)})
   ```

---

## Advanced: Extracting Metadata from JWT

If you want to pre-populate user fields from JWT metadata:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_metadata JSONB;
BEGIN
    -- Extract raw_user_meta_data from auth.users
    user_metadata := NEW.raw_user_meta_data;

    INSERT INTO public.users (
        auth_uid,
        email,
        first_name,
        last_name,
        username,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        NEW.email,
        user_metadata->>'first_name',    -- From signup metadata
        user_metadata->>'last_name',     -- From signup metadata
        user_metadata->>'username',      -- From signup metadata
        NOW(),
        NOW()
    )
    ON CONFLICT (auth_uid) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = NOW();

    RETURN NEW;
END;
$$;
```

**Signup with metadata** (Supabase JS example):
```javascript
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'secure-password',
  options: {
    data: {
      first_name: 'John',
      last_name: 'Doe',
      username: 'johndoe'
    }
  }
})
```

---

## Security Considerations

### Why `SECURITY DEFINER`?

Without it, the function runs with the permissions of the user who triggered it. Since new users don't exist yet in `public.users`, they have no RLS context and the INSERT would fail.

`SECURITY DEFINER` makes the function run with superuser privileges, bypassing RLS during provisioning.

### Why `ON CONFLICT` Instead of Checking Existence?

- **Performance**: Single upsert is faster than SELECT + conditional INSERT
- **Concurrency**: Handles race conditions (two signups at exact same time)
- **Idempotency**: Safe to retry if signup fails partway through

---

## Deferred Features (Phase 2+)

**Not included in initial implementation**:

- ❌ **RLS Policies**: Will be added when multi-tenancy is needed
- ❌ **Enterprise/Organization Fields**: `enterprise_id`, `role` - deferred
- ❌ **Email Update Sync**: Separate `UPDATE` trigger if needed
- ❌ **Helper Functions**: `app.effective_uid()` - will be added with RLS
- ❌ **User Deletion Handling**: Cascade behavior on `auth.users` deletion

**Can be added later without breaking changes**.

---

## Migration Timeline

```
Step 1: Create users table (alembic revision --autogenerate -m "add users table")
  ↓
Step 2: Apply migration (alembic upgrade head)
  ↓
Step 3: Create trigger migration (alembic revision -m "add user auth trigger")
  ↓
Step 4: Apply trigger (alembic upgrade head)
  ↓
Step 5: Test signup flow in Supabase Dashboard
  ↓
Done! Users auto-provision on signup
```

---

## Troubleshooting

### Issue: Trigger not firing

```sql
-- Verify trigger exists
SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Verify function exists
SELECT proname FROM pg_proc WHERE proname = 'handle_new_user';

-- Check trigger is enabled
SELECT tgenabled FROM pg_trigger WHERE tgname = 'on_auth_user_created';
-- Result should be 'O' (origin - fires for all)
```

### Issue: Permission errors

```sql
-- Verify function has SECURITY DEFINER
SELECT proname, prosecdef FROM pg_proc WHERE proname = 'handle_new_user';
-- prosecdef should be 't' (true)
```

### Issue: Unique constraint violation

```sql
-- Check for duplicate auth_uid values
SELECT auth_uid, COUNT(*)
FROM public.users
GROUP BY auth_uid
HAVING COUNT(*) > 1;

-- Fix: Delete duplicates, keeping oldest
DELETE FROM public.users
WHERE id NOT IN (
    SELECT MIN(id) FROM public.users GROUP BY auth_uid
);
```

---

## References

- Marlin Blueprint: `docs/plans/user-models-marlin.md`
- Supabase Triggers Documentation: https://supabase.com/docs/guides/database/postgres/triggers
- PostgreSQL Trigger Documentation: https://www.postgresql.org/docs/current/sql-createtrigger.html
