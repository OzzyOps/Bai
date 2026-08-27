# Runbook

Written for a tired person at 3am in a timezone nobody anticipated. Short
sentences, exact commands, no assumed context.

## Before anything else

```bash
curl -fsS https://api.bai.example/health
fly status --app bai-api-eu
supabase projects list
```

Identify the **region** first. Every subsequent command is region-scoped, and
running the right command against the wrong region is the easiest way to make an
incident worse.

---

## Agent runs are stuck in `running`

**Symptom:** `agent_runs.state = 'running'` with no progress.
**Blast radius:** one tenant, unless the queue is backed up for all.

```bash
fly logs --app bai-workers-eu | tail -100
redis-cli -u "$REDIS_URL" llen celery
```

Runs are durable and idempotent. Restarting a worker is **safe** — completed
steps are skipped by input hash, so nothing is repeated.

```bash
fly apps restart bai-workers-eu
```

If a specific run is wedged, requeue it. It will resume, not restart:

```bash
uv run celery -A bai_workers.celery_app call bai.agent.run --args='["<run_id>","<org_id>"]'
```

---

## A tenant reports missing data

**Do not reach for the service-role key.** In almost every case this is RLS
working correctly, and bypassing it turns a support question into an incident.

1. Confirm the user's `role` and `org_id` from their JWT.
2. Check whether the record is restricted:
   ```sql
   select * from record_restrictions where record_id = '<id>';
   ```
3. Check assignment — `manager`, `operator` and `viewer` see assigned records only:
   ```sql
   select * from record_assignments where record_id = '<id>';
   ```

The fix is an assignment or a grant made by an admin **in the product**, never a
manual database write.

---

## Inference budget exhausted

**Symptom:** runs failing with `budget_exceeded`; API returning 402.

This is the guard working. Do not raise the ceiling to clear a queue without
understanding why spend rose.

```sql
select org_id, sum(cost_minor), cost_currency
from agent_runs
where started_at > now() - interval '30 days'
group by org_id, cost_currency
order by 2 desc;
```

Check for a re-ingest loop: the same document hash analysed repeatedly means
deduplication is broken, which is a bug, not a capacity problem.

---

## Suspected cross-tenant exposure

**Treat as a P0 immediately.**

1. Do not investigate in production with a service-role key — you will destroy
   the evidence of what a normal user could actually see.
2. Reproduce with the affected user's own token in staging.
3. Run the coverage assertion:
   ```bash
   supabase db execute --file scripts/assert_rls_coverage.sql
   ```
4. Run the isolation suite against the affected region:
   ```bash
   SUPABASE_DB_URL=... uv run pytest packages/platform-py/tests/test_rls.py -v
   ```
5. Engage `secops`. **Breach-notification clocks differ by jurisdiction and
   change — confirm the current requirement for every affected region before
   relying on any figure. Do not use a remembered number.**

---

## Rollback

Every deployment must have a tested rollback before it is used in anger.

```bash
fly releases --app bai-api-eu
fly deploy --app bai-api-eu --image <previous-image>
```

**Migrations:** a migration without a reverse path should not have merged. If one
did, roll back the application first and leave the schema alone — a forward-
compatible app on a newer schema is recoverable; a mangled schema is not.

---

## Escalations piling up

Not an outage. Either the agent's confidence has dropped, or an autonomy grant
was revoked.

```sql
select action_name, count(*) from escalations
where state = 'open' group by 1 order by 2 desc;
```

If one action dominates, check whether a recent change moved the confidence
distribution. Run the golden set before concluding anything:

```bash
uv run python scripts/eval/run_golden_set.py --all --calibration
```

**Never clear the queue by granting autonomy.** That converts a quality problem
into a silent correctness problem.
