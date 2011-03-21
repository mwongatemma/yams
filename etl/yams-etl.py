#!/usr/bin/env python

# This is a simple python script that pulls collectd-formatted JSON data from
# Redis.  Then this script iterates through the data to insert the data into
# the data warehouse.

import sys
import signal
from optparse import OptionParser
from redis import Redis
import simplejson as json
from threading import Lock, Thread
from time import ctime, gmtime, sleep, time
import random
import re

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

class Stats:
    def __init__(self):
        self.rlock = Lock()
        self.plock = Lock()

        self.rcount = 0
        self.pcount = 0

    def addp(self):
        self.plock.acquire()
        try:
            self.pcount += 1
        finally:
            self.plock.release()

    def addr(self):
        self.rlock.acquire()
        try:
            self.rcount += 1
        finally:
            self.rlock.release()

class StatsThread(Thread):
    def __init__(self, stats):
        Thread.__init__(self)
        self.stats = stats

        self.stopping = False

    def run(self):
        while not self.stopping:
            print '%s %d (redis) %d (pg) per minute' % (ctime(),
                    self.stats.rcount, self.stats.pcount)
            self.stats.rcount = 0
            self.stats.pcount = 0
            sleep(60)

    def stop(self):
        self.stopping = True

class MyThread(Thread):
    def __init__(self, redis_server, redis_port, redis_key, engine, stats,
                 stats_counter, verbose):
        Thread.__init__(self)

        self.redis_server = redis_server
        self.redis_port = redis_port
        self.redis_key = redis_key

        self.engine = engine

        self.stats = stats
        self.stats_counter = stats_counter

        self.verbose = verbose

        self.stopping = False

        self.random = random.Random()
        self.random.seed()

        self.pg_regex = re.compile('^(.*?)-.*$')

        self.redis = Redis(host=redis_server, port=redis_port)

    def process(self, data):
        # The data coming out of redis is a string.  It needs to be evaluated
        # back into a list of dicts.
        for datum in eval(data[1:-1]):
            if self.verbose:
                print json.dumps(datum, sort_keys=True, indent=4)
            self.load(datum)
            if (self.stats):
                self.stats_counter.addp()

    def load(self, datum):
        # Build a single INSERT statement per datum since collectd sends data
        # from more than one plugin at a time.

        plugin = datum['plugin']

        # Depending on the plugin there may be meta data to capture.
        meta_columns = ''
        if plugin == 'postgresql':
            meta_columns = ', database, schemaname, tablename, ' \
                           'indexname, metric'

        # Convert json arrays into postgres arrays.
        dsnames = list()
        dstypes = list()
        values = list()
        for val in datum['dsnames']:
            dsnames.append('"%s"' % val)
        for val in datum['dstypes']:
            dstypes.append('"%s"' % val)
        for val in datum['values']:
            values.append('%g' % val)

        ts = gmtime(datum['time'])
        partition_table = 'vl_%s_%d%02d%02d' % (plugin, ts.tm_year,
                                                ts.tm_mon, ts.tm_mday)

        # Convert empty strings to NULL.
        if datum['plugin_instance'] == '':
            plugin_instance = 'NULL'
        else:
            plugin_instance = '\'%s\'' % datum['plugin_instance']

        if datum['type_instance'] == '':
            type_instance = 'NULL'
        else:
            type_instance = '\'%s\'' % datum['type_instance']

            if plugin == 'postgresql':
                # PostgreSQL data specific.
                match = re.match(self.pg_regex, datum['type_instance'])
                metric = match.group(1)
                partition_table += '_'
                partition_table += metric

        # Append meta data value if appropriate.
        meta_values = ''
        if plugin == 'postgresql':
            if 'schema' in datum:
                schemaname = '\'%s\'' % datum['schema']
            else:
                schemaname = 'NULL'
            if 'table' in datum:
                tablename = '\'%s\'' % datum['table']
            else:
                tablename = 'NULL'
            if 'index' in datum:
                indexname = '\'%s\'' % datum['index']
            else:
                indexname = 'NULL'
            meta_values = ', \'%s\', %s, %s, %s, \'%s\'' % \
                    (datum['database'], schemaname, tablename,
                     indexname, metric)

        # TODO: Is there a way to parameterize the values as opposed to
        # building it 100% on the fly?

        # Use WITH TIME ZONE otherwise the time is adjusted to GMT and will
        # fails the check constraints on "time" since they WITHOUT TIME ZONE.
        sql = \
"""INSERT INTO %s (time, interval, host, plugin, plugin_instance, type,
                      type_instance, dsnames, dstypes, values%s)
VALUES (TIMESTAMP WITH TIME ZONE \'EPOCH\' + %s * INTERVAL \'1 SECOND\',
        %s, \'%s\', \'%s\', %s, \'%s\', %s, \'{%s}\', \'{%s}\',
        \'{%s}\'%s);""" % (partition_table, meta_columns, datum['time'],
                    datum['interval'], datum['host'], plugin,
                    plugin_instance, datum['type'],
                    type_instance, ', '.join(dsnames),
                    ', '.join(dstypes), ', '.join(values), meta_values)
        if self.verbose:
            print sql
        connection = self.engine.connect()
        try:
            connection.execute('BEGIN;')
            # Yeah, postgres doesn't technically support READ UNCOMMITTED so
            # changing the isolation level for performance reasons is
            # pointless, but maybe one day...
            #connection.execute('SET TRANSACTION ISOLATION LEVEL ' \
                    #'READ UNCOMMITTED;')

            # Optimistic behavior, assume the partitioned table exists.  If the
            # INSERT fails, assume the partitioned table doesn't exist and
            # create them as needed.
            try:
                connection.execute(sql)
            except ProgrammingError, exc:
                # Create the partitioned table if it doesn't exist.  Tables
                # are partitioned by day.

                # FIXME: Why isn't this a NoSuchTableError when the INSERT
                # fails?

                connection.execute('ROLLBACK;')

                connection.execute('BEGIN;')

                # Calculate dates for the CHECK constraint.
                result = connection.execute('SELECT ((TIMESTAMP WITH ' \
                        'TIME ZONE \'EPOCH\' + %s * INTERVAL ' \
                        '\'1 SECOND\') AT TIME ZONE \'UTC\')::DATE;' % \
                        datum['time'])
                startdate = result.scalar()

                result = connection.execute('SELECT \'%s\'::DATE + ' \
                        'INTERVAL \'1 DAY\';' % startdate)
                enddate = result.scalar()

                if plugin == 'postgresql':
                    # PostgreSQL data specific.
                    extra_check = 'CHECK (metric = \'%s\'),' % (metric)
                else:
                    extra_check = ''

                sql = \
