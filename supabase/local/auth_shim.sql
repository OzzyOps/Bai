-- BAi · local auth shim
--
-- Recreates the pieces of Supabase's `auth` schema that the migrations depend on,
-- so tenant-isolation tests can run against a plain Postgres 16 — in CI, in a
-- container, or anywhere Docker and the Supabase CLI are not available.
--
-- NOT for any real environment. Hosted Supabase provides all of this itself;
-- applying this there would collide with the real auth schema.
--
--   psql -f supabase/local/auth_shim.sql
--   psql -f supabase/migrations/*.sql   (in order)
--   psql -f supabase/seed.sql

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin noinherit bypassrls;
  end if;
end $$;

create schema if not exists auth;
grant usage on schema auth to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;

-- Only the columns the migrations actually reference.
create table if not exists auth.users (
  id                 uuid primary key default gen_random_uuid(),
  email              text unique,
  raw_user_meta_data jsonb not null default '{}'::jsonb,
  created_at         timestamptz not null default now()
);

-- Supabase reads the verified JWT from the `request.jwt.claims` GUC. Same here,
-- so policies behave identically; the difference is that nothing verifies the
-- token locally, which is precisely why this file is local-only.
create or replace function auth.jwt() returns jsonb
language sql stable as $$
  select coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb,
    '{}'::jsonb
  )
$$;

create or replace function auth.uid() returns uuid
language sql stable as $$
  select nullif(auth.jwt() ->> 'sub', '')::uuid
$$;

grant execute on function auth.jwt(), auth.uid() to anon, authenticated, service_role;

-- Supabase grants table privileges to these roles by default, BEFORE any
-- migration runs. Order matters: a migration that revokes a privilege (as
-- `audit_log` does, to make the table append-only) must run last, or the
-- revoke is silently undone. Using default privileges reproduces that order.
alter default privileges in schema public
  grant select, insert, update, delete on tables to authenticated;
alter default privileges in schema public
  grant usage, select on sequences to authenticated;
alter default privileges in schema public
  grant execute on functions to anon, authenticated, service_role;
