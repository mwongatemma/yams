#!/bin/sh

# PostgreSQL super user database information.
PG_SUPERUSER="postgres"
PG_DB="postgres"

# YAMS database information.
COLLECTD_DB="collectd"
COLLECTD_USER="collectd"
WUI_USER="yams"
COLLECTD_TBLSPACE="collectd"

# Create the users, don't exit if they already exist.
psql -U ${PG_SUPERUSER} -d ${PG_DB} -c "CREATE USER ${COLLECTD_USER};"
psql -U ${PG_SUPERUSER} -d ${PG_DB} -c "CREATE USER ${WUI_USER};"

# Create the database.
psql -U ${PG_SUPERUSER} -d ${PG_DB} \
		-c "CREATE DATABASE ${COLLECTD_DB} WITH OWNER ${COLLECTD_USER};" \
		|| exit 1

psql -U ${PG_SUPERUSER} -d ${COLLECTD_DB} \
		-c "CREATE EXTENSION hstore;" || exit 1

# Create the schemas.
psql -U ${PG_SUPERUSER} -d ${COLLECTD_DB} \
		-c "CREATE SCHEMA AUTHORIZATION ${COLLECTD_USER};" || exit 1
psql -U ${PG_SUPERUSER} -d ${COLLECTD_DB} \
		-c "CREATE SCHEMA AUTHORIZATION ${WUI_USER};" || exit 1

psql -U ${COLLECTD_USER} -d ${COLLECTD_DB} \
		-c "GRANT USAGE ON SCHEMA ${COLLECTD_USER} TO ${WUI_USER}" || exit 1
psql -U ${COLLECTD_USER} -d ${COLLECTD_DB} \
		-c "ALTER DEFAULT PRIVILEGES IN SCHEMA ${COLLECTD_DB}
			GRANT SELECT ON TABLES TO ${WUI_USER};" || exit 1

# Alter user details.
psql -U ${COLLECTD_USER} -d ${COLLECTD_DB} \
		-c "ALTER USER ${COLLECTD_USER}
			SET default_tablespace TO '${COLLECTD_TBLSPACE}';"
psql -U ${WUI_USER} -d ${COLLECTD_DB} \
		-c "ALTER USER ${WUI_USER}
			SET search_path TO \"\$user\",${COLLECTD_USER},public;" || exit 1

# Create the default tables.
psql -U ${COLLECTD_USER} -d ${COLLECTD_DB} << __EOF__
BEGIN;
\i create-tables-collectd.sql
COMMIT;
__EOF__
