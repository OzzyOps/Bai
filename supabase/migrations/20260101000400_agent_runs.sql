-- BAi platform · agent runs, steps and facts
-- Invariant 1: every step is persisted with its input hash, so a resumed run
-- never repeats an action it already completed.

create type run_state as enum
  ('pending','running','awaiting_human','completed','failed','cancelled');

create table public.agent_runs (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.orgs(id)    on delete cascade,
  record_id    uuid          references public.records(id) on delete cascade,
  product      text not null,
  agent        text not null,
  state        run_state not null default 'pending',
  started_by   uuid references auth.users(id),
  error        text,
  -- cost is money: minor units plus an explicit currency, never a float
  cost_minor   bigint  not null default 0,
  cost_currency char(3) not null default 'USD',
  started_at   timestamptz not null default now(),
  completed_at timestamptz,
  constraint run_cost_currency_iso check (cost_currency ~ '^[A-Z]{3}$'),
  constraint run_terminal_has_end check (
    state not in ('completed','failed','cancelled') or completed_at is not null
  )
);
create index runs_org_idx    on public.agent_runs(org_id);
create index runs_record_idx on public.agent_runs(record_id);
create index runs_open_idx   on public.agent_runs(org_id, state)
  where state in ('pending','running','awaiting_human');

create table public.agent_steps (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.orgs(id)        on delete cascade,
  run_id        uuid not null references public.agent_runs(id)  on delete cascade,
  ordinal       integer not null,
  name          text    not null,
  input_hash    char(64) not null,
  output        jsonb,
  tokens_in     integer not null default 0,
  tokens_out    integer not null default 0,
  cost_minor    bigint  not null default 0,
  cost_currency char(3) not null default 'USD',
  started_at    timestamptz not null default now(),
  completed_at  timestamptz,
  constraint step_unique_ord unique (run_id, ordinal),
  -- the idempotency key: one completed step per (run, name, input)
  constraint step_unique_work unique (run_id, name, input_hash)
);
create index steps_run_idx on public.agent_steps(run_id);

-- Invariant 2: no fact exists without provenance. Enforced by NOT NULL on the
-- source columns plus the check below — not by application convention.
create table public.agent_facts (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.orgs(id)       on delete cascade,
  run_id      uuid not null references public.agent_runs(id) on delete cascade,
  record_id   uuid          references public.records(id)    on delete cascade,
  key         text not null,
  value       jsonb not null,
  confidence  real not null,
  document_id uuid not null references public.documents(id)  on delete cascade,
  locator     text not null,
  char_start  integer,
  char_end    integer,
  created_at  timestamptz not null default now(),
  constraint fact_confidence_range check (confidence >= 0 and confidence <= 1),
  constraint fact_span_valid check (
    (char_start is null and char_end is null) or (char_end > char_start)
  )
);
create index facts_run_idx    on public.agent_facts(run_id);
create index facts_record_idx on public.agent_facts(record_id, key);
-- Facts below the confidence floor render as `unknown`, never as a finding.
create index facts_uncertain_idx on public.agent_facts(org_id)
  where confidence < 0.70;
