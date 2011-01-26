-- A postgres superuser needs to run this.
CREATE USER collectd;
ALTER USER collectd SET search_path TO collectd,"$user",public;
