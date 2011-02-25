from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def get_data_vmem_swap(host, duration=86400, end_ctime=None):
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
FROM vl_vmem
WHERE time > :starttime
  AND time <= :endtime
  AND host = :name
  AND type = 'vmpage_io'
  AND type_instance = 'memory'
ORDER BY time ASC;"""), name=host, starttime=start_timestamp,
                        endtime=end_timestamp)
    connection.execute('COMMIT;')

    if tuples.rowcount < 1:
        return None

    data = dict()
    tmpdata = dict()
    first = True
    rows = tuples.fetchall()
    data['dsnames'] = rows[0]['dsnames']
    for ds in data['dsnames']:
        tmpdata[ds] = list()
    i = 1
    while i < tuples.rowcount:
        ctime = int(rows[i]['time'])
        for j in range(len(data['dsnames'])):
            tmpdata[data['dsnames'][j]].append('[%d, %f]' % (ctime,
                    float(rows[i]['values'][j] - rows[i - 1]['values'][j])))
        i += 1

    for ds in data['dsnames']:
        data[ds] = ', '.join(tmpdata[ds])

    return data
