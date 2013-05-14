# Monitoring PostgreSQL

This document has examples for how to monitoring most of the statistics that 
PostgreSQL can provide.  

## Patching collectd

In order to query PostgreSQL statistics better, there is a proposed patch for
v5.2 to annotate collectd data with metadata from data queried from a database:
http://mailman.verplant.org/pipermail/collectd/2013-May/005788.html

Having this patch allows data to be queried by database, schema, table, or 
index names more easily.  If any of this metadata is collectd then YAMS expects
the metadata keys to be database, schema, table, and index, respectively.  The
metadata key is set based on the column name.

The patch is not required and if it is not used then the MetadataFrom fields in
the examples below will not be recognized.

## Database Statistics

Create a custom collectd type for metrics from the pg_stat_database table.

    database_stats numbackends:GAUGE:0:u, xact_rollback:COUNTER:0:u, xact_commit:COUNTER:0:u, blks_read:COUNTER:0:u, blks_hit:COUNTER:0:u, tup_returned:COUNTER:0:u, tup_fetched:COUNTER:0:u, tup_inserted:COUNTER:0:u, tup_updated:COUNTER:0:u, tup_deleted:COUNTER:0:u 

Example of how to configure the collectd postgresql plugin <Query> block:

        <Query stat_database>
            Statement " \
    SELECT datname AS database, numbackends, xact_commit, xact_rollback, \
           blks_read, blks_hit, tup_returned, tup_fetched, tup_inserted, \
           tup_updated, tup_deleted \
    FROM pg_stat_database;"
            <Result>
                Type database_stats
                InstancePrefix "database_stats"
                InstancesFrom "database"
                ValuesFrom "numbackends" "xact_rollback" "xact_commit" "blks_read" "blks_hit" "tup_returned" "tup_fetched" "tup_inserted" "tup_updated" "tup_deleted"
                MetadataFrom "database"
            </Result>
        </Query>

## Table Statistics

Create a custom collectd type for metrics from the pg_stat_all_tables and
pg_statio_all_tables tables.

    table_stats seq_scan:COUNTER:0:U seq_tup_read:COUNTER:0:U, idx_scan:COUNTER:0:U, idx_tup_fetch:COUNTER:0:U, n_tup_ins:COUNTER:0:U, n_tup_upd:COUNTER:0:U, n_tup_del:COUNTER:0:U, n_tup_hot_upd:COUNTER:0:U, n_live_tup:COUNTER:0:U, n_dead_tup:COUNTER:0:U, heap_blks_read:COUNTER:0:U, heap_blks_hit:COUNTER:0:U, idx_blks_read:COUNTER:0:U, idx_blks_hit:COUNTER:0:U, toast_blks_read:COUNTER:0:U, toast_blks_hit:COUNTER:0:U, tidx_blks_read:COUNTER:0:U, tidx_blks_hit:COUNTER:0:U

Example of how to configure the collectd postgresql plugin <Query> block:

        <Query stat_table>
            Statement "\
    SELECT 1::TEXT AS database, a.schemaname AS schema, a.relname AS table, \
           seq_scan, seq_tup_read, COALESCE(idx_scan, 0) AS idx_scan, \
           COALESCE(idx_tup_fetch, 0) AS idx_tup_fetch, n_tup_ins, n_tup_upd, \
           n_tup_del, n_tup_hot_upd, n_live_tup, n_dead_tup, heap_blks_read, \
           heap_blks_hit, COALESCE(idx_blks_read, 0) AS idx_blks_read, \
           COALESCE(idx_blks_hit, 0) AS idx_blks_hit, \
           COALESCE(toast_blks_read, 0) AS toast_blks_read, \
           COALESCE(toast_blks_hit, 0) AS toast_blks_hit, \
               COALESCE(tidx_blks_read, 0) AS tidx_blks_read, \
           COALESCE(tidx_blks_hit, 0) AS tidx_blks_hit \
    FROM pg_statio_all_tables a, pg_stat_all_tables b \
    WHERE a.relid = b.relid;"
            Param database
            <Result>
                Type table_stats
                InstancePrefix "table_stats"
                InstancesFrom "table" "schema" "database"
                ValuesFrom "seq_scan" "seq_tup_read" "idx_scan" "idx_tup_fetch" "n_tup_ins" "n_tup_upd" "n_tup_del" "n_tup_hot_upd" "n_live_tup" "n_dead_tup" "heap_blks_read" "heap_blks_hit" "idx_blks_read" "idx_blks_hit" "toast_blks_read" "toast_blks_hit" "tidx_blks_read" "tidx_blks_hit"
                MetadataFrom "table" "schema" "database"
            </Result>
        </Query>

## Index Statistics

Create a custom collectd type for metrics from the pg_stat_all_indexes and
pg_statio_all_indexes tables.

    index_stats idx_scan:COUNTER:0:U idx_tup_read:COUNTER:0:U idx_tup_fetch:COUNTER:0:U idx_blks_read:COUNTER:0:U idx_blks_hit:COUNTER:0:U

Example of how to configure the collectd postgresql plugin <Query> block:

        <Query stat_index>
            Statement "\
    SELECT $1::TEXT AS database, a.schemaname AS schema, a.relname AS table, \
           a.indexrelname AS index, idx_scan, idx_tup_read, idx_tup_fetch, \
           idx_blks_read, idx_blks_hit \
    FROM pg_stat_all_indexes a, pg_statio_all_indexes b \
    WHERE a.indexrelid = b.indexrelid;"
            Param database
            <Result>
                Type index_stats
                InstancePrefix "index_stats"
                InstancesFrom "index" "table" "schema" "database"
                ValuesFrom "idx_scan" "idx_tup_read" "idx_tup_fetch" "idx_blks_read" "idx_blks_hit"
                MetadataFrom "index" "table" "schema" "database"
            </Result>
        </Query>

## Table Sizes

Here is example for getting the table sizes.  Create a custom collectd type:

    table_sizes total_relation_size:GAUGE:0:U, table_size:GAUGE:0:U, indexes_size:GAUGE:0:U

Example of how to configure the collectd postgresql plugin <Query> block:

        <Query table_sizes>
            Statement "\
    SELECT $1::TEXT AS database, schemaname AS schema, tablename AS table, \
           pg_total_relation_size(schemaname || '.' || tablename) \
               AS total_relation_size, \
           pg_table_size(schemaname || '.' || tablename) \
               AS table_size, \
           pg_indexes_size(schemaname || '.' || tablename) \
               AS indexes_size \
    FROM pg_tables;"
            Param database
            <Result>
                Type table_sizes
                InstancePrefix "table_sizes"
                InstancesFrom "table" "schema" "database"
                ValuesFrom "total_relation_size" "table_size" "indexes_size"
                MetadataFrom "table" "schema" "database"
            </Result>
        </Query>
