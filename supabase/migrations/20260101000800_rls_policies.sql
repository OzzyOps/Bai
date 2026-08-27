-- BAi platform · Row Level Security
--
-- THE RULE: tenant isolation is enforced here, never in application code.
-- Application checks are defence in depth. This file is the boundary.
--
-- Every policy derives org_id from the JWT, never from a request parameter.

alter table public.orgs                      enable row level security;
alter table public.org_members               enable row level security;
alter table public.records                   enable row level security;
alter table public.record_assignments        enable row level security;
alter table public.record_restrictions       enable row level security;
alter table public.record_restriction_grants enable row level security;

-- ── helpers ────────────────────────────────────────────────────────────────
create or replace function public.jwt_org_id() returns uuid
language sql stable as $$ select nullif(auth.jwt() ->> 'org_id','')::uuid $$;

create or replace function public.jwt_role() returns text
language sql stable as $$ select coalesce(auth.jwt() ->> 'role','viewer') $$;

-- Visible unless restricted; restricted only with an explicit grant.
-- Note this excludes `owner` too — that is deliberate, and it is the control
-- that survives enterprise security review.
create or replace function public.record_visible(rid uuid) returns boolean
language sql stable as $$
  select not exists (select 1 from public.record_restrictions rr where rr.record_id = rid)
      or exists (select 1 from public.record_restriction_grants g
                 where g.record_id = rid and g.user_id = auth.uid());
$$;

create or replace function public.record_in_scope(rid uuid) returns boolean
language sql stable as $$
  select public.jwt_role() in ('owner','admin')
      or exists (select 1 from public.record_assignments ra
                 where ra.record_id = rid and ra.user_id = auth.uid());
$$;

-- ── orgs ───────────────────────────────────────────────────────────────────
create policy orgs_select on public.orgs for select to authenticated
  using (id = public.jwt_org_id());

create policy orgs_update on public.orgs for update to authenticated
  using (id = public.jwt_org_id() and public.jwt_role() in ('owner','admin'))
  with check (id = public.jwt_org_id() and public.jwt_role() in ('owner','admin'));

-- ── membership ─────────────────────────────────────────────────────────────
create policy members_select on public.org_members for select to authenticated
  using (org_id = public.jwt_org_id());

-- A member may not escalate their own role, nor touch an owner.
create policy members_write on public.org_members for all to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and (role <> 'owner' or public.jwt_role() = 'owner')
  )
  with check (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and (role <> 'owner' or public.jwt_role() = 'owner')
  );

-- ── records ────────────────────────────────────────────────────────────────
create policy records_select on public.records for select to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.record_in_scope(id)
    and public.record_visible(id)
  );

create policy records_insert on public.records for insert to authenticated
  with check (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager')
  );

create policy records_update on public.records for update to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager')
    and public.record_in_scope(id)
    and public.record_visible(id)
  )
  with check (org_id = public.jwt_org_id());

create policy records_delete on public.records for delete to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin')
    and public.record_visible(id)
  );

-- ── assignments ────────────────────────────────────────────────────────────
create policy assignments_select on public.record_assignments for select to authenticated
  using (exists (select 1 from public.records r
                 where r.id = record_id and r.org_id = public.jwt_org_id()));

create policy assignments_write on public.record_assignments for all to authenticated
  using (
    public.jwt_role() in ('owner','admin','manager')
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  )
  with check (
    public.jwt_role() in ('owner','admin','manager')
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  );

-- ── restrictions ───────────────────────────────────────────────────────────
create policy restrictions_select on public.record_restrictions for select to authenticated
  using (exists (select 1 from public.records r
                 where r.id = record_id and r.org_id = public.jwt_org_id()));

create policy restrictions_write on public.record_restrictions for all to authenticated
  using (
    public.jwt_role() in ('owner','admin')
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  )
  with check (
    public.jwt_role() in ('owner','admin')
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  );

-- A user may read their own grants; only admins may create them, and never
-- for themselves — self-granting access to a restricted record is the exact
-- privilege escalation this table exists to prevent.
create policy grants_select on public.record_restriction_grants for select to authenticated
  using (
    user_id = auth.uid()
    or (public.jwt_role() in ('owner','admin')
        and exists (select 1 from public.records r
                    where r.id = record_id and r.org_id = public.jwt_org_id()))
  );

create policy grants_write on public.record_restriction_grants for all to authenticated
  using (
    public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  )
  with check (
    public.jwt_role() in ('owner','admin')
    and user_id <> auth.uid()
    and exists (select 1 from public.records r
                where r.id = record_id and r.org_id = public.jwt_org_id())
  );
