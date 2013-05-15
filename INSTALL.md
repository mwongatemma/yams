# Installation

It isn't a requirement to install some of these components from source.

## PostgreSQL

PostgreSQL is available from http://www.postgresql.org/

The json_exhancement extension can be installed from PGXN if using v9.2.  This
extension is not needed for later versions.  Instructions for how to install
extensions from PGXN are on the FAQ.  http://pgxn.org/faq/

## Redis

Redis is available from http://redis.io/

YAMS was proofed against v2.2 but versions as early as 1.2, or newer versions,
are likely to be compatible.

## Web server

nginx http://nginx.org/ or lighttpd http://www.lighttpd.net/ are know to work.
Any web servers with a support for FastCGI C programs should also work.

If nginx is used then something like spawn-fcgi
http://redmine.lighttpd.net/projects/spawn-fcgi is required to run the FastCGI
C program.

## YAMS ETL programs

The following libraries are required in order build the ETL programs in the etl directory:
* fcgi 2.4 http://www.fastcgi.com
* hiredis 0.9.2 https://github.com/redis/hiredis
* json-c 0.10 https://github.com/json-c/json-c/wiki

The two ETL program can be built and installed by the following commands:

    cd etl
    make
    make install

## YAMS WUI

The Pyramid application can be installed by the following commands:

    cd yams-wui
    python setup.py install

# Configuration

## PostgreSQL

A script is provided to create two users, yams and collectd, in
pg/create-database.sh.  This script needs to be run by a PostgreSQL superuser.
The user yams is used for the Web user interface and the user collectd is used
by the ETL process.  

## Web Server

Here are a couple of examples for a couple of different Web servers.

### nginx

The nginx.conf file needs to set up an end point to redirect HTTP requests to
the FastCGI C program.  Here is an example for setting up the path to /yams/ to
redirect for a given virtual host:

        location /yams/ {
            include        fastcgi_params;
            fastcgi_pass   127.0.0.1:9000;
        }

### lighttpd

Here is an example for setting up a interface to the YAMS FastCGI C program in
lighttpd.

    server.modules += ( "mod_fastcgi" )

    fastcgi.server = ( "/yams/" =>
                       ( "etl" =>
                         (
                           "socket" => "/var/run/fastcgi.yams-etl.socket",
                           "bin-path" => "/usr/local/bin/yams-etl-fcgi",
                           "bin-environment" =>
                           (
                             "REDIS_SERVER" => "localhost",
                             "REDIS_PORT" => "6379",
                             "REDIS_KEY" => "yamsetl"
                           ),
                           "check-local" => "disable",
                           "max-procs" => 1,
                         )
                       )
                     )

## collectd

collectd must use the write_http plugin to submit data to YAMS.  Here is an
example for configuring the plugin to match the examples in the Web server
configuration section:

    <Plugin write_http>
            <URL "http://localhost/yams/">
                    Format "JSON"
            </URL>
    </Plugin>

# Starting up services

## spawn-fcgi

If using a Web server like nginx that does not run FastCGI programs itself,
something like spawn-fcgi is needed to start the FactCGI C program externally:

    spawn-fcgi -p 9000 /usr/local/bin/yams-etl-fcgi

## yams-etl

The YAMS ETL program needs to be started in order to take the collectd data
stored in Redis and insert it into the database:

    yams-etl --pghost localhost --pgdatabase collectd --pgusername collectd

## YAMS WUI

### Standalone

The Pyramid application can be deployed with many Web servers.  It can also be
started using pserve, which is provided by Pyramid.  Here is an example of
using virtualenvwrapper http://virtualenvwrapper.readthedocs.org/en/latest/ to
set up a virtual environment.

    source /usr/local/bin/virtualenvwrapper.sh
    mkvirtualenv yams
    cd yams-wui
    python setup.py install
    pserve production.ini

### Apache

Here is an example for an Apache config with mod_wsgi enabled that will put the
YAMS WUI at the root:

	    WSGIScriptAlias / /usr/local/bin/pyramid.wsgi
	    <Directory /usr/local/src/yams/yams-wui>
		    WSGIProcessGroup pyramid
		    Order allow,deny
		    Allow from all
	    </Directory>
