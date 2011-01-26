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
  values NUMERIC[]
);

-- Partition by creating a child table per collectd plugin.

CREATE TABLE vl_apache () INHERITS(value_list);
CREATE TABLE vl_apcups () INHERITS(value_list);
CREATE TABLE vl_apple_sensors () INHERITS(value_list);
CREATE TABLE vl_ascent () INHERITS(value_list);
CREATE TABLE vl_battery () INHERITS(value_list);
CREATE TABLE vl_bind () INHERITS(value_list);
CREATE TABLE vl_conntrack () INHERITS(value_list);
CREATE TABLE vl_contextswitch () INHERITS(value_list);
CREATE TABLE vl_cpu () INHERITS (value_list);
CREATE TABLE vl_cpufreq () INHERITS(value_list);
CREATE TABLE vl_curl () INHERITS(value_list);
CREATE TABLE vl_curl_json () INHERITS(value_list);
CREATE TABLE vl_curl_xml () INHERITS(value_list);
CREATE TABLE vl_dbi () INHERITS(value_list);
CREATE TABLE vl_df () INHERITS(value_list);
CREATE TABLE vl_disk () INHERITS(value_list);
CREATE TABLE vl_dns () INHERITS(value_list);
CREATE TABLE vl_email () INHERITS(value_list);
CREATE TABLE vl_entropy () INHERITS(value_list);
CREATE TABLE vl_exec () INHERITS(value_list);
CREATE TABLE vl_filecount () INHERITS(value_list);
CREATE TABLE vl_fscache () INHERITS(value_list);
CREATE TABLE vl_gmond () INHERITS(value_list);
CREATE TABLE vl_hddtemp () INHERITS(value_list);
CREATE TABLE vl_interface () INHERITS(value_list);
CREATE TABLE vl_iptables () INHERITS(value_list);
CREATE TABLE vl_ipmi () INHERITS(value_list);
CREATE TABLE vl_ipvs () INHERITS(value_list);
CREATE TABLE vl_irq () INHERITS(value_list);
CREATE TABLE vl_java () INHERITS(value_list);
CREATE TABLE vl_libvirt () INHERITS(value_list);
CREATE TABLE vl_load () INHERITS(value_list);
CREATE TABLE vl_madwifi () INHERITS(value_list);
CREATE TABLE vl_mbmon () INHERITS(value_list);
CREATE TABLE vl_memcachec () INHERITS(value_list);
CREATE TABLE vl_memcached () INHERITS(value_list);
CREATE TABLE vl_memory () INHERITS(value_list);
CREATE TABLE vl_modbus () INHERITS(value_list);
CREATE TABLE vl_multimeter () INHERITS(value_list);
CREATE TABLE vl_mysql () INHERITS(value_list);
CREATE TABLE vl_netapp () INHERITS(value_list);
CREATE TABLE vl_netlink () INHERITS(value_list);
CREATE TABLE vl_nfs () INHERITS(value_list);
CREATE TABLE vl_nginx () INHERITS(value_list);
CREATE TABLE vl_notify_desktop () INHERITS(value_list);
CREATE TABLE vl_notify_email () INHERITS(value_list);
CREATE TABLE vl_ntpd () INHERITS(value_list);
CREATE TABLE vl_nut () INHERITS(value_list);
CREATE TABLE vl_olsrd () INHERITS(value_list);
CREATE TABLE vl_onewire () INHERITS(value_list);
CREATE TABLE vl_openvpn () INHERITS(value_list);
CREATE TABLE vl_oracle () INHERITS(value_list);
CREATE TABLE vl_pinba () INHERITS(value_list);
CREATE TABLE vl_ping () INHERITS(value_list);
CREATE TABLE vl_postgresql (
  database VARCHAR(64) NOT NULL,
  schemaname VARCHAR(64),
  tablename VARCHAR(64),
  indexname VARCHAR(64)
) INHERITS (value_list);
CREATE TABLE vl_powerdns () INHERITS(value_list);
CREATE TABLE vl_processes () INHERITS(value_list);
CREATE TABLE vl_protocols () INHERITS(value_list);
CREATE TABLE vl_routeros () INHERITS(value_list);
CREATE TABLE vl_sensors () INHERITS(value_list);
CREATE TABLE vl_serial () INHERITS(value_list);
CREATE TABLE vl_snmp () INHERITS(value_list);
CREATE TABLE vl_swap () INHERITS(value_list);
CREATE TABLE vl_table () INHERITS(value_list);
CREATE TABLE vl_tail () INHERITS(value_list);
CREATE TABLE vl_tape () INHERITS(value_list);
CREATE TABLE vl_tcpconns () INHERITS(value_list);
CREATE TABLE vl_teamspeak2 () INHERITS(value_list);
CREATE TABLE vl_ted () INHERITS(value_list);
CREATE TABLE vl_thermal () INHERITS(value_list);
CREATE TABLE vl_tokyotyrant () INHERITS(value_list);
CREATE TABLE vl_uptime () INHERITS(value_list);
CREATE TABLE vl_users () INHERITS(value_list);
CREATE TABLE vl_uuid () INHERITS(value_list);
CREATE TABLE vl_vmem () INHERITS(value_list);
CREATE TABLE vl_vserver () INHERITS(value_list);
CREATE TABLE vl_wireless () INHERITS(value_list);
CREATE TABLE vl_xmms () INHERITS(value_list);
CREATE TABLE vl_zfs_arc () INHERITS(value_list);
