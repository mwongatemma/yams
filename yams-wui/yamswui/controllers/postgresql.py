import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect

from yamswui.lib.base import BaseController, render

log = logging.getLogger(__name__)

class PostgresqlController(BaseController):

    def index(self):
        # Return a rendered template
        #return render('/postgresql.mako')
        # or, return a string
        return 'Hello World'

    def stat(self, id):
        c.host = id
        if 'dbname' in request.params:
            c.dbname = request.params['dbname']
        return render('/postgresql-stat.mako')
