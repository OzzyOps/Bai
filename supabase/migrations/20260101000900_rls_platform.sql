-- BAi platform · RLS for documents, runs, escalations and audit
--
-- Same rule as everywhere: org_id comes from the JWT, never from a parameter.
-- Every table below inherits record scope, so a viewer who cannot see a record
-- cannot see its documents, its agent facts, or its escalations either.

alter table public.documents        enable row level security;
alter table public.document_chunks  enable row level security;
alter table public.agent_runs       enable row level security;
alter table public.agent_steps      enable row level security;
alter table public.agent_facts      enable row level security;
alter table public.escalations      enable row level security;
alter table public.autonomy_grants  enable row level security;
alter table public.audit_log        enable row level security;

-- Record-scoped visibility, reused by every child table. A null record_id means
-- org-level, visible to anyone in the org who is not otherwise restricted.
create or replace function public.child_visible(rid uuid) returns boolean
language sql stable as $$
  select rid is null
      or (public.record_in_scope(rid) and public.record_visible(rid));
$$;

-- ── documents ──────────────────────────────────────────────────────────────
create policy documents_select on public.documents for select to authenticated
  using (org_id = public.jwt_org_id() and public.child_visible(record_id));

create policy documents_insert on public.documents for insert to authenticated
  with check (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager')
    and public.child_visible(record_id)
  );

create policy documents_delete on public.documents for delete to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin')
    and public.child_visible(record_id)
  );

-- Chunks carry embeddings. Cross-tenant leakage through vector search is a
-- common and severe miss, so the policy is the same as for the parent document.
create policy chunks_select on public.document_chunks for select to authenticated
  using (
    org_id = public.jwt_org_id()
    and exists (
      select 1 from public.documents d
      where d.id = document_id and public.child_visible(d.record_id)
    )
  );

-- ── agent runs ─────────────────────────────────────────────────────────────
create policy runs_select on public.agent_runs for select to authenticated
  using (org_id = public.jwt_org_id() and public.child_visible(record_id));

create policy runs_insert on public.agent_runs for insert to authenticated
  with check (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager','operator')
    and public.child_visible(record_id)
  );

create policy runs_update on public.agent_runs for update to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager')
    and public.child_visible(record_id)
  )
  with check (org_id = public.jwt_org_id());

create policy steps_select on public.agent_steps for select to authenticated
  using (
    org_id = public.jwt_org_id()
    and exists (select 1 from public.agent_runs r
                where r.id = run_id and public.child_visible(r.record_id))
  );

-- Facts carry the citation a user clicks through to. Same scope as the record.
create policy facts_select on public.agent_facts for select to authenticated
  using (org_id = public.jwt_org_id() and public.child_visible(record_id));

-- ── escalations ────────────────────────────────────────────────────────────
create policy escalations_select on public.escalations for select to authenticated
  using (org_id = public.jwt_org_id() and public.child_visible(record_id));

-- `operator` may resolve without being able to change the record. That
-- separation is what makes the exception queue delegable.
create policy escalations_update on public.escalations for update to authenticated
  using (
    org_id = public.jwt_org_id()
    and public.jwt_role() in ('owner','admin','manager','operator')
    and public.child_visible(record_id)
  )
  with check (org_id = public.jwt_org_id());

-- ── autonomy grants ────────────────────────────────────────────────────────
create policy autonomy_select on public.autonomy_grants for select to authenticated
  using (org_id = public.jwt_org_id());

-- Granting autonomy is an admin act, and the trigger in the previous migration
-- still refuses an unsafe combination even for an owner.
create policy autonomy_write on public.autonomy_grants for all to authenticated
  using (org_id = public.jwt_org_id() and public.jwt_role() in ('owner','admin'))
  with check (org_id = public.jwt_org_id() and public.jwt_role() in ('owner','admin'));

-- ── audit ──────────────────────────────────────────────────────────────────
-- Readable by admins only; insertable by anyone in the org so that ordinary
-- actions can log themselves. UPDATE and DELETE have no policy at all, and are
-- additionally blocked by revoke + trigger.
create policy audit_select on public.audit_log for select to authenticated
  using (org_id = public.jwt_org_id() and public.jwt_role() in ('owner','admin'));

create policy audit_insert on public.audit_log for insert to authenticated
  with check (org_id = public.jwt_org_id());