"""CREATE TABLE %s (
    %s
    CHECK (time >= '%s'::TIMESTAMP AT TIME ZONE 'UTC'
       AND time < '%s'::TIMESTAMP AT TIME ZONE 'UTC')
) INHERITS(vl_%s);""" % (partition_table, extra_check, startdate, enddate,
                         plugin)
                # Might be fighting with another thread to create the table.
                # If an exception is thrown, just try inserting the data.
                try:
                    connection.execute(sql)
                    if plugin == 'cpu':
                        connection.execute('CREATE INDEX ON %s (time, host, ' \
                                'type_instance, plugin_instance);' % \
                                partition_table)
                    elif plugin in ['memory', 'vmem']:
                        connection.execute('CREATE INDEX ON %s (time, host, ' \
                                'type_instance);' % partition_table)
                    else:
                        connection.execute( \
                                'CREATE INDEX ON %s (time, host);' % \
                                partition_table)
                    connection.execute('GRANT SELECT ON %s TO yams;' % \
                            partition_table)
                except Exception, e:
                    connection.execute('ROLLBACK;')
                    # Sleep a few seconds to make sure the table, indexes and
                    # grants complete.
                    sleep(3)
                    connection.execute('BEGIN;')
                # Try the INSERT again.
                connection.execute(sql)
            except Exception, e:
                raise
            connection.execute('COMMIT;')
        except Exception, e:
            connection.execute('ROLLBACK;')
            print e
        connection.close()

    def run(self):
        while not self.stopping:
            # The data returned by redist is a 2 element list, first element
            # has the redist key and the second element is the data.
            self.process(self.redis.blpop(self.redis_key)[1])
            if (self.stats):
                self.stats_counter.addr()

    def stop(self):
        self.stopping = True

threads = list()
stats_thread = None

def signal_handler(signal, frame):
    if stats_thread is not None:
        stats_thread.stop()
    for thread in threads:
        thread.stop()
    sys.exit(0);

def main():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('--redisserver',
            help='redis hostname (default localhost)')
    parser.add_option('--redisport', help='redis server port (default 6379)')
    parser.add_option('--rediskey', help='redis key (default yamsetl)')
    parser.add_option('--pgdatabase',
            help='postgres database (default collectd)')
    parser.add_option('--pghost', help='postgres host')
    parser.add_option('--pgpool',
            help='postgres connection pool size (default 10)')
    parser.add_option('--pgport', help='postgres port (default 5432)')
    parser.add_option('--pguser', help='postgres user (default collectd)')
    parser.add_option('-s', '--stats', action='store_true', default=False,
                      help='output queue statistics')
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='verbose output')
    parser.add_option('-w', '--workers', help='number of threads (default 1)')
    options, args = parser.parse_args()

    verbose = options.verbose
    stats = options.stats

    if options.workers:
        workers = int(options.workers)
    else:
        workers = 1

    if options.redisserver:
        redis_server = options.redisserver
    else:
        redis_server = 'localhost'

    if options.redisport:
        redis_port = int(options.redisport)
    else:
        redis_port = 6379

    if options.rediskey:
        redis_key = options.rediskey
    else:
        redis_key = 'yamsetl'

    if not options.pghost:
        parser.error('database hostname must be specified')
    else:
        pghost = options.pghost

    if options.pgpool:
        pgpool = int(options.pgpool)
    else:
        pgpool = 10

    if options.pgport:
        pgport = options.pgport
    else:
        pgport = None

    if options.pguser:
        pguser = options.pguser
    else:
        pguser = 'collectd'

    if options.pgdatabase:
        pgdatabase = options.pgdatabase
    else:
        pgdatabase = 'collectd'

    dsnname = 'postgresql://%s@%s' % (pguser, pghost)
    if pgport:
        dsnname += ':%s' % port
    dsnname += '/%s' % pgdatabase
    engine = create_engine(dsnname, pool_size=pgpool, max_overflow=0)

    i = 0
    print 'ramping up worker threads'
    if stats:
        stats_counter = Stats()
        stats_thread = StatsThread(stats_counter)
        stats_thread.start()
    else:
        stats_counter = None

    while i < workers:
        threads.append(MyThread(redis_server, redis_port, redis_key, engine,
                                stats, stats_counter, verbose))
        threads[i].start()
        i += 1
    print 'worker threads ramped up'

    signal.signal(signal.SIGINT, signal_handler)
    print 'Press Ctrl+C to exit'
    signal.pause()

if __name__ == '__main__':
    main()
