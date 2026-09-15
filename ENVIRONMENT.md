# Environment Variables

Copy `.env.example` to `.env` at the repo root (the API reads it via
`apps/api/app/core/config.py`, which looks in both `apps/api/.env` and
`../../.env`). **Never commit `.env`.**

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | |
| `DEMO_MODE` | `true` | Keep `true` unless connecting real operational data |
| `DATABASE_URL` | local Docker Postgres | Full read/write connection |
| `DATABASE_URL_READONLY` | `naimos_readonly` role | Used only by the AI query pipeline |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | empty | Unused - local Docker Postgres is the default; only needed if you switch to Supabase |
| `JWT_SECRET` | placeholder | **Change for anything beyond local dev** |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `OPENAI_API_KEY` | empty | Leave empty to use the built-in mock AI provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `MAPBOX_TOKEN` | empty | Unused - the web app uses token-free MapLibre tiles |
| `SENTINELHUB_CLIENT_ID` / `SENTINELHUB_CLIENT_SECRET` | empty | Leave both empty for the built-in mock satellite provider; set both (OAuth Client Credentials from Dashboards > Sentinel Hub > User settings > OAuth clients) to activate real Sentinel-2 change detection |
| `SENTINELHUB_TOKEN_URL` | CDSE's OAuth endpoint | Override only if using commercial services.sentinel-hub.com instead of the free Copernicus Data Space Ecosystem |
| `SENTINELHUB_STATISTICS_URL` | CDSE's Statistical API endpoint | Same override note as above |
| `STORAGE_PROVIDER` | `local` | `local` \| `s3` (S3 not implemented yet) |
| `STORAGE_BUCKET` | `naimos-evidence` | Used if/when an S3 provider is added |
| `STORAGE_LOCAL_PATH` | `./apps/api/storage` | Where evidence files are written locally |
| `REDIS_URL` | local Docker Redis | Not yet consumed by application code |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Set in `apps/web/.env.local` |

## Never commit

`.env`, `apps/web/.env.local` (contains no secrets by default but keep the
pattern), any credentials, API keys, or service-account files.
