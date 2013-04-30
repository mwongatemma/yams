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
    session = DBSession()
    data = session.execute(
        """SELECT time::TIMESTAMP, values[1] AS shortterm,
               values[2] AS midterm, values[3] AS longterm
        FROM value_list
        WHERE plugin = 'load'
        ORDER BY time;""")

    resp = 'timestamp,shortterm,midterm,longterm\n'
    for row in data:
        resp += '%s,%s,%s,%s\n' % (row[0], row[1], row[2], row[3])

    return Response(resp)
