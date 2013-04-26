-- This composite type is for helping convert json to hstore.
CREATE TYPE json2hstore AS (
  key TEXT,
  value TEXT
);

-- Parent table
CREATE TABLE value_list (
  time TIMESTAMP WITH TIME ZONE NOT NULL,
  interval INTEGER NOT NULL,
  host VARCHAR(64) NOT NULL,
  plugin VARCHAR(64) NOT NULL,
  plugin_instance VARCHAR(64),
  type VARCHAR(64) NOT NULL,
  type_instance VARCHAR(64),
  dsnames VARCHAR(512)[] NOT NULL,
  dstypes VARCHAR(8)[] NOT NULL,
  values NUMERIC[] NOT NULL,
  meta HSTORE NOT NULL DEFAULT ''
);
