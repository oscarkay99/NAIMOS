# NAIMOS Intelligence

**AI-Assisted Illegal Mining Intelligence & Operations Platform** - a decision-support
prototype for NAIMOS Ghana. Helps authorized personnel monitor suspected illegal-mining
activity, prioritize locations for field verification, manage incidents and evidence,
and generate intelligence/PRO communications - with AI outputs always labeled and
subject to human verification. See the full product spec in
`NAIMOS AI Intelligence & Operations Platform - Master VS Code Build Prompt.md`.

> **DEMO ENVIRONMENT - DATA IS SIMULATED.** All incidents, field reports, evidence, and
> AI detections in the seed data are synthetic (`is_demo=true`). Regions/districts and
> named rivers/forest reserves use real, public Ghanaian geography; nothing else should
> be treated as real operational data.

## What's implemented

- **Auth & RBAC** - JWT login/refresh, bcrypt hashing, 10 roles with a real
  permissions table, server-side permission checks on every route.
- **PostGIS database** - regions/districts/communities, water bodies, protected
  areas, forest reserves, incidents + status history, investigations/assignments,
  teams/officers, field reports, evidence + versioning, AI detections, risk
  scores/factors, audit logs, AI query log, reports.
- **Explainable risk engine** - rule-based 0–100 "Operational Risk / Investigation
  Priority Score" with a labeled factor breakdown (never a black box).
- **Geospatial intelligence map** - MapLibre (token-free tiles), layered
  incidents/hotspots/water bodies/protected areas/forest reserves/AI detections,
  click-to-inspect Location Intelligence panel.
- **Incident lifecycle** - CRUD, status workflow with full audit trail.
- **Evidence management** - hashed, versioned uploads; originals are never
  overwritten.
- **Field reporting** - responsive (phone-usable) incident form, plus a
  voice-to-report flow (transcribe → structured draft → officer review/approve).
- **AI assistant** - natural language → allowlisted, parametrized queries only
  (never free-form AI-generated SQL) against a read-only DB role.
- **PRO Communications Centre** - report/briefing generator built only from
  database records, separating VERIFIED FACTS from AI-GENERATED INTERPRETATION.
- **Audit logging** - every sensitive action (login, status change, evidence
  upload/download, AI query, report generation) is recorded.
- **Analytics** - incidents over time/region/status, verification rate, team
  workload, driven by live DB aggregates.

See the build plan and explicitly deferred scope (native mobile app, live
satellite imagery, Elasticsearch, SMS/WhatsApp/email providers, exhaustive
security test suite) in `ARCHITECTURE.md`.

## Quick start

### 1. Database

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 2. API

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../../.env.example .env   # edit if needed
alembic upgrade head
psql "$DATABASE_URL" -f scripts/grant_readonly.sql   # or: docker exec -i naimos-postgres psql -U naimos -d naimos < scripts/grant_readonly.sql
python -m app.seeds.seed_data
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Web

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000 - log in with any seeded account (password `Demo@1234`):
`admin@naimos.gov.gh`, `officer@naimos.gov.gh`, `analyst@naimos.gov.gh`,
`pro@naimos.gov.gh`, `auditor@naimos.gov.gh`, etc. (full list in `DEMO.md`).

### Tests

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - system design, provider abstractions, scope
- [DATABASE.md](DATABASE.md) - schema and key relationships
- [AI.md](AI.md) - AI guardrails, LLM provider abstraction, NL→query pipeline
- [SECURITY.md](SECURITY.md) - auth, RBAC, audit logging, data classification
- [DEMO.md](DEMO.md) - demo accounts, scenarios, walkthrough script
- [ENVIRONMENT.md](ENVIRONMENT.md) - environment variables
