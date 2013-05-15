# YAMS - Yet Another Monitoring System

YAMS is designed to be a long term trending system capable of handling large
volumes of data.  It leverages other open source software such as collectd and
Postgres.  There are four main components: SUM, ETL, DW and WUI.

See INSTALL.md for installation help, and the doc directory for specific use
cases.

## System Under Monitor (SUM)

The SUM is a system that is monitored by collectd.

## Extract, Load, Transform (ETL)

The ETL is a custom built application that is specifically designed to
transform collectd JSON formatted data from the collectd write_http module and
load it into a relational database management system.  The custon application
is suite of software consisting of a FastCGI C program, an ETL C program, Web
server, and Redis.

## Data Warehouse (DW)

The DW is the PostgreSQL relational database management system.

## Web User Interface (WUI)

The WUI is an application built on Pyramid using Flotr2.

## Minimum software versions:

* collectd 5.2
* fcgi 2.4
* hiredis 0.9.2
* json-c 0.10
* nginx 1.2
* PostgreSQL 9.2 with json_enhancements extension
* Pyramid 1.4
* Redis 2.2
* spawn-fcgi 1.6

A script is provided for Vagrant http://www.vagrantup.com that will build a
working system with YAMS running on it.
