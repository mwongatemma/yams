from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import (
    DBSession,
    )


@view_config(route_name='add_source')
def add_source(request):
    params = {}

    if 'plugin' in request.session:
        params['plugin'] = request.session['plugin']
    else:
        return Response()

    if 'hosts' in request.session:
        hosts = request.session['hosts']
    else:
        return Response()

    if 'type' in request.session:
        params['type'] = request.session['type']
    else:
        return response()

    if 'dsnames' in request.session:
        dsnames = request.session['dsnames']
    else:
        return Response()

    if 'meta' in request.session:
        meta = request.session['meta']
    else:
        return Response()

    if 'url_list' not in request.session:
        request.session['url_list'] = []

    for host in hosts:
        params['host'] = host
        url = 'data.csv/%(plugin)s/%(host)s?type=%(type)s' % params
        if len(dsnames) > 0:
            url += '&' + \
                    '&'.join(['dsnames=%s' % dsname for dsname in dsnames])

            # Append meta data by create an array of keys, then the key with
            # its value.
            url += '&' + \
                    '&'.join(['meta=%s' % key for key in meta.iterkeys()])
            url += '&' + \
                    '&'.join(['%s=%s' % (key, value) \
                            for (key, value) in meta.iteritems()])
        if url not in request.session['url_list']:
            request.session['url_list'].append(url)

    return Response()


@view_config(route_name='chart', renderer='templates/chart.pt')
def chart(request):
    if 'url_list' in request.session:
        url_list = request.session['url_list']
    else:
        url_list = []
    return {'url_list': url_list}


@view_config(route_name='clear_sources')
def clear_sources(request):
    if 'url_list' in request.session:
        request.session['url_list'] = []
    return Response()


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {}


@view_config(route_name='hosts', renderer='templates/hosts.pt')
def hosts(request):
    plugin = request.matchdict['plugin']
    type = request.matchdict['type']

    session = DBSession()

    # For performance reasons, find the most recent table partition for the
    # plugin and get the hosts from that.
    if plugin == 'postgresql':
        table = session.execute(
                "SELECT tablename " \
                "FROM pg_tables " \
                "WHERE tablename LIKE 'vl\\_postgresql\\_%%_%s' " \
                "ORDER BY tablename DESC " \
                "LIMIT 1;" % type).fetchone()['tablename']
    else:
        table = session.execute(
                "SELECT tablename " \
                "FROM pg_tables " \
                "WHERE tablename LIKE 'vl\\_%s\\_%%' " \
                "ORDER BY tablename DESC " \
                "LIMIT 1;" % plugin).fetchone()['tablename']

    # Take advantage of the column index on host by using a recursive query.
    hosts = session.execute(
            "WITH RECURSIVE t(n) AS (" \
            "    SELECT min(host) " \
            "    FROM %(table)s " \
            "    UNION ALL " \
            "    SELECT (SELECT host " \
            "            FROM %(table)s " \
            "            WHERE host > n " \
            "            ORDER BY host " \
            "            LIMIT 1) " \
            "    FROM t WHERE n IS NOT NULL " \
            ") " \
            "SELECT n AS host " \
            "FROM t " \
            "WHERE n <> '';" % {'table': table})

    return {'plugin': plugin, 'type': type, 'hosts': hosts}


