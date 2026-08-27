# Data retention and erasure

Retention is a **tenant attribute** (`orgs.retention_days`, default 2555 — seven
years). Regulated financial-services tenants routinely need longer; some
jurisdictions require shorter. Nothing in the platform assumes a global default.

## Classes

| Class | Default | Notes |
|---|---|---|
| Customer content (documents, chunks) | tenant-configured | The tenant owns this decision |
| Embeddings | lifetime of the source | **Deleted with the source. Most-missed path.** |
| Agent runs and steps | 3 years | Evidence of automated decision-making (GDPR Art. 22) |
| Agent facts | lifetime of the record | Carries the citation a user clicks through to |
| Audit trail | 7 years, immutable | Never deleted, including by erasure |
| Prompt/response logs | 30 days, PII-redacted | Debugging only |
| Telemetry | 25 months, pseudonymous | Never contains customer content |
| Backups | 35 days, region-local | Erasure reconciled against the backup cycle |

## Erasure order — this order, always

```
embeddings → chunks → documents → record → tombstone
```

Deleting the document first orphans its embeddings. Orphaned vectors remain
searchable, so content the customer believes erased can still surface in a RAG
result. This is the single most common erasure failure in AI products, and the
reason `enforce_retention` in `apps/workers` is explicit about the sequence.

The **audit trail survives erasure**. That is not an oversight — demonstrating
*that* data was erased, by whom and when, requires a record that erasure does not
touch. The trail holds no customer content by construction (`AuditEntry` rejects
content keys), so preserving it does not preserve the erased material.

## Data subject requests

`POST /dsr/export` returns machine-readable data for a subject within the tenant.
`POST /dsr/erase` returns **202** — erasure cascades and cannot complete inline.

Response clocks differ by regime and change. `docs/RUNBOOK.md` holds the current
values; **verify them at incident time rather than reproducing them from
memory.** Do not treat any figure written here or in `company/COMPLIANCE.md` as
legal authority.

## Regional boundary

Erasure runs in the tenant's region against that region's Supabase project. There
is no cross-region replication, so there is no second copy to chase — which is
precisely why the architecture is worth its cost.
