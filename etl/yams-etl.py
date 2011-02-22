#!/usr/bin/env python

# This is a simple python script that behaves like an HTTP server only to
# listen to POST requests from collectd's write_html output plugin.  The
# resulting data from collectd is a collection of JSON object but is not 100%
# pure JSON.  Then this script iterates through the POST data to submit the
# individual JSON objects to another HTTP RESTful JSON API.

import sys
from optparse import OptionParser
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_qs
import simplejson as json
from urllib import urlencode
from httplib import HTTPConnection
from threading import Lock, Thread
from time import ctime, gmtime, sleep, time
import random
import re

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

class MyQueue:
    def __init__(self, verbose, stats):
        self.verbose = verbose
        self.stats = stats

        self.count = 0
        self.encount = 0
        self.decount = 0
        self.lock = Lock()
        self.queue = list()
        if stats:
            self.laststat = time()

    def dequeue(self):
        self.lock.acquire()
        try:
            if self.count > 0:
                data = self.queue.pop(0)
                self.count -= 1
                self.decount += 1
                if self.verbose:
                    print 'dequeue: %d' % self.count
            else:
                data = None
        finally:
            self.lock.release()

        if self.stats:
            self.log_stats()
        return data

    def enqueue(self, data):
        self.lock.acquire()
        try:
            self.queue.append(data)
            self.count += 1
            self.encount += 1
            if self.verbose:
                print 'enqueue: %d' % self.count
        finally:
            self.lock.release()

        if self.stats:
            self.log_stats()

    def log_stats(self):
        curtime = time()
        if curtime < self.laststat + 60:
            return
        print '%s %d queued data' % (ctime(), self.count)
        print '%s %0.1f enqueues per min' % (ctime(),
                self.encount / ((curtime - self.laststat) / 60.0))
        print '%s %0.1f dequeues per min' % (ctime(),
                self.decount / ((curtime - self.laststat) / 60.0))
        self.laststat = curtime
        self.encount = 0
        self.decount = 0

class MyThread(Thread):
    def __init__(self, queue, engine, verbose):
        Thread.__init__(self)

        self.queue = queue
        self.engine = engine
        self.verbose = verbose

        self.stopping = False

        self.random = random.Random()
        self.random.seed()

        self.pg_regex = re.compile('^(.*?)-.*$')

    def process(self, data):
        if self.verbose:
            print json.dumps(data, sort_keys=True, indent=4)

        # Since we have a python list of json objects, iterate through the
        # list.

        for datum in data:
            # Build a single INSERT statement per datum since collectd sends
            # data from more than one plugin at a time.

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
            # fails the check constraints on "time" since they WITHOUT TIME
            # ZONE.
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
                # Yeah, postgres doesn't technically support READ UNCOMMITTED
                # so changing the isolation level for performance reasons is
                # pointless, but maybe one day...
                #connection.execute('SET TRANSACTION ISOLATION LEVEL ' \
                        #'READ UNCOMMITTED;')

                # Optimistic behavior, assume the partitioned table exists.  If
                # the INSERT fails, assume the partitioned table doesn't exist
                # and create them as needed.
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
                    # Might be fighting with another thread to create the
                    # table.  If an exception is thrown, just try inserting the
                    # data.
                    try:
                        connection.execute(sql)
                        if plugin == 'cpu':
                            connection.execute( \
                                    'CREATE INDEX ON %s (time, host, ' \
                                    'type_instance, plugin_instance);' % \
                                    partition_table)
                        elif plugin in ['memory', 'vmem']:
                            connection.execute( \
                                    'CREATE INDEX ON %s (time, host, ' \
                                    'type_instance);' % partition_table)
                        else:
                            connection.execute( \
                                    'CREATE INDEX ON %s (time, host);' % \
                                    partition_table)
                        connection.execute('GRANT SELECT ON %s TO yams;' % \
                                partition_table)
                    except Exception, e:
                        connection.execute('ROLLBACK;')
                        # Sleep a few seconds to make sure the table, indexes
                        # and grants complete.
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
        while True:
            data = self.queue.dequeue()
            if data is None:
                if self.stopping:
                    return
                # Sleep up to 5 seconds if there is nothing to do.
                sleep(self.random.randint(0, 5))
            else:
                self.process(json.loads(data))

    def stop(self):
        self.stopping = True

class MyHandler(BaseHTTPRequestHandler):
    queue = None
    verbose = False

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self.do_HEAD()

    def do_POST(self):
        self.do_HEAD()

        length = int(self.headers['content-length'])
        # Don't understand the data sent by collectd.  The resulting
        # datastructure in python is effectively a list of valid json objects,
        # as opposed to a single json object.
        data = self.rfile.read(length)
        self.queue.enqueue(data)

    def log_message(self, format, *args):
        if self.verbose:
            print format % (args)

def main():
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option('-l', '--listener', help='listener port (default 8888)')
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

    listener = 8888
    port = 5984
    uri = '/collectd/'

    verbose = options.verbose
    stats = options.stats

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

    if options.listener:
        listener = int(options.listener)

    if options.workers:
        workers = int(options.workers)
    else:
        workers = 1

    try:
        queue = MyQueue(verbose, stats)

        myh = MyHandler
        myh.queue = queue
        myh.verbose = verbose
        myh.stats = stats

        dsnname = 'postgresql://%s@%s' % (pguser, pghost)
        if pgport:
            dsnname += ':%s' % port
        dsnname += '/%s' % pgdatabase
        engine = create_engine(dsnname, pool_size=pgpool, max_overflow=0)

        i = 0
        print 'ramping up worker threads'
        threads = list()
        while i < workers:
            threads.append(MyThread(queue, engine, verbose))
            threads[i].start()
            i += 1
        print 'worker threads ramped up'

        httpserver = HTTPServer(('', listener), myh)
        print 'listener started'
        httpserver.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        for thread in threads:
            thread.stop()
        httpserver.socket.close()

if __name__ == '__main__':
    main()
