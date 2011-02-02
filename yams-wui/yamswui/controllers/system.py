import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import validate

from yamswui.lib.base import BaseController, render
from yamswui.model import meta
from yamswui.model.meta import Session

import formencode

from sqlalchemy.sql.expression import text

log = logging.getLogger(__name__)

class SystemAddForm(formencode.Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    name = formencode.validators.String(not_empty=True)

class SystemController(BaseController):

    def add(self):
        return render('/system-add.mako')

    def detail(self, id):
        c.host = id
        return render('/system-detail.mako')

    def index(self):
        connection = Session.connection()
        connection.execute('BEGIN;')
        tuples = connection.execute('SELECT name FROM systems ORDER BY name;')
        connection.execute('COMMIT;')
        connection.close()

        c.systems = list()
        for tuple in tuples:
            c.systems.append(tuple['name'])

        return render('/system.mako')

    @validate(schema=SystemAddForm(), form='add')
    def insert(self):
        connection = Session.connection()
        connection.execute('BEGIN;')
        connection.execute(
                text('INSERT INTO systems (name) VALUES (:name);'),
                name=request.params['name'])
        connection.execute('COMMIT;')
        connection.close()

        redirect(url(controller='system', action='index'))
