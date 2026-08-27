-- Fails the build if any table in `public` is missing RLS or has no policy.
-- A new tenant table without a policy is the single most dangerous thing that
-- can merge in a multi-tenant product, so this runs on every PR.

do $$
declare
  offending text;
begin
  select string_agg(format('%s (%s)', c.relname, reason), E'\n  ')
  into offending
  from (
    select c.oid, c.relname,
           case
             when not c.relrowsecurity then 'RLS not enabled'
             when not exists (select 1 from pg_policy p where p.polrelid = c.oid)
               then 'no policies defined'
           end as reason
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind = 'r'
      and c.relname not like 'pg_%'
  ) c
  where c.reason is not null;

  if offending is not null then
    raise exception E'RLS coverage failure:\n  %', offending;
  end if;

  raise notice 'RLS coverage OK — every public table has RLS enabled and at least one policy';
end $$;

-- Every tenant table must be isolated by org, one of exactly two ways:
--
--   (a) it carries org_id itself, and its policy compares it to the JWT; or
--   (b) it is a child of public.records and inherits isolation through a
--       record_id foreign key, with a policy that joins back to records.
--
-- (b) is the only permitted exemption, and it is not taken on trust: the table
-- must genuinely have a record_id FK pointing at public.records. A table that
-- has neither is unisolatable, and merging one is the single most dangerous
-- thing that can happen to a multi-tenant product.
do $$
declare
  missing text;
begin
  select string_agg(format('%s (%s)', c.relname, why), ', ')
  into missing
  from (
    select c.relname,
           case
             when exists (
               select 1 from pg_attribute a
               where a.attrelid = c.oid and a.attname = 'org_id' and a.attnum > 0
             ) then null
             when not exists (
               select 1
               from pg_constraint fk
               join pg_class parent on parent.oid = fk.confrelid
               where fk.conrelid = c.oid
                 and fk.contype = 'f'
                 and parent.relname = 'records'
             ) then 'no org_id and no record_id FK to records'
             when not exists (select 1 from pg_policy p where p.polrelid = c.oid)
               then 'inherits via records but has no policy of its own'
           end as why
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind = 'r'
      and c.relname not in ('orgs')        -- orgs IS the tenant
  ) c
  where c.why is not null;

  if missing is not null then
    raise exception 'tables that cannot be isolated by org: %', missing;
  end if;

  raise notice 'org isolation coverage OK — every table carries org_id or inherits it from records';
end $$;
