-- Runs automatically on first container start (docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- fuzzy/full-text search support

-- Read-only role used exclusively by the AI natural-language query pipeline
-- (see services/ai/nl_query.py). This role is granted SELECT only, after the
-- application has run its migrations, via scripts/grant_readonly.sql.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'naimos_readonly') THEN
    CREATE ROLE naimos_readonly WITH LOGIN PASSWORD 'naimos_readonly_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE naimos TO naimos_readonly;
