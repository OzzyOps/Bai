# RBAC

Five roles, defined once at platform level in
`packages/platform-py/src/bai_platform/rbac/`. **Products may add permissions.
Products may never add roles** — a sixth role would have to be reasoned about in
every RLS policy, every product, forever.

## Matrix

| Permission | viewer | operator | manager | admin | owner |
|---|:--:|:--:|:--:|:--:|:--:|
| `record:read:assigned` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `record:read:all` | — | — | — | ✅ | ✅ |
| `record:create` / `record:update` | — | — | ✅ | ✅ | ✅ |
| `record:delete` | — | — | — | ✅ | ✅ |
| `document:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `document:create` / `document:update` | — | — | ✅ | ✅ | ✅ |
| `document:delete` | — | — | — | ✅ | ✅ |
| `run:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `run:start` | — | ✅ | ✅ | ✅ | ✅ |
| `run:cancel` | — | — | ✅ | ✅ | ✅ |
| `escalation:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`escalation:resolve`** | — | **✅** | ✅ | ✅ | ✅ |
| `autonomy:grant` | — | — | — | ✅ | ✅ |
| `restriction:grant` | — | — | — | ✅ | ✅ |
| `dsr:execute` | — | — | — | ✅ | ✅ |
| `member:manage` | — | — | — | ✅ | ✅ |
| `audit:read` | — | — | — | ✅ | ✅ |
| `billing:manage` | — | — | — | — | ✅ |

Each role is a strict superset of the one below. `test_rbac.py` asserts this,
so a permission cannot be granted to `viewer` and accidentally withheld from
`admin`.

## Why `operator` exists

`operator` can **resolve escalations but not change records**. That separation
is the point: it lets the exception queue be handed to someone who processes
volume without granting them authority over the underlying data.

Delegability is what makes the automation worth buying. If only a manager could
clear the queue, the customer has moved work rather than removed it.

## Restricted records

`record_restrictions` marks a record commercially sensitive. **Even `owner` is
excluded** unless explicitly granted, and grants are audited.

A user cannot grant themselves access — the RLS policy carries
`user_id <> auth.uid()`. This is the control that survives enterprise security
review, and `test_rls.py` asserts it.

## Where enforcement actually happens

| Layer | Purpose | Authoritative? |
|---|---|---|
| `Can` component (React) | Hides controls the user cannot use | ❌ Courtesy only |
| `require(Permission)` (FastAPI) | Rejects early with a clear message | ❌ Defence in depth |
| **RLS policy (Postgres)** | Refuses to return the rows | ✅ **Yes** |

The first two exist so users get a good message instead of an empty screen.
Neither is a security boundary. If the RLS policy is missing, the data is
exposed regardless of what the other two layers do.

## JWT claims

```json
{ "sub": "<user_uuid>", "org_id": "<uuid>", "role": "operator", "tier": "scale", "region": "eu" }
```

Set by a Supabase Auth hook. `org_id` and `role` are read by every RLS policy via
`auth.jwt()`. A forged claim does not widen access: the org row is itself read
under RLS, so an org_id the user is not a member of returns nothing.