@view_config(route_name='data_csv')
def data_csv(request):
    plugin = request.matchdict['plugin']
    host = request.matchdict['host']

    sql_params = {'plugin': plugin, 'host': host}

    # Not sure if there is a faster way, but always get the entire dataset from
    # the database, and filter out the values we don't want specified by the
    # query string.
    wanted_dsnames = None
    if 'dsnames' in request.params:
        wanted_dsnames = request.params.getall('dsnames')

    where_condition = ''

    if 'type' in request.params:
        where_condition += ' AND type = :type'
        sql_params['type'] = request.params['type']

    if 'meta' in request.params:
        keys = request.params.getall('meta')

        for key in keys:
            where_condition += ' AND meta -> \'%(key)s\' = :%(key)s' % \
                    {'key': key}
            sql_params[key] = request.params[key]

    session = DBSession()

    # The data source name and type should be the consistent within a plugin.
    # Grab the first one to get the details.
    result = session.execute(
            "SELECT dsnames, dstypes, " \
            "       plugin || " \
            "           CASE WHEN plugin_instance <> '' " \
            "                THEN '.' || plugin_instance ELSE '' END || " \
            "           '.' || type || " \
            "           CASE WHEN type_instance <> '' " \
            "                THEN '.' || type_instance ELSE '' END " \
            "           AS prefix " \
            "FROM value_list " \
            "WHERE plugin = :plugin " \
            "%s " \
            "LIMIT 1;""" % where_condition, sql_params).first()
    if not result:
        # These query parameters do not return any data.
        return Response('')

    dsnames = result['dsnames']
    dstypes = result['dstypes']
    prefix = result['prefix']
    length = len(dsnames)

    if wanted_dsnames:
        plot_dsnames = []
        for dsname in dsnames:
            if dsname in wanted_dsnames:
                plot_dsnames.append(dsname)
    else:
        plot_dsnames = dsnames

    if len(plot_dsnames) == 0:
        # No need to continue if there is nothing to plot.
        return Response('')

    # Cast the timestamp with time zone to without time zone, which should
    # result in the system timezone because I can't figure out the format to
    # make d3 read the time zone correctly.
    data = session.execute(
            "SELECT extract(EPOCH FROM time)::BIGINT * 1000 AS ctime_ms, " \
            "       values " \
            "FROM value_list " \
            "WHERE plugin = :plugin " \
            "AND host = :host " \
            "AND time > CURRENT_TIMESTAMP - INTERVAL '1 HOUR' " \
            "%s " \
            "ORDER BY time;" % where_condition, sql_params)

    csv = 'timestamp,%s\n' % \
            ','.join(['%s.%s.%s' % \
                     (host.replace('.', '_'), prefix, dsname) \
                      for dsname in plot_dsnames])

    # TODO: With thousands of data points, this loop seems to be unacceptably
    # slow. Is there a faster way? Database stored procedure?
    oldrow = data.fetchone()
    for newrow in data:
        datum = []
        for i in range(length):
            if dsnames[i] in plot_dsnames:
                # TODO: Handle absolute types.
                if dstypes[i] == 'counter':
                    # FIXME: Handle wrap around.
                    datum.append(str(
                            newrow['values'][i] - oldrow['values'][i]))
                elif dstypes[i] == 'derive':
                    datum.append(str(
                            newrow['values'][i] - oldrow['values'][i]))
                elif dstypes[i] == 'gauge':
                    datum.append(str(oldrow['values'][i]))

        csv += '%s,%s\n' % (oldrow['ctime_ms'], ','.join(datum))
        oldrow = newrow

    return Response(body=csv, content_type='text/csv')


@view_config(route_name='dsnames', renderer='templates/dsnames.pt')
def dsnames(request):
    plugin = request.matchdict['plugin']
    type = request.matchdict['type']

    session = DBSession()
    dsnames = session.execute(
            "SELECT dsnames " \
            "FROM value_list " \
            "WHERE plugin = :plugin " \
            "  AND type = :type " \
            "LIMIT 1;", {'plugin': plugin, 'type': type}).fetchone()['dsnames']

    return {'plugin': plugin, 'type': type, 'dsnames': dsnames}


@view_config(route_name='plugins', renderer='templates/plugins.pt')
def plugins(request):
    session = DBSession()
    # Cheat on getting the list of plugins that data exists for by taking
    # advantage of the table partitioning naming schema.
    plugins = session.execute(
            "SELECT DISTINCT substring(tablename, 'vl_(.*?)_') AS plugin " \
            "FROM pg_tables " \
            "WHERE schemaname = 'collectd' " \
            "  AND tablename LIKE 'vl\\_%' " \
            "ORDER BY plugin;")
    return {'plugins': plugins}


@view_config(route_name='plugin_instances',
        renderer='templates/plugin_instances.pt')
def plugin_instancess(request):
    plugin = request.matchdict['plugin']

    request.session['plugin'] = plugin
    if 'type' in request.session:
        request.session['type'] = ''
    if 'hosts' in request.session:
        request.session['hosts'] = []
    if 'dsnames' in request.session:
        request.session['dsnames'] = []
    if 'meta' in request.session:
        request.session['meta'] = {}

    if plugin == 'postgresql':
        return Response()

    session = DBSession()

    # For performance reasons, find the most recent table partition for the
    # plugin and get the plugin_instances from that.
    table = session.execute(
            "SELECT tablename " \
            "FROM pg_tables " \
            "WHERE tablename LIKE 'vl\\_%s\\_%%' " \
            "ORDER BY tablename DESC " \
            "LIMIT 1;" % plugin).fetchone()['tablename']

    plugin_instances = session.execute(
            "SELECT DISTINCT plugin_instance " \
            "FROM %s " \
            "WHERE plugin_instance <> '' " \
            "ORDER BY plugin_instance;" % table)

    if plugin_instances.rowcount == 0:
        return Response()

    return {'plugin': plugin, 'plugin_instances': plugin_instances}


