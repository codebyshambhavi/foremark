-- Runs once when the Postgres data volume is first created.
-- (To re-run it: `docker compose down -v` deletes local data, then start again.)
--
-- 1. Enable pg_trgm in the main database (used by the Safety Memory Engine for text similarity).
-- 2. Create an isolated database for the automated test suite, with the same extension.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE DATABASE foremark_test;

\connect foremark_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
