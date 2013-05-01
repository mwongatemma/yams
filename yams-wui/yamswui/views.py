from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from .models import (
    DBSession,
    )


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'ylabel': ''}

@view_config(route_name='data')
def my_data(request):
    plugin = request.matchdict['plugin']

    session = DBSession()

    # The data source name and type should be the consistent within a plugin.
    # Grab the first one to get the details.
    result = session.execute(
            """SELECT dsnames, dstypes
            FROM value_list
            WHERE plugin = :plugin
            LIMIT 1;""", {'plugin': plugin}).first()
    dsnames = result[0]
    dstypes = result[1]
    length = len(dsnames)

    # Cast the timestamp with time zone to without time zone, which should
    # result in the system timezone because I can't figure out the format to
    # make d3 read the time zone correctly.
    data = session.execute(
            """SELECT time::TIMESTAMP, values
            FROM value_list
            WHERE plugin = :plugin
            ORDER BY time;""", {'plugin': plugin})

    csv = 'timestamp,%s\n' % ','.join(dsnames)

    lastrow = data.fetchone()
    for row in data:
        datum = []
        for i in range(length):
            # TODO: Handle counter and absolute types.
            if dstypes[i] == 'gauge':
                datum.append(str(lastrow[1][i]))
            elif dstypes[i] == 'derive':
                datum.append(str(lastrow[1][i] - row[1][i]))

        csv += '%s,%s\n' % (lastrow[0], ','.join(datum))
        lastrow = row

    return Response(csv)
