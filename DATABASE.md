# Database

PostgreSQL + PostGIS. Schema is managed entirely through Alembic migrations in
`apps/api/alembic/versions/` - do not hand-edit the database; add a migration.

## Core tables

| Table | Purpose |
|---|---|
| `roles`, `permissions`, `role_permissions`, `users` | RBAC (section 23) |
| `regions`, `districts`, `communities` | Ghana administrative geography |
| `water_bodies`, `protected_areas`, `forest_reserves` | Environmental reference geometry (PostGIS `GEOMETRY`) |
| `incidents`, `incident_status_history` | Core incident record + full status audit trail |
| `investigations`, `assignments`, `teams`, `officers`, `operations` | Workflow/assignment |
| `field_reports` | Field submissions, incl. voice-to-report transcript/extraction |
| `evidence`, `evidence_versions` | Hashed, versioned evidence files (originals never overwritten) |
| `ai_detections` | AI change-detection signals, always `requires_verification` |
| `risk_scores`, `risk_factors` | Explainable risk score + its named contributing factors |
| `reports`, `report_sources` | Generated PRO/intelligence reports + the incident IDs backing them |
| `audit_logs` | Append-only log of every sensitive action |
| `ai_queries` | Audit trail of every NL question sent to the AI assistant |
| `notifications`, `system_settings` | Supporting tables |

## Key relationships

- `incidents.region_id` / `district_id` → `regions` / `districts`.
- `incident_status_history.incident_id` → `incidents`, one row per transition
  (previous status, new status, who, when, why).
- `risk_scores.incident_id` → `incidents`; `risk_factors.risk_score_id` →
  `risk_scores` (one score, many labeled factors).
- `evidence.incident_id` → `incidents`; `evidence_versions.evidence_id` →
  `evidence` (append-only version history).
- `field_reports.incident_id` → `incidents` (nullable - a voice report can be
  captured before an incident exists).
- `report_sources` is a join table from a generated `reports` row to every
  `incidents.id` that backed it, so every generated statement is traceable.

## Geospatial

All location columns are PostGIS `Geometry(SRID=4326)`. GIST spatial indexes
are created by hand in the initial migration (`geoalchemy2`'s
`spatial_index=True` auto-DDL is disabled to avoid double-creating them
under Alembic - see the comment in `alembic/env.py`). Distance queries in
`services/geospatial/queries.py` cast to `geography` so results are real
metres, not degrees.

## Read-only role

`naimos_readonly` (created in `docker/init/01-extensions-and-roles.sql`,
granted SELECT via `apps/api/scripts/grant_readonly.sql` after migrations
run) is used exclusively by the AI assistant's query pipeline - see AI.md.
