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

        connection = Session.connection()

        # load stats
        connection.execute('BEGIN;')
        tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, dsnames, values
FROM vl_load
WHERE time > NOW() - INTERVAL '1 DAY'
  AND host = :name
ORDER BY time ASC; ;"""), name=c.host)
        connection.execute('COMMIT;')

        vl_load1 = list()
        vl_load5 = list()
        vl_load15 = list()
        first = True
        for row in tuples:
            if first:
                c.load_dsnames = row['dsnames']

            ctime = int(row['time'])
            vl_load1.append('[%d, %f]' % (ctime, row['values'][0]))
            vl_load5.append('[%d, %f]' % (ctime, row['values'][1]))
            vl_load15.append('[%d, %f]' % (ctime, row['values'][2]))
        c.load1 = ', '.join(vl_load1)
        c.load5 = ', '.join(vl_load5)
        c.load15 = ', '.join(vl_load15)

        # processor stats
        connection.execute('BEGIN;')
        tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time,
       SUM(CASE WHEN type_instance = 'idle' THEN values[1] ELSE 0 END) AS idle,
       SUM(CASE WHEN type_instance = 'interrupt'
                THEN values[1] ELSE 0 END) AS interrupt,
       SUM(CASE WHEN type_instance = 'nice' THEN values[1] ELSE 0 END) AS nice,
       SUM(CASE WHEN type_instance = 'softirq'
                THEN values[1] ELSE 0 END) AS softirq,
       SUM(CASE WHEN type_instance = 'steal'
                THEN values[1] ELSE 0 END) AS steal,
       SUM(CASE WHEN type_instance = 'system'
                THEN values[1] ELSE 0 END) AS system,
       SUM(CASE WHEN type_instance = 'user' THEN values[1] ELSE 0 END) AS user,
       SUM(CASE WHEN type_instance = 'wait' THEN values[1] ELSE 0 END) AS wait
FROM vl_cpu
WHERE time > NOW() - INTERVAL '1 DAY'
  AND host = :name
GROUP BY time
ORDER BY time ASC;"""), name=c.host)

        rows = tuples.fetchall()

        vl_idle = list()
        vl_interrupt = list()
        vl_nice = list()
        vl_softirq = list()
        vl_steal = list()
        vl_system = list()
        vl_user = list()
        vl_wait = list()

        i = 1
        while i < tuples.rowcount:
            # Calculate change in values.
            idle = rows[i]['idle'] - rows[i - 1]['idle']
            interrupt = rows[i]['interrupt'] - rows[i - 1]['interrupt']
            nice = rows[i]['nice'] - rows[i - 1]['nice']
            softirq = rows[i]['softirq'] - rows[i - 1]['softirq']
            steal = rows[i]['steal'] - rows[i - 1]['steal']
            system = rows[i]['system'] - rows[i - 1]['system']
            user = rows[i]['user'] - rows[i - 1]['user']
            wait = rows[i]['wait'] - rows[i - 1]['wait']
            total = idle + interrupt + nice + softirq + steal + system + \
                    user + wait
            if total == 0:
                # Proactive handling of divide by 0.
                idle = 0
                interrupt = 0
                nice = 0
                softirq = 0
                steal = 0
                system = 0
                user = 0
                wait = 0
            else:
                # Convert jiffles to percentages.
                idle /= total / 100
                interrupt /= total / 100
                nice /= total / 100
                softirq /= total / 100
                steal /= total / 100
                system /= total / 100
                user /= total / 100
                wait /= total / 100

            # Convert into how flotr wants the data.
            ctime = int(rows[i]['time'])
            vl_idle.append('[%d, %f]' % (ctime, idle))
            vl_interrupt.append('[%d, %f]' % (ctime, interrupt))
            vl_nice.append('[%d, %f]' % (ctime, nice))
            vl_softirq.append('[%d, %f]' % (ctime, softirq))
            vl_steal.append('[%d, %f]' % (ctime, steal))
            vl_system.append('[%d, %f]' % (ctime, system))
            vl_user.append('[%d, %f]' % (ctime, user))
            vl_wait.append('[%d, %f]' % (ctime, wait))

            i += 1

        # Generate strings for javascript to use.
        c.idle = ', '.join(vl_idle)
        c.interrupt = ', '.join(vl_interrupt)
        c.nice = ', '.join(vl_nice)
        c.softirq = ', '.join(vl_softirq)
        c.steal = ', '.join(vl_steal)
        c.system = ', '.join(vl_system)
        c.user = ', '.join(vl_user)
        c.wait = ', '.join(vl_wait)

        connection.close()

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
