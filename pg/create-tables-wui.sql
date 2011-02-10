
-- Put all tables for WUI into a separate schema from public.
SET search_path TO yams;

CREATE TABLE systems (
  name VARCHAR(255) UNIQUE NOT NULL,
  lprocs SMALLINT NOT NULL
);
