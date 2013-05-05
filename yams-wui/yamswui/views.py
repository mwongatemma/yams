from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import (
    DBSession,
    )


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    url_list = ['data.csv/load/tweety?dsnames=shortterm',
                'data.csv/load/tweety?dsnames=longterm']
    return {'url_list': url_list}


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

    if 'database' in request.params:
        where_condition += ' AND meta -> \'database\' = :database'
        sql_params['database'] = request.params['database']

    if 'schema' in request.params:
        where_condition += ' AND meta -> \'schema\' = :schema'
        sql_params['schema'] = request.params['schema']

    if 'table' in request.params:
        where_condition += ' AND meta -> \'table\' = :table'
        sql_params['table'] = request.params['table']

    if 'index' in request.params:
        where_condition += ' AND meta -> \'index\' = :index'
        sql_params['index'] = request.params['index']

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
        # No need to continue if ther eis nothing to plot.
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
                "  AND tablename LIKE 'vl\\_%' " \
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
