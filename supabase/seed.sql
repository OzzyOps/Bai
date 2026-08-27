-- Local development seed. Synthetic data only.
-- Preview environments use this too — production data never reaches a preview.

insert into public.orgs (id, name, region, currency, locale, timezone, jurisdictions, lawful_basis)
values
  ('00000000-0000-0000-0000-0000000000e1','Meridian Operations GmbH','eu','EUR','de-DE','Europe/Berlin','{DE,AT}','contract'),
  ('00000000-0000-0000-0000-0000000000e2','Kanda Shoji KK','jp','JPY','ja-JP','Asia/Tokyo','{JP}','contract'),
  ('00000000-0000-0000-0000-0000000000e3','Northgate Services Ltd','uk','GBP','en-GB','Europe/London','{GB}','legitimate_interest')
on conflict (id) do nothing;

-- Money is minor units. 4,820,000 JPY-minor is ¥4,820,000 because JPY has no
-- minor unit; 1,245,000 GBP-minor is £12,450.00. Getting this wrong by
-- assuming two decimals everywhere is the classic global-product bug.
insert into public.records (org_id, product, external_ref, title, status, value_minor, value_currency)
values
  ('00000000-0000-0000-0000-0000000000e2','reconcile','REC-4471','Supplier onboarding — Kanda KK','open',4820000,'JPY'),
  ('00000000-0000-0000-0000-0000000000e3','reconcile','REC-4468','Q3 licence true-up','open',1245000,'GBP'),
  ('00000000-0000-0000-0000-0000000000e1','reconcile','REC-4455','Freight invoice batch 88-B','open',214900,'EUR')
on conflict do nothing;

-- ───────────────────────────────────────────────────────────────────────────
-- ISOLATION FIXTURE
--
-- packages/platform-py/tests/test_rls.py asserts that a user of org A can see
-- nothing belonging to org B. Without rows in org B those assertions pass
-- while proving nothing: "0 rows leaked" is trivially true of an empty table.
-- Everything below exists so that a broken policy has something to leak.
--
-- Org A = …a1 (user …a001) · Org B = …b1 (user …b001). Synthetic throughout.
-- ───────────────────────────────────────────────────────────────────────────

insert into auth.users (id, email, raw_user_meta_data) values
  ('00000000-0000-0000-0000-00000000a001','ana@org-a.test','{"full_name":"Ana (org A)"}'),
  ('00000000-0000-0000-0000-00000000b001','ben@org-b.test','{"full_name":"Ben (org B)"}')
on conflict (id) do nothing;

insert into public.orgs (id, name, region, currency, locale, timezone, jurisdictions, lawful_basis) values
  ('00000000-0000-0000-0000-0000000000a1','Org A (isolation fixture)','eu','EUR','fr-FR','Europe/Paris','{FR}','contract'),
  ('00000000-0000-0000-0000-0000000000b1','Org B (isolation fixture)','us','USD','en-US','America/New_York','{US}','contract')
on conflict (id) do nothing;

insert into public.org_members (org_id, user_id, role) values
  ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-00000000a001','admin'),
  ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000b001','admin')
on conflict do nothing;

insert into public.records (id, org_id, product, external_ref, title, status, value_minor, value_currency) values
  ('00000000-0000-0000-0000-00000000aa01','00000000-0000-0000-0000-0000000000a1','reconcile','A-1','Org A record','open',100000,'EUR'),
  ('00000000-0000-0000-0000-00000000bb01','00000000-0000-0000-0000-0000000000b1','reconcile','B-1','Org B record','open',250000,'USD'),
  -- restricted inside its own org: visible to nobody without an explicit grant
  ('00000000-0000-0000-0000-00000000bb02','00000000-0000-0000-0000-0000000000b1','reconcile','B-2','Org B restricted record','open',999000,'USD')
on conflict (id) do nothing;

insert into public.record_assignments (record_id, user_id) values
  ('00000000-0000-0000-0000-00000000aa01','00000000-0000-0000-0000-00000000a001'),
  ('00000000-0000-0000-0000-00000000bb01','00000000-0000-0000-0000-00000000b001')
on conflict do nothing;

insert into public.record_restrictions (record_id, reason) values
  ('00000000-0000-0000-0000-00000000bb02','fixture: exercises the restriction path')
on conflict do nothing;

insert into public.documents (id, org_id, record_id, filename, media_type, sha256, byte_size, storage_path) values
  ('00000000-0000-0000-0000-0000000d0a01','00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-00000000aa01','a.pdf','application/pdf',repeat('a',64),1024,'a1/a.pdf'),
  ('00000000-0000-0000-0000-0000000d0b01','00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000bb01','b.pdf','application/pdf',repeat('b',64),2048,'b1/b.pdf')
on conflict (id) do nothing;

insert into public.document_chunks (org_id, document_id, ordinal, content, char_start, char_end, locator) values
  ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000d0a01',0,'org A chunk',0,11,'p.1'),
  ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000d0b01',0,'org B chunk — must never be readable by org A',0,45,'p.1')
on conflict do nothing;

insert into public.agent_runs (id, org_id, record_id, product, agent, state, completed_at) values
  ('00000000-0000-0000-0000-000000700a01','00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-00000000aa01','reconcile','matcher','completed', now()),
  ('00000000-0000-0000-0000-000000700b01','00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000bb01','reconcile','matcher','completed', now())
on conflict (id) do nothing;

insert into public.agent_steps (org_id, run_id, ordinal, name, input_hash, output) values
  ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-000000700a01',0,'extract',repeat('1',64),'{"ok":true}'),
  ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-000000700b01',0,'extract',repeat('2',64),'{"ok":true}')
on conflict do nothing;

insert into public.agent_facts (org_id, run_id, record_id, key, value, confidence, document_id, locator, char_start, char_end) values
  ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-000000700a01','00000000-0000-0000-0000-00000000aa01','total','{"minor":100000,"currency":"EUR"}',0.94,'00000000-0000-0000-0000-0000000d0a01','p.1',0,11),
  ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-000000700b01','00000000-0000-0000-0000-00000000bb01','total','{"minor":250000,"currency":"USD"}',0.91,'00000000-0000-0000-0000-0000000d0b01','p.1',0,11)
on conflict do nothing;

insert into public.escalations (org_id, run_id, record_id, action_name, consequence, reversible, reason, confidence) values
  ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-000000700a01','00000000-0000-0000-0000-00000000aa01','approve_match','reversible',true,'confidence below threshold',0.41),
  ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-000000700b01','00000000-0000-0000-0000-00000000bb01','post_payment','consequential',false,'irreversible by definition',0.88)
on conflict do nothing;

insert into public.autonomy_grants (org_id, action_name, level, consequence, reversible) values
  ('00000000-0000-0000-0000-0000000000a1','approve_match','act','reversible',true),
  ('00000000-0000-0000-0000-0000000000b1','approve_match','act_with_approval','reversible',true)
on conflict do nothing;

-- An audit row in each org. The append-only trigger fires per row, so with an
-- empty table `update audit_log` succeeds with 0 rows and the test proves nothing.
insert into public.audit_log (org_id, action, actor_id, subject_type, subject_id) values
  ('00000000-0000-0000-0000-0000000000a1','record.created','00000000-0000-0000-0000-00000000a001','record','00000000-0000-0000-0000-00000000aa01'),
  ('00000000-0000-0000-0000-0000000000b1','record.created','00000000-0000-0000-0000-00000000b001','record','00000000-0000-0000-0000-00000000bb01')
on conflict do nothing;
