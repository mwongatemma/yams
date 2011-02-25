from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def get_data_cpu(host, duration=86400, end_ctime=None, cpu=None):
    if end_ctime is None:
        end_ctime = time()

    ts = gmtime(end_ctime)
    end_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                             ts.tm_min, ts.tm_sec)

    ts = gmtime(end_ctime - duration)
    start_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                               ts.tm_min, ts.tm_sec)

    if cpu is not None:
        where_clause = 'AND plugin_instance = :cpu'
    else:
        where_clause = ''

    sql = text("""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time,
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
WHERE time > :starttime
  AND time <= :endtime
  AND host = :name
  %s
GROUP BY time
ORDER BY time ASC;""" % where_clause)

    connection = Session.connection()
    connection.execute('BEGIN;')
    if cpu is not None:
        tuples = connection.execute(sql, name=host, starttime=start_timestamp,
                                    endtime=end_timestamp, cpu=str(cpu))
    else:
        tuples = connection.execute(sql, name=host, starttime=start_timestamp,
                                    endtime=end_timestamp)
    connection.execute('COMMIT;')

    if tuples.rowcount < 1:
        return None

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
            # Convert jiffies to percentages.
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
    data = dict()
    data['idle'] = ', '.join(vl_idle)
    data['interrupt'] = ', '.join(vl_interrupt)
    data['nice'] = ', '.join(vl_nice)
    data['softirq'] = ', '.join(vl_softirq)
    data['steal'] = ', '.join(vl_steal)
    data['system'] = ', '.join(vl_system)
    data['user'] = ', '.join(vl_user)
    data['wait'] = ', '.join(vl_wait)

    return data
