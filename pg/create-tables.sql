-- Run as collectd user.

-- Put all tables into a separate schema from public.
SET search_path TO collectd;

-- Parent table
CREATE TABLE value_list (
  time TIMESTAMP NOT NULL,
  interval INTEGER NOT NULL,
  host VARCHAR(64) NOT NULL,
  plugin VARCHAR(64) NOT NULL,
  plugin_instance VARCHAR(64),
  type VARCHAR(64) NOT NULL,
  type_instance VARCHAR(64),
  dsnames VARCHAR(512)[] NOT NULL,
  dstypes VARCHAR(8)[] NOT NULL,
  values NUMERIC[] NOT NULL
);

-- Partition by creating a child table per collectd plugin.

CREATE TABLE vl_apache (
  CHECK (plugin = 'apache')
) INHERITS(value_list);
CREATE TABLE vl_apcups (
  CHECK (plugin = 'apcups')
) INHERITS(value_list);
CREATE TABLE vl_apple_sensors (
  CHECK (plugin = 'apple_sensors')
) INHERITS(value_list);
CREATE TABLE vl_ascent (
  CHECK (plugin = 'ascent')
) INHERITS(value_list);
CREATE TABLE vl_battery (
  CHECK (plugin = 'battery')
) INHERITS(value_list);
CREATE TABLE vl_bind (
  CHECK (plugin = 'bind')
) INHERITS(value_list);
CREATE TABLE vl_conntrack (
  CHECK (plugin = 'conntrack')
) INHERITS(value_list);
CREATE TABLE vl_contextswitch (
  CHECK (plugin = 'contextswitch')
) INHERITS(value_list);
CREATE TABLE vl_cpu (
  CHECK (plugin = 'cpu')
) INHERITS (value_list);
CREATE TABLE vl_cpufreq (
  CHECK (plugin = 'cpufreq')
) INHERITS(value_list);
CREATE TABLE vl_curl (
  CHECK (plugin = 'curl')
) INHERITS(value_list);
CREATE TABLE vl_curl_json (
  CHECK (plugin = 'json')
) INHERITS(value_list);
CREATE TABLE vl_curl_xml (
  CHECK (plugin = 'curl_xml')
) INHERITS(value_list);
CREATE TABLE vl_dbi (
  CHECK (plugin = 'dbi')
) INHERITS(value_list);
CREATE TABLE vl_df (
  CHECK (plugin = 'df')
) INHERITS(value_list);
CREATE TABLE vl_disk (
  CHECK (plugin = 'disk')
) INHERITS(value_list);
CREATE TABLE vl_dns (
  CHECK (plugin = 'dns')
) INHERITS(value_list);
CREATE TABLE vl_email (
  CHECK (plugin = 'email')
) INHERITS(value_list);
CREATE TABLE vl_entropy (
  CHECK (plugin = 'entropy')
) INHERITS(value_list);
CREATE TABLE vl_exec (
  CHECK (plugin = 'exec')
) INHERITS(value_list);
CREATE TABLE vl_filecount (
  CHECK (plugin = 'filecount')
) INHERITS(value_list);
CREATE TABLE vl_fscache (
  CHECK (plugin = 'fscache')
) INHERITS(value_list);
CREATE TABLE vl_gmond (
  CHECK (plugin = 'gmond')
) INHERITS(value_list);
CREATE TABLE vl_hddtemp (
  CHECK (plugin = 'hddtemp')
) INHERITS(value_list);
CREATE TABLE vl_interface (
  CHECK (plugin = 'interface')
) INHERITS(value_list);
CREATE TABLE vl_iptables (
  CHECK (plugin = 'iptables')
) INHERITS(value_list);
CREATE TABLE vl_ipmi (
  CHECK (plugin = 'ipmi')
) INHERITS(value_list);
CREATE TABLE vl_ipvs (
  CHECK (plugin = 'ipvs')
) INHERITS(value_list);
CREATE TABLE vl_irq (
  CHECK (plugin = 'irq')
) INHERITS(value_list);
CREATE TABLE vl_java (
  CHECK (plugin = 'java')
) INHERITS(value_list);
CREATE TABLE vl_libvirt (
  CHECK (plugin = 'libvirt')
) INHERITS(value_list);
CREATE TABLE vl_load (
  CHECK (plugin = 'load')
) INHERITS(value_list);
CREATE TABLE vl_madwifi (
  CHECK (plugin = 'madwifi')
) INHERITS(value_list);
CREATE TABLE vl_mbmon (
  CHECK (plugin = 'mbmon')
) INHERITS(value_list);
CREATE TABLE vl_memcachec (
  CHECK (plugin = 'memcachec')
) INHERITS(value_list);
CREATE TABLE vl_memcached (
  CHECK (plugin = 'memcached')
) INHERITS(value_list);
CREATE TABLE vl_memory (
  CHECK (plugin = 'memory')
) INHERITS(value_list);
CREATE TABLE vl_modbus (
  CHECK (plugin = 'modbus')
) INHERITS(value_list);
CREATE TABLE vl_multimeter (
  CHECK (plugin = 'multimeter')
) INHERITS(value_list);
CREATE TABLE vl_mysql (
  CHECK (plugin = 'mysql')
) INHERITS(value_list);
CREATE TABLE vl_netapp (
  CHECK (plugin = 'netapp')
) INHERITS(value_list);
CREATE TABLE vl_netlink (
  CHECK (plugin = 'netlink')
) INHERITS(value_list);
CREATE TABLE vl_nfs (
  CHECK (plugin = 'nfs')
) INHERITS(value_list);
CREATE TABLE vl_nginx (
  CHECK (plugin = 'nginx')
) INHERITS(value_list);
CREATE TABLE vl_notify_desktop (
  CHECK (plugin = 'notify_desktop')
) INHERITS(value_list);
CREATE TABLE vl_notify_email (
  CHECK (plugin = 'notify_email')
) INHERITS(value_list);
CREATE TABLE vl_ntpd (
  CHECK (plugin = 'ntpd')
) INHERITS(value_list);
CREATE TABLE vl_nut (
  CHECK (plugin = 'nut')
) INHERITS(value_list);
CREATE TABLE vl_olsrd (
  CHECK (plugin = 'olsrd')
) INHERITS(value_list);
CREATE TABLE vl_onewire (
  CHECK (plugin = 'onewire')
) INHERITS(value_list);
CREATE TABLE vl_openvpn (
  CHECK (plugin = 'openvpn')
) INHERITS(value_list);
CREATE TABLE vl_oracle (
  CHECK (plugin = 'oracle')
) INHERITS(value_list);
CREATE TABLE vl_pinba (
  CHECK (plugin = 'pinba')
) INHERITS(value_list);
CREATE TABLE vl_ping (
  CHECK (plugin = 'ping')
) INHERITS(value_list);
CREATE TABLE vl_postgresql (
  database VARCHAR(64) NOT NULL,
  schemaname VARCHAR(64),
  tablename VARCHAR(64),
  indexname VARCHAR(64),
  metric VARCHAR(64) NOT NULL,
  CHECK (plugin = 'postgresql')
) INHERITS (value_list);
CREATE TABLE vl_powerdns (
  CHECK (plugin = 'powerdns')
) INHERITS(value_list);
CREATE TABLE vl_processes (
  CHECK (plugin = 'processes')
) INHERITS(value_list);
CREATE TABLE vl_protocols (
  CHECK (plugin = 'protocols')
) INHERITS(value_list);
CREATE TABLE vl_routeros (
  CHECK (plugin = 'routeros')
) INHERITS(value_list);
CREATE TABLE vl_sensors (
  CHECK (plugin = 'sensors')
) INHERITS(value_list);
CREATE TABLE vl_serial (
  CHECK (plugin = 'serial')
) INHERITS(value_list);
CREATE TABLE vl_snmp (
  CHECK (plugin = 'snmp')
) INHERITS(value_list);
CREATE TABLE vl_swap (
  CHECK (plugin = 'swap')
) INHERITS(value_list);
CREATE TABLE vl_table (
  CHECK (plugin = 'table')
) INHERITS(value_list);
CREATE TABLE vl_tail (
  CHECK (plugin = 'tail')
) INHERITS(value_list);
CREATE TABLE vl_tape (
  CHECK (plugin = 'tape')
) INHERITS(value_list);
CREATE TABLE vl_tcpconns (
  CHECK (plugin = 'tcpconns')
) INHERITS(value_list);
CREATE TABLE vl_teamspeak2 (
  CHECK (plugin = 'teamspeak2')
) INHERITS(value_list);
CREATE TABLE vl_ted (
  CHECK (plugin = 'ted')
) INHERITS(value_list);
CREATE TABLE vl_thermal (
  CHECK (plugin = 'thermal')
) INHERITS(value_list);
CREATE TABLE vl_tokyotyrant (
  CHECK (plugin = 'tokyotyrant')
) INHERITS(value_list);
CREATE TABLE vl_uptime (
  CHECK (plugin = 'uptime')
) INHERITS(value_list);
CREATE TABLE vl_users (
  CHECK (plugin = 'users')
) INHERITS(value_list);
CREATE TABLE vl_uuid (
  CHECK (plugin = 'uuid')
) INHERITS(value_list);
CREATE TABLE vl_vmem (
  CHECK (plugin = 'vmem')
) INHERITS(value_list);
CREATE TABLE vl_vserver (
  CHECK (plugin = 'vserver')
) INHERITS(value_list);
CREATE TABLE vl_wireless (
  CHECK (plugin = 'wireless')
) INHERITS(value_list);
CREATE TABLE vl_xmms (
  CHECK (plugin = 'xmms')
) INHERITS(value_list);
CREATE TABLE vl_zfs_arc (
  CHECK (plugin = 'zfs_arc')
) INHERITS(value_list);
