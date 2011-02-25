from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def get_data_load(host, duration=86400, end_ctime=None):
    if end_ctime is None:
        end_ctime = time()

    ts = gmtime(end_ctime)
    end_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                             ts.tm_min, ts.tm_sec)

    ts = gmtime(end_ctime - duration)
    start_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                               ts.tm_min, ts.tm_sec)

    connection = Session.connection()
    connection.execute('BEGIN;')
    tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, dsnames, values
FROM vl_load
WHERE time > :starttime
  AND time <= :endtime
  AND host = :name
ORDER BY time ASC;"""), name=host, starttime=start_timestamp,
                        endtime=end_timestamp)
    connection.execute('COMMIT;')

    if tuples.rowcount < 1:
        return None

    data = dict()
    vl_load1 = list()
    vl_load5 = list()
    vl_load15 = list()
    first = True
    for row in tuples:
        if first:
            data['dsnames'] = row['dsnames']

        ctime = int(row['time'])
        vl_load1.append('[%d, %f]' % (ctime, row['values'][0]))
        vl_load5.append('[%d, %f]' % (ctime, row['values'][1]))
        vl_load15.append('[%d, %f]' % (ctime, row['values'][2]))

    data['load1'] = ', '.join(vl_load1)
    data['load5'] = ', '.join(vl_load5)
    data['load15'] = ', '.join(vl_load15)

    return data
