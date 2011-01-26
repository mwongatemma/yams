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
from time import sleep
import random

from sqlalchemy import create_engine

class MyQueue:
    def __init__(self, verbose):
        self.verbose = verbose

        self.count = 0
        self.lock = Lock()
        self.queue = list()

    def dequeue(self):
        self.lock.acquire()
        try:
            if self.count > 0:
                data = self.queue.pop(0)
                self.count -= 1
                if self.verbose:
                    print 'dequeue: %d' % self.count
            else:
                data = None
        finally:
            self.lock.release()
        return data

    def enqueue(self, data):
        self.lock.acquire()
        try:
            self.queue.append(data)
            self.count += 1
            if self.verbose:
                print 'enqueue: %d' % self.count
        finally:
            self.lock.release()

class MyThread(Thread):
    def __init__(self, queue, connection, verbose):
        Thread.__init__(self)

        self.queue = queue
        self.connection = connection
        self.verbose = verbose

        self.stopping = False

        self.random = random.Random()
        self.random.seed()

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
                meta_columns = ', database, schemaname, tablename, indexname'

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

            # Append meta data value if appropriate.
            meta_values = ''
            if plugin == 'postgresql':
                if 'schema' in datum:
                    schemaname = datum['schema']
                else:
                    schemaname = 'NULL'
                if 'table' in datum:
                    tablename = datum['table']
                else:
                    tablename = 'NULL'
                if 'index' in datum:
                    indexname = datum['index']
                else:
                    indexname = 'NULL'
                meta_values = ', \'%s\', \'%s\', \'%s\', \'%s\'' % \
                        (datum['database'], schemaname, tablename,
                         indexname)

            # Convert empty strings to NULL.
            if datum['plugin_instance'] == '':
                plugin_instance = 'NULL'
            else:
                plugin_instance = '\'%s\'' % datum['plugin_instance']
                
            if datum['type_instance'] == '':
                type_instance = 'NULL'
            else:
                type_instance = '\'%s\'' % datum['type_instance']

            # TODO: Is there a way to parameterize the values as opposed to
            # building it 100% on the fly?
            sql = \
"""INSERT INTO vl_%s (time, interval, host, plugin, plugin_instance, type,
                      type_instance, dsnames, dstypes, values%s)
VALUES (TIMESTAMP WITH TIME ZONE \'epoch\' + %s * INTERVAL \'1 second\', %s, \
        \'%s\', \'%s\', %s, \'%s\', %s, \'{%s}\', \'{%s}\', \
        \'{%s}\'%s);""" % (plugin, meta_columns, datum['time'],
                    datum['interval'], datum['host'], plugin,
                    plugin_instance, datum['type'],
                    type_instance, ', '.join(dsnames),
                    ', '.join(dstypes), ', '.join(values), meta_values)
            if self.verbose:
                print sql
            try:
                self.connection.execute('BEGIN;')
                # Yeah, postgres doesn't technically support READ UNCOMMITTED
                # but maybe one day...
                #self.connection.execute('SET TRANSACTION ISOLATION LEVEL ' \
                        #'READ UNCOMMITTED;')
                self.connection.execute(sql)
                self.connection.execute('COMMIT;')
            except Exception, e:
                self.connection.execute('ROLLBACK;')
                print e
                sys.exit(1)

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

def main():
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option('-l', '--listener', help='listener port (default 8888)')
    parser.add_option('--pgdatabase',
            help='postgres database (default collectd')
    parser.add_option('--pghost', help='postgres host')
    parser.add_option('--pgpool',
            help='postgres connection pool size (default 10)')
    parser.add_option('--pgport', help='postgres port (default 5432)')
    parser.add_option('--pguser', help='postgres user (default collectd)')
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='verbose output')
    parser.add_option('-w', '--workers', help='number of threads (default 1)')
    options, args = parser.parse_args()

    listener = 8888
    port = 5984
    uri = '/collectd/'

    verbose = options.verbose

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
        listener = options.listener

    if options.workers:
        workers = int(options.workers)
    else:
        workers = 1

    try:
        queue = MyQueue(verbose)

        myh = MyHandler
        myh.queue = queue

        dsnname = 'postgresql://%s@%s' % (pguser, pghost)
        if pgport:
            dsnname += ':%s' % port
        dsnname += '/%s' % pgdatabase
        engine = create_engine(dsnname, pool_size=pgpool, max_overflow=0)
        connection = engine.connect()

        i = 0
        print 'ramping up worker threads'
        threads = list()
        while i < workers:
            threads.append(MyThread(queue, connection, verbose))
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