@view_config(route_name='session', renderer='templates/session.pt')
def session(request):
    session = DBSession()

    if 'plugin' in request.session:
        plugin = request.session['plugin']
    else:
        plugin = ''

    if 'type' in request.session:
        type = request.session['type']
    else:
        type = ''

    if 'hosts' in request.session:
        hosts = request.session['hosts']
    else:
        hosts = []

    if 'dsnames' in request.session:
        dsnames = request.session['dsnames']
    else:
        dsnames = []

    if 'url_list' not in request.session:
        request.session['url_list'] = []
    url_list = request.session['url_list']

    if 'meta' not in request.session:
        request.session['meta'] = {}
    meta = request.session['meta']

    if plugin <> '' and type <> '' and len(hosts) > 0:
        add_source = True
    else:
        add_source = False

    if len(url_list) > 0:
        show_clear = True
    else:
        show_clear = False

    # Create input form for meta data only for the postgresql plugin.
    if plugin == 'postgresql':
        # Because of potentially high volumes of postgres metrics, take
        # advantage of the special partitioning schema used for the
        # postgresql plugin.
        tablename = session.execute(
                "SELECT tablename " \
                "FROM pg_tables " \
                "WHERE schemaname = 'collectd' " \
                "  AND substring(tablename, " \
                "      'vl_postgresql_\d\d\d\d\d\d\d\d_%s') IS NOT NULL " \
                "ORDER BY tablename;" % type).fetchone()['tablename']

        meta_keys = session.execute(
                "SELECT akeys(meta) AS keys " \
                "FROM %s " \
                "LIMIT 1;" % tablename).fetchone()['keys']
    else:
        meta_keys = []

    return {'plugin': plugin, 'type': type, 'hosts': ', '.join(hosts),
            'dsnames': ', '.join(dsnames), 'url_list': url_list,
            'add_source': add_source, 'show_clear': show_clear,
            'meta_keys': meta_keys, 'meta': meta}


@view_config(route_name='toggle_dsname')
def toggle_dsname(request):
    dsname = request.matchdict['dsname']
    if 'dsnames' in request.session:
        if dsname in request.session['dsnames']:
            request.session['dsnames'].remove(dsname)
        else:
            request.session['dsnames'].append(dsname)
    else:
        request.session['dsnames'] = [dsname]
    return Response()


@view_config(route_name='toggle_host')
def toggle_host(request):
    host = request.matchdict['host']
    if 'hosts' in request.session:
        if host in request.session['hosts']:
            request.session['hosts'].remove(host)
        else:
            request.session['hosts'].append(host)
    else:
        request.session['hosts'] = [host]
    return Response()


@view_config(route_name='toggle_meta')
def toggle_meta(request):
    key = request.matchdict['key']
    value = request.matchdict['value']

    if 'meta' not in request.session:
        request.session['meta'] = {}

    request.session['meta'][key] = value

    return Response()


@view_config(route_name='types', renderer='templates/types.pt')
def types(request):
    plugin = request.matchdict['plugin']

    session = DBSession()

    if plugin == 'postgresql':
        # Because of potentially high volumes of postgres metrics, take
        # advantage of the special partitioning schema used for the postgresql
        # plugin.
        types = session.execute(
                "SELECT DISTINCT substring(tablename, " \
                "       'vl_postgresql_\d\d\d\d\d\d\d\d_(.*)') AS type " \
                "FROM pg_tables " \
                "WHERE schemaname = 'collectd' " \
                "  AND substring(tablename, " \
                "      'vl_postgresql_\d\d\d\d\d\d\d\d_(.*)') IS NOT NULL " \
                "ORDER BY type;")
    else:
        # For performance reasons, find the most recent table partition for the
        # plugin and get the types from that.
        table = session.execute(
                "SELECT tablename " \
                "FROM pg_tables " \
                "WHERE tablename LIKE 'vl\\_%s\\_%%' " \
                "ORDER BY tablename DESC " \
                "LIMIT 1;" % plugin).fetchone()['tablename']

        types = session.execute(
                "SELECT DISTINCT type " \
                "FROM %s " \
                "ORDER BY type;" % table)

    return {'plugin': plugin, 'types': types}


@view_config(route_name='type_instances',
        renderer='templates/type_instances.pt')
def type_instances(request):
    plugin = request.matchdict['plugin']
    type = request.matchdict['type']

    request.session['type'] = type
    if 'dsnames' in request.session:
        request.session['dsnames'] = []

    if plugin == 'postgresql':
        return Response()

    session = DBSession()

    # For performance reasons, find the most recent table partition for the
    # plugin and get the plugin_instances from that.
    table = session.execute(
            "SELECT tablename " \
            "FROM pg_tables " \
            "WHERE tablename LIKE 'vl\\_%s\\_%%' " \
            "ORDER BY tablename DESC " \
            "LIMIT 1;" % plugin).fetchone()['tablename']

    type_instances = session.execute(
            "SELECT DISTINCT type_instance " \
            "FROM %s " \
            "WHERE type_instance <> '' " \
            "ORDER BY type_instance;" % table)

    if type_instances.rowcount == 0:
        return Response()

    return {'plugin': plugin, 'type': type, 'type_instances': type_instances}
