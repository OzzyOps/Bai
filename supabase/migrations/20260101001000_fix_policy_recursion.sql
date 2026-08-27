-- BAi platform · fix: RLS policy recursion made `records` unreadable
--
-- FOUND BY TEST, NOT BY REVIEW. With any row present in record_restrictions,
-- an ordinary `select count(*) from public.records` failed outright with
-- 54001 statement_too_complex — stack depth exceeded. Not an edge case: the
-- core table of the platform became unreadable for the whole org the moment
-- the first sensitive record was restricted.
--
-- THE CYCLE
--   policy records_select        → calls record_visible(id)
--   record_visible               → selects public.record_restrictions
--   policy restrictions_select   → selects public.records
--   policy records_select        → calls record_visible(id) …
--
-- Policy helper functions are invoker-rights by default, so every table they
-- read has its own policies applied, and those policies read back into the
-- table that called them. Postgres only breaks the loop by running out of
-- stack, which is why this presented as a resource error rather than a
-- recursion error and would have been baffling in production.
--
-- THE FIX
-- The helpers become SECURITY DEFINER with a pinned search_path. A definer
-- function does not re-enter RLS, so the cycle cannot form. This is the
-- standard pattern for RLS helpers and is exactly why Supabase's own
-- documentation recommends it.
--
-- Why this is safe: each helper takes a record id and answers one boolean
-- about the CALLER (auth.uid(), jwt_org_id()) — it never returns a row, never
-- takes org_id as a parameter, and cannot be used to read another tenant's
-- data. The pinned search_path closes the classic definer escalation, where a
-- caller shadows `public` with a schema of their own.
--
-- Idempotent: safe on a fresh database and on one that already ran 000800/000900.

create or replace function public.record_visible(rid uuid) returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select not exists (select 1 from public.record_restrictions rr where rr.record_id = rid)
      or exists (select 1 from public.record_restriction_grants g
                 where g.record_id = rid and g.user_id = auth.uid());
$$;

create or replace function public.record_in_scope(rid uuid) returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select public.jwt_role() in ('owner','admin')
      or exists (select 1 from public.record_assignments ra
                 where ra.record_id = rid and ra.user_id = auth.uid());
$$;

create or replace function public.child_visible(rid uuid) returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select rid is null
      or (public.record_in_scope(rid) and public.record_visible(rid));
$$;

-- Replaces `exists (select 1 from public.records r where r.id = … and r.org_id = …)`
-- in the child-table policies. Same question, asked without re-entering the
-- policy on records. Returns a boolean only — never the org id itself.
create or replace function public.record_in_my_org(rid uuid) returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select exists (select 1 from public.records r
                 where r.id = rid and r.org_id = public.jwt_org_id());
$$;

revoke execute on function
  public.record_visible(uuid), public.record_in_scope(uuid),
  public.child_visible(uuid), public.record_in_my_org(uuid)
from public, anon;

grant execute on function
  public.record_visible(uuid), public.record_in_scope(uuid),
  public.child_visible(uuid), public.record_in_my_org(uuid)
to authenticated, service_role;

-- ── policies rebuilt to use the definer helper ─────────────────────────────
-- Only the ones that read public.records directly. Behaviour is unchanged;
-- the difference is that they no longer recurse.

drop policy if exists assignments_select on public.record_assignments;
create policy assignments_select on public.record_assignments for select to authenticated
  using (public.record_in_my_org(record_id));

drop policy if exists assignments_write on public.record_assignments;
create policy assignments_write on public.record_assignments for all to authenticated
  using (
    public.jwt_role() in ('owner','admin','manager')
    and public.record_in_my_org(record_id)
  )
  with check (
    public.jwt_role() in ('owner','admin','manager')
    and public.record_in_my_org(record_id)
  );

drop policy if exists restrictions_select on public.record_restrictions;
create policy restrictions_select on public.record_restrictions for select to authenticated
  using (public.record_in_my_org(record_id));

drop policy if exists restrictions_write on public.record_restrictions;
create policy restrictions_write on public.record_restrictions for all to authenticated
  using (
    public.jwt_role() in ('owner','admin')
    and public.record_in_my_org(record_id)
  )
  with check (
    public.jwt_role() in ('owner','admin')
    and public.record_in_my_org(record_id)
  );

drop policy if exists grants_select on public.record_restriction_grants;
create policy grants_select on public.record_restriction_grants for select to authenticated
  using (
    user_id = auth.uid()
    or (public.jwt_role() in ('owner','admin') and public.record_in_my_org(record_id))
  );

-- The self-grant block is the point of this table: an admin may grant another
-- user access to a restricted record, never themselves.
drop policy if exists grants_write on public.record_restriction_grants;
create policy grants_write on public.record_restriction_grants for all to authenticated
  using (
    public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and public.record_in_my_org(record_id)
  )
  with check (
    public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and public.record_in_my_org(record_id)
  );
