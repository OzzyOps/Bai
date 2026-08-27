-- BAi platform · escalations and autonomy grants
-- Invariant 3: escalation is a first-class outcome, not an error.
-- Invariant 4: consequential and irreversible actions cannot be automated away.

create type consequence_level as enum ('none','reversible','consequential');
create type autonomy_level    as enum ('none','suggest','act_with_approval','act');
create type escalation_state  as enum ('open','resolved','expired');

create table public.escalations (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.orgs(id)       on delete cascade,
  run_id       uuid not null references public.agent_runs(id) on delete cascade,
  record_id    uuid          references public.records(id)    on delete cascade,
  action_name  text not null,
  consequence  consequence_level not null,
  reversible   boolean not null,
  reason       text not null,
  confidence   real,
  payload      jsonb not null default '{}',
  options      jsonb not null default '[]',
  state        escalation_state not null default 'open',
  resolved_by  uuid references auth.users(id),
  resolution   text,
  created_at   timestamptz not null default now(),
  resolved_at  timestamptz,
  constraint esc_confidence_range check (confidence is null or (confidence >= 0 and confidence <= 1)),
  constraint esc_resolved_complete check (
    state <> 'resolved' or (resolved_by is not null and resolved_at is not null)
  )
);
create index esc_open_idx   on public.escalations(org_id, state) where state = 'open';
create index esc_record_idx on public.escalations(record_id);

-- Autonomy is granted per action type, per tenant — never globally, never by
-- default. The trigger below refuses a grant that would automate an
-- irreversible consequential action.
create table public.autonomy_grants (
  org_id       uuid not null references public.orgs(id) on delete cascade,
  action_name  text not null,
  level        autonomy_level not null default 'none',
  consequence  consequence_level not null,
  reversible   boolean not null,
  evidence_url text,
  granted_by   uuid references auth.users(id),
  granted_at   timestamptz not null default now(),
  primary key (org_id, action_name)
);

create or replace function public.reject_unsafe_autonomy() returns trigger
language plpgsql as $$
begin
  if new.level = 'act'
     and new.consequence = 'consequential'
     and new.reversible = false then
    raise exception
      'cannot grant full autonomy for %: the action is consequential and irreversible',
      new.action_name
      using hint = 'A human must approve it. This is a locked platform decision.';
  end if;
  return new;
end;
$$;

create trigger autonomy_grants_guard
before insert or update on public.autonomy_grants
for each row execute function public.reject_unsafe_autonomy();
