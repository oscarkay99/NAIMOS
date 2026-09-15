# Architecture

## Stack

- **apps/web** - Next.js 14 (App Router) + TypeScript + Tailwind CSS + MapLibre GL.
  Talks to the API only via `src/lib/api.ts` (JWT bearer auth, automatic refresh).
- **apps/api** - FastAPI + SQLAlchemy 2 + Alembic + GeoAlchemy2, PostgreSQL/PostGIS.
- **docker/** - Postgres+PostGIS and Redis via Docker Compose for local dev.

## Monorepo layout

```
apps/
  web/    Next.js frontend - dashboard, map, incidents, field UI, assistant, comms
  api/    FastAPI backend
    app/
      core/        settings, security (JWT/bcrypt), RBAC permission matrix
      db/          SQLAlchemy base + session (+ a separate read-only session)
      models/      ORM models (one module per domain area)
      schemas/     Pydantic request/response models
      api/routes/  one router per resource
      services/
        ai/            LLMProvider abstraction, mock + OpenAI-compatible impl,
                        allowlisted NL→query pipeline, voice extraction
        risk/           explainable rule-based risk engine
        geospatial/     PostGIS distance/nearest-feature queries
        storage/        local filesystem StorageProvider (S3-swappable)
        reports/        report/briefing generator (DB-only, cites sources)
      seeds/       demo data generator
    alembic/       migrations
    tests/         pytest (auth, RBAC, risk engine)
docker/
  docker-compose.yml, init/ (extensions + read-only role bootstrap)
```

## Provider abstractions (section 55 of the spec)

Nothing in this build pretends to talk to a real external system it isn't
actually connected to. Instead, each integration point is a small interface
with a working mock implementation, so a real provider can be swapped in
later without touching call sites:

- **`LLMProvider`** (`services/ai/llm_provider.py`) - `MockLLMProvider` by
  default (deterministic, labeled DEMO output); `OpenAILLMProvider` activates
  automatically when `OPENAI_API_KEY` is set, for text generation only. Voice
  transcription and image analysis stay on the mock implementation regardless
  (see the module docstring) until a real Whisper/vision integration is
  built and tested against real credentials.
- **`StorageProvider`** (`services/storage/local_storage.py`) - local
  filesystem today; swap for an S3-compatible client via `STORAGE_PROVIDER`.
- **`SatelliteProvider`** (`services/satellite/provider.py`) - two implementations:
  `MockSatelliteProvider` (default, no credentials) simulates a before/after
  Sentinel-2-style change-detection pass, deterministic per AOI per day.
  `SentinelHubProvider` (`services/satellite/sentinelhub_provider.py`,
  active once `SENTINELHUB_CLIENT_ID`/`SENTINELHUB_CLIENT_SECRET` are set -
  defaults target the free Copernicus Data Space Ecosystem deployment, see
  `ENVIRONMENT.md`) is a real detector, verified end-to-end against live
  Sentinel-2 data: it queries the Statistical API for mean NDVI over a
  ~1.1km AOI in a baseline window and a current window, and flags a
  significant drop as vegetation loss / exposed soil / excavation depending
  on magnitude - a standard, well-established remote-sensing technique that
  needs no training data or hosted model. It can genuinely report "no
  significant change" rather than always producing a finding. Two things
  learned by testing against the real API and baked into the implementation:
  windows are ~4 months wide, not the ~6 weeks originally assumed, because a
  small AOI in tropical West Africa's rainy season can otherwise have zero
  cloud-free Sentinel-2 passes; and the query explicitly requests
  `mosaickingOrder: leastCC`, since without it the API defaults to the most
  recent scene regardless of cloud cover. Either way, the AOI view in the
  Satellite Monitoring page renders actual current satellite imagery (Esri
  World Imagery, no key required); running a scan persists real
  `satellite_observations` + `ai_detections` rows through the normal
  application code path, which the existing risk engine, map, and audit log
  all react to identically regardless of which provider
  produced them.
- **Notifications** - the `notifications` table models channel + event type;
  no email/SMS/WhatsApp sender is wired up (nothing to fake without real
  credentials).

## AI natural-language → database pipeline

`services/ai/nl_query.py` implements the controlled pipeline required by the
spec: question → regex-based intent detection → one of a fixed set of
hand-written, parametrized SQL queries → executed on the **`naimos_readonly`**
Postgres role (SELECT-only, `statement_timeout` + `LIMIT` enforced) → templated
explanation. There is no code path where AI-generated SQL executes against the
database. Unrecognized questions get an explicit "insufficient verified data"
answer rather than a guess.

## Risk engine

`services/risk/engine.py` computes a 0–100 score from named, point-weighted
signals (recent/historical nearby incidents, nearby AI detections, proximity
to water bodies/protected areas, activity trend) and always returns the full
breakdown alongside the score - there is no opaque score with no explanation.

## Explicitly out of scope for this build

Native mobile app (the field UI is a responsive web app usable on phones
instead - see `apps/web/src/app/(app)/field`), a hosted/trained ML change
classifier (the real `SentinelHubProvider` uses index-thresholding, not a
trained model - see the `SatelliteProvider` note above), a scheduled
ingestion job that scans AOIs automatically rather than on-demand,
Elasticsearch/OpenSearch (Postgres full-text search is used where
search exists), real SMS/WhatsApp/email sending, offline conflict resolution
beyond the `captured_offline`/`synced_at` fields already on `field_reports`,
an exhaustive penetration-style security test suite, and CI/CD configuration.
These match the spec's own instruction not to fake integrations without real
credentials/access, and were called out explicitly in the build plan the user
approved before implementation started.
