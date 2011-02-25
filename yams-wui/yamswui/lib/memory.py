from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def get_data_memory(host, duration=86400, end_ctime=None):
    if end_ctime is None:
        end_ctime = time()

    ts = gmtime(end_ctime)
    end_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                             ts.tm_min, ts.tm_sec)

    ts = gmtime(end_ctime - duration)
    start_timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                               ts.tm_min, ts.tm_sec)

    data = dict()
    connection = Session.connection()
    connection.execute('BEGIN;')
    for type_instance in ['buffered', 'cached', 'free', 'used']:
        tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, values[1] AS value
FROM vl_memory
WHERE time > :starttime
  AND time <= :endtime
  AND host = :name
  AND type_instance = :type_instance
ORDER BY time ASC;"""), name=host, starttime=start_timestamp,
                        endtime=end_timestamp, type_instance=type_instance)
        vl = list()
        for row in tuples:
            ctime = int(row['time'])
            vl.append('[%d, %f]' % (ctime, float(row['value'])))
        data[type_instance] = ', '.join(vl)
    connection.execute('COMMIT;')

    return data
