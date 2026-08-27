-- BAi platform · append-only audit trail
--
-- The table grants INSERT and SELECT and NOTHING ELSE. No role, including
-- `owner`, may UPDATE or DELETE. That is what makes this evidence rather than
-- a log, and it is what SOC 2, ISO 27001 and SOX all actually check.

create table public.audit_log (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references public.orgs(id) on delete cascade,
  action         text not null,
  actor_id       uuid references auth.users(id),
  actor_is_agent boolean not null default false,
  subject_type   text,
  subject_id     uuid,
  metadata       jsonb not null default '{}',
  at             timestamptz not null default now(),
  -- an unattributed entry is not an audit entry
  constraint audit_has_actor check (actor_id is not null or actor_is_agent)
);
create index audit_org_at_idx  on public.audit_log(org_id, at desc);
create index audit_subject_idx on public.audit_log(subject_type, subject_id);
create index audit_action_idx  on public.audit_log(org_id, action, at desc);

-- Belt and braces: revoke at the grant level AND block at the trigger level,
-- so a future migration that carelessly re-grants cannot silently open a hole.
revoke update, delete on public.audit_log from authenticated, anon;

create or replace function public.audit_is_append_only() returns trigger
language plpgsql as $$
begin
  raise exception 'audit_log is append-only; % is not permitted', tg_op;
end;
$$;

create trigger audit_no_mutation
before update or delete on public.audit_log
for each row execute function public.audit_is_append_only();
