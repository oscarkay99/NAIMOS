# Security

## Authentication

JWT access tokens (short-lived, default 30 min) + refresh tokens (default 7
days), bcrypt password hashing (`app/core/security.py`). The frontend stores
tokens in `localStorage` and transparently refreshes on a 401
(`apps/web/src/lib/api.ts`). MFA is not implemented in this prototype; the
`users.mfa_enabled` column exists so it can be added without a schema change.

## Authorization (RBAC)

10 roles (`SUPER_ADMIN` … `AUDITOR`), each mapped to a set of fine-grained
permission codes (`app/core/permissions.py`), stored in the database
(`roles`/`permissions`/`role_permissions`) and seeded from that same mapping.
Every protected route declares its required permission via the
`require_permission(code)` FastAPI dependency (`app/api/deps.py`), which
checks the authenticated user's role against the **database-backed**
permission set - never a frontend-only check. The frontend also hides
nav items/controls the user lacks permission for, but that is UX only; the
API enforces the real boundary (verified by `tests/test_auth_rbac.py`).

## Audit logging

`services/audit.py::log_action()` is called inside the same DB transaction as
every sensitive action: login/logout, incident creation/update/status change,
evidence upload/download, AI queries, AI image analysis, AI detection
feedback, report generation. Records are append-only (`audit_logs`) and
capture who, what, previous/new value, reason, and timestamp. Nothing in the
API updates or deletes an audit row.

## Data classification

`incidents.classification` (`PUBLIC` / `INTERNAL` / `SENSITIVE` /
`RESTRICTED`) exists per section 26. This prototype does not yet gate reads
by classification level beyond role-based permissions - a full build would
add a classification check alongside `require_permission`.

## Evidence integrity

Every uploaded file is hashed (SHA-256) and stored with a UUID-prefixed name;
`evidence_versions` records every replacement as a new version rather than
overwriting the original (section 11).

## AI query safety

See AI.md - the assistant only runs a fixed set of parametrized queries
against a `SELECT`-only Postgres role, with a query timeout and row limit.

## What's not hardened in this prototype

CSRF protection (not applicable to this bearer-token JSON API, but would
matter for a cookie-based session), rate limiting, structured secret
management beyond `.env`, and the full security test suite (SQL injection /
role escalation / malicious upload fuzzing) described in spec section 46 -
only representative RBAC-denial tests are included (`tests/test_auth_rbac.py`).
Treat this as a functional prototype, not a hardened production deployment.

## Secrets

`.env.example` lists every variable with placeholder values; `.env` is
git-ignored. No credentials are committed.
