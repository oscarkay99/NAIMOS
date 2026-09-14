-- Run after migrations: grants the naimos_readonly role SELECT-only access,
-- used exclusively by the AI natural-language query pipeline
-- (app/services/ai/nl_query.py) so no AI-mediated query can ever mutate data.
GRANT USAGE ON SCHEMA public TO naimos_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO naimos_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO naimos_readonly;
