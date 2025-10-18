  Core Architecture

  1. Two-Table Pattern

  - auth.users (Supabase managed): Handles authentication credentials, passwords, JWT issuance
  - public.users (Your schema): Extended user profile with enterprise context and business data

  2. Linkage Field: auth_uid

  # In your User model (backend/models/database/users.py:25)
  auth_uid: UUID = Field(
      unique=True,
      index=True,
      description="Supabase auth.users.id reference"
  )
  - This field in public.users references auth.users.id (the sub claim in JWT)
  - Not a foreign key (different schemas), but enforced as unique constraint
  - Indexed for fast lookups during authentication

  Automatic User Provisioning

  3. Database Trigger Pattern

  When a new user signs up in Supabase Auth, your system automatically creates the corresponding public.users record:

  -- Migration: 036d56ab118e_add_auth_foundation_tables.py:125-130
  CREATE TRIGGER on_auth_user_created
      AFTER INSERT ON auth.users
      FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

  4. The handle_new_user() Function

  -- Current version (ec2e3967eac1_fix_handle_new_user_function_after_.py:24-87)

  What it does:
  1. Triggered automatically when Supabase creates a new auth.users record
  2. Creates matching public.users record with:
    - auth_uid = NEW.id (from auth.users)
    - email = NEW.email
    - full_name = from JWT metadata or defaults to email
    - enterprise_id = from JWT metadata or default enterprise
    - role = from JWT metadata or defaults to 'member'
  3. Handles conflicts gracefully with ON CONFLICT (auth_uid) DO UPDATE
  4. Runs with SECURITY DEFINER to bypass RLS policies during provisioning

  Authentication Flow Integration

  5. JWT Token Structure

  When Supabase issues a JWT, it contains:
  {
    "sub": "<auth_uid>",           // Links to public.users.auth_uid
    "email": "user@example.com",
    "app_metadata": {
      "enterprise_id": "<uuid>",   // Optional
      "role": "member"             // Optional
    }
  }

  6. Two-Phase Bootstrap Process

  This is the clever part that solves a chicken-and-egg problem:

  The Problem:
  - Need user data from public.users to set RLS context
  - But querying public.users requires RLS context already set!

  The Solution (backend/core/auth.py:142-181):

  Phase 1: Minimal Context
  # Set just auth_uid for bootstrap policy
  db.execute(
      text("SELECT set_config('app.auth_uid', :auth_uid, true)"),
      {"auth_uid": auth_uid}
  )

  Phase 2: Self-Only Read
  # Special RLS policy allows users to read their OWN record
  user = db.exec(
      select(User)
      .where(User.auth_uid == auth_uid)
      .where(User.is_active == True)
  ).first()

  Phase 3: Full Context (in set_rls_context())
  # Now set complete RLS context from user data
  db.execute(text("""
      SELECT 
          set_config('app.user_id', :user_id, true),
          set_config('app.enterprise_id', :enterprise_id, true),
          set_config('app.user_role', :role, true)
  """), {...})

  Dual-Path RLS Architecture

  7. Unified Helper Functions

  Your system supports two database access paths:
  - Path 1: Frontend → Supabase API → Database (uses auth.uid())
  - Path 2: Backend → Database direct (uses session variables)

  Helper functions (dbd488299a02_implement_dual_path_rls_helper_functions.py):

  -- Works for BOTH paths
  app.effective_uid() → Returns auth.uid() OR current_setting('app.auth_uid')
  app.effective_enterprise_id() → Returns current_setting('app.enterprise_id')

  8. RLS Policies Pattern

  -- Example policy (uses helper functions)
  CREATE POLICY offers_isolation ON offers
  FOR ALL
  USING (enterprise_id = app.effective_enterprise_id());

  Key Design Decisions

  9. Why NOT a Foreign Key?

  - auth.users is in the auth schema (Supabase managed)
  - public.users is in your schema
  - PostgreSQL doesn't support cross-schema foreign keys well with RLS
  - Unique constraint + trigger provides equivalent guarantees

  10. Simplified Architecture Evolution

  - Original: Had user_enterprise_membership join table
  - Current: Direct fields on users table:
  enterprise_id: UUID  # Direct reference
  role: UserRole       # Stored on user, not membership

  11. Transaction-Scoped RLS Context

  Despite using SESSION pooling, RLS context is transaction-scoped (true parameter):
  set_config('app.auth_uid', :auth_uid, true)  # ← true = transaction scope

  Why?
  - Clean context boundaries
  - Security (no context leakage between requests)
  - Works with connection pooling

  Data Flow Summary

  User Signs Up
      ↓
  Supabase creates auth.users record
      ↓
  Trigger fires: handle_new_user()
      ↓
  Creates public.users record with auth_uid link
      ↓
  User logs in
      ↓
  JWT contains 'sub' (= auth_uid)
      ↓
  Backend validates JWT
      ↓
  Phase 1: Sets app.auth_uid from JWT 'sub'
      ↓
  Phase 2: Queries public.users WHERE auth_uid = JWT 'sub'
      ↓
  Phase 3: Sets full RLS context (user_id, enterprise_id, role)
      ↓
  All subsequent queries filtered by RLS policies

  This architecture provides complete separation between authentication (Supabase's domain) and authorization/business logic (your domain) while maintaining automatic synchronization and enterprise-level data isolation.