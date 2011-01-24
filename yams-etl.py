#!/usr/bin/env python

# This is a simple python script that behaves like an HTTP server only to
# listen to POST requests from collectd's write_html output plugin.  The
# resulting data from collectd is a collection of JSON object but is not 100%
# pure JSON.  Then this script iterates through the POST data to submit the
# individual JSON objects to another HTTP RESTful JSON API.

from optparse import OptionParser
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_qs
import simplejson as json
from urllib import urlencode
from httplib import HTTPConnection

class MyHandler(BaseHTTPRequestHandler):
    hostname = None
    port = None
    uri = None
    verbose = None

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

        jdata = json.loads(data)
        if self.verbose:
            print json.dumps(jdata, sort_keys=True, indent=4)
        headers = {'Content-Type': 'application/json'}

        conn = HTTPConnection(self.hostname, self.port)
        # Since we have a python list of json objects, iterate through the list
        # and send each python object individually.
        for datum in jdata:
            params = json.dumps(datum)
            if self.verbose:
                conn.set_debuglevel(1)
            conn.request('POST', self.uri, params, headers)
            # Must read the response before reusing the connection to send
            # another request.
            response = conn.getresponse()
            response.read()
        conn.close()

def main():
    parser = OptionParser(usage="usage: %prog [options]")
    parser.add_option('-l', '--listener', help='listener port (default 8888)')
    parser.add_option('-p', '--port', help='http server port (default 5984)')
    parser.add_option('-s', '--server', help='http server hostname')
    parser.add_option('-u', '--uri', help='uri (default /collectd/)')
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='verbose output')
    options, args = parser.parse_args()

    listener = 8888
    port = 5984
    uri = '/collectd/'

    verbose = options.verbose

    if not options.server:
        parser.error('a hostname must be specified')
    else:
        hostname = options.server

    if options.port:
        port = options.port

    if options.uri:
        uri = options.uri

    if options.listener:
        listener = options.listener

    try:
        myh = MyHandler
        myh.hostname = hostname
        myh.port = port
        myh.uri = uri
        myh.verbose = verbose

        httpserver = HTTPServer(('', listener), myh)
        print 'yams test listener started'
        httpserver.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        httpserver.socket.close()

if __name__ == '__main__':
    main()
