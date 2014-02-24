#!/bin/sh

# YAMS database information.
COLLECTD_DB="collectd"
COLLECTD_USER="collectd"
WUI_USER="yams"

# Create the users, don't exit if they already exist.
createuser --no-superuser --no-createrole --login ${COLLECTD_USER}
createuser --no-superuser --no-createrole --login ${WUI_USER}

# Create the database.
createdb --owner=${COLLECTD_USER} collectd "YAMS Data Warehouse"

psql -v ON_ERROR_STOP=1 -d ${COLLECTD_DB} << $$
CREATE EXTENSION hstore;
CREATE EXTENSION json_enhancements;
CREATE EXTENSION plr;

-- Create the schemas.
CREATE SCHEMA AUTHORIZATION ${COLLECTD_USER};
CREATE SCHEMA AUTHORIZATION ${WUI_USER};

GRANT USAGE ON SCHEMA ${COLLECTD_USER} TO ${WUI_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA ${COLLECTD_DB}
GRANT SELECT ON TABLES TO ${WUI_USER};

CREATE OR REPLACE FUNCTION yams.array_add(x DOUBLE PRECISION[],
                                          y DOUBLE PRECISION[])
 RETURNS DOUBLE PRECISION[]
 LANGUAGE plr
AS \$function\$
 return (x + y)
\$function\$;

CREATE OR REPLACE FUNCTION yams.array_subtract(x DOUBLE PRECISION[],
                                               y DOUBLE PRECISION[])
 RETURNS DOUBLE PRECISION[]
 LANGUAGE plr
AS \$function\$
 return (x - y)
\$function\$;

CREATE OR REPLACE FUNCTION yams.array_percentage(x DOUBLE PRECISION[],
                                                 y DOUBLE PRECISION[])
 RETURNS DOUBLE PRECISION[]
 LANGUAGE plr
AS \$function\$
 tmp <- x / y * 100
 # Replace all INF with 0.
 tmp[is.infinite(tmp)] <- 0
 return(tmp)
\$function\$;

CREATE AGGREGATE yams.sum(DOUBLE PRECISION[]) (
 SFUNC = yams.array_add,
 STYPE = DOUBLE PRECISION[],
 INITCOND = '{0}'
);
$$
if [ $? -ne 0 ]; then
	exit 1
fi

psql -v ON_ERROR_STOP=1 -U ${COLLECTD_USER} -d ${COLLECTD_DB} << $$
ALTER DEFAULT PRIVILEGES IN SCHEMA ${COLLECTD_USER}
GRANT SELECT ON TABLES TO ${WUI_USER};
$$
if [ $? -ne 0 ]; then
	exit 1
fi

# Alter user details.
psql -v ON_ERROR_STOP=1 -U ${WUI_USER} -d ${COLLECTD_DB} << $$
ALTER USER ${WUI_USER}
SET search_path TO "\$user",${COLLECTD_USER},public;
$$
if [ $? -ne 0 ]; then
	exit 1
fi

# Create the default tables.
psql -v ON_ERROR_STOP=1 -U ${COLLECTD_USER} -d ${COLLECTD_DB} << $$
BEGIN;
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
  values DOUBLE PRECISION[] NOT NULL,
  meta HSTORE NOT NULL DEFAULT ''
);
COMMIT;
$$
if [ $? -ne 0 ]; then
	exit 1
fi
