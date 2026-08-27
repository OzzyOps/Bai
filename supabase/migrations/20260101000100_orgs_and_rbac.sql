-- BAi platform · orgs, membership, RBAC
-- Jurisdiction is a tenant attribute. Nothing here assumes a country or currency.

create type bai_role as enum ('owner','admin','manager','operator','viewer');
create type bai_region as enum ('eu','uk','us','apac','jp','br');

create table public.orgs (
  id                  uuid primary key default gen_random_uuid(),
  name                text        not null,
  region              bai_region  not null,
  -- ISO 4217 alpha-3. Independent of region and locale — never inferred.
  currency            char(3)     not null,
  -- BCP 47 with region subtag, e.g. 'de-DE', 'ja-JP', 'pt-BR'
  locale              text        not null,
  timezone            text        not null default 'UTC',
  -- ISO 3166-1 alpha-2 codes this tenant operates under
  jurisdictions       char(2)[]   not null default '{}',
  lawful_basis        text,
  data_sharing_optout boolean     not null default true,
  retention_days      integer     not null default 2555,
  created_at          timestamptz not null default now(),
  constraint currency_is_iso4217 check (currency ~ '^[A-Z]{3}$'),
  constraint locale_has_region   check (locale ~ '^[a-z]{2,3}-[A-Za-z0-9]{2,4}$'),
  constraint retention_positive  check (retention_days > 0)
);

create table public.org_members (
  org_id     uuid      not null references public.orgs(id) on delete cascade,
  user_id    uuid      not null references auth.users(id)  on delete cascade,
  role       bai_role  not null default 'viewer',
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);
create index org_members_user_idx on public.org_members(user_id);

-- Generic tenant record spine. Products extend via `domain_data` and their own
-- tables; every one of them carries org_id and gets the same RLS treatment.
create table public.records (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.orgs(id) on delete cascade,
  product      text not null,
  external_ref text,
  title        text not null,
  status       text not null default 'open',
  -- money as minor units + explicit currency. Never numeric, never float.
  value_minor  bigint,
  value_currency char(3),
  domain_data  jsonb not null default '{}',
  created_by   uuid references auth.users(id),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint value_currency_iso check (value_currency is null or value_currency ~ '^[A-Z]{3}$'),
  constraint value_pair_complete check (
    (value_minor is null and value_currency is null)
    or (value_minor is not null and value_currency is not null)
  )
);
create index records_org_idx     on public.records(org_id);
create index records_org_product on public.records(org_id, product, status);

create table public.record_assignments (
  record_id uuid not null references public.records(id) on delete cascade,
  user_id   uuid not null references auth.users(id)     on delete cascade,
  primary key (record_id, user_id)
);

-- Per-record ACL for commercially sensitive items. Even `owner` is excluded
-- unless explicitly granted, and grants are themselves audited.
create table public.record_restrictions (
  record_id  uuid primary key references public.records(id) on delete cascade,
  reason     text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create table public.record_restriction_grants (
  record_id  uuid not null references public.records(id) on delete cascade,
  user_id    uuid not null references auth.users(id)     on delete cascade,
  granted_by uuid references auth.users(id),
  granted_at timestamptz not null default now(),
  primary key (record_id, user_id)
);

create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

create trigger records_touch before update on public.records
for each row execute function public.touch_updated_at();
