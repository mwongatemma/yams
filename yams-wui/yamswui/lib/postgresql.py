from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def get_backend_data(host, dbname):
    ts = gmtime(time() - 86400)
    timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                         ts.tm_min, ts.tm_sec)

    connection = Session.connection()
    connection.execute('BEGIN;')
    tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, values
FROM vl_postgresql
WHERE time > :timestamp
  AND host = :host
  AND metric = 'numbackends'
  AND database = :dbname
ORDER BY time ASC; ;"""), timestamp=timestamp, host=host, dbname=dbname)
    connection.execute('COMMIT;')

    if tuples.rowcount < 1:
        return None

    data = list()
    
    for row in tuples:
        ctime = int(row['time'])
        data.append('[%d, %f]' % (ctime, row['values'][0]))

    return ', '.join(data)

def get_xact_data(host, dbname):
    data = dict()
    data['commit'] = list()
    data['rollback'] = list()

    ts = gmtime(time() - 86400)
    timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                         ts.tm_min, ts.tm_sec)

    connection = Session.connection()

    connection.execute('BEGIN;')
    tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, values
FROM vl_postgresql
WHERE time > :timestamp
  AND host = :host
  AND metric = 'xact_commit'
  AND database = :dbname
ORDER BY time ASC; ;"""), timestamp=timestamp, host=host, dbname=dbname)

    rows = tuples.fetchall()

    tmp = list()
    i = 1
    while i < tuples.rowcount:
        metric = rows[i]['values'][0] - rows[i - 1]['values'][0]
        ctime = int(rows[i]['time'])
        tmp.append('[%d, %f]' % (ctime, metric))
        i += 1

    data['commit'] = ', '.join(tmp)

    tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, values
FROM vl_postgresql
WHERE time > :timestamp
  AND host = :host
  AND metric = 'xact_rollback'
  AND database = :dbname
ORDER BY time ASC; ;"""), timestamp=timestamp, host=host, dbname=dbname)
    connection.execute('COMMIT;')

    tmp = list()
    i = 1
    while i < tuples.rowcount:
        metric = rows[i]['values'][0] - rows[i - 1]['values'][0]
        ctime = int(rows[i]['time'])
        tmp.append('[%d, %f]' % (ctime, metric))
        i += 1

    data['rollback'] = ', '.join(tmp)

    return data

def postgresql_backend(host, dbname):
    data = get_backend_data(host, dbname)

    js = """
    <button id="reset-postgresql-backend">Reset</button>
    <div id="backend" style="width:600px;height:300px;">
    </div>"""

    js += """
    <script type="text/javascript" charset="utf-8">
      var options_backend = {
          title: 'Backends',
          xaxis: {
              title: 'Time',
              tickFormatter: myDateFormatter
          },
          yaxis: {
              min: 0,
          },
          legend: {
              position: 'nw',
              labelFormatter: myLabelFunc
          },
          mouse: {
              track: true,
              lineColor: 'purple',
              sensibility: 100,
              trackDecimals: 2,
              trackFormatter: function(obj) {
                  return myDateFormatter(obj.x) +', ' + obj.y;
              }
          },
          selection: { mode: 'x' }
      };

      function myLabelFunc(label) {
          return label;
      }

      function myDateFormatter(ctime) {
          myDate = Date(ctime);
          return myDate.toLocaleString();
      }

      function myDraw() {
          function drawGraph(opts) {
              var o = Object.extend(Object.clone(options_backend), opts || {});
              return Flotr.draw(
                  $('backend'),
                  [
                      {
                          label: '%s',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      }
                  ],
                  o
              );
          }

          var f = drawGraph();

          $('backend').observe('flotr:select', function(evt) {
              var area = evt.memo[0];

              f = drawGraph({
                  xaxis: {
                      min: area.x1,
                      max: area.x2,
                      tickFormatter: myDateFormatter
                  },
                  yaxis: { min: area.y1, max: area.y2, title: 'Backends' }
              });
          });

          $('reset-postgresql-backend').observe('click',
                  function() { drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>""" % (dbname, data)

    return literal(js)

def postgresql_xact(host, dbname):
    data = get_xact_data(host, dbname)

    js = """
    <button id="reset-postgresql-xact">Reset</button>
    <div id="xact" style="width:600px;height:300px;">
    </div>"""

    js += """
    <script type="text/javascript" charset="utf-8">
      var options_xact = {
          title: 'Transactions',
          xaxis: {
              title: 'Time',
              tickFormatter: myDateFormatter
          },
          yaxis: {
              min: 0,
          },
          legend: {
              position: 'nw',
              labelFormatter: myLabelFunc
          },
          mouse: {
              track: true,
              lineColor: 'purple',
              sensibility: 100,
              trackDecimals: 2,
              trackFormatter: function(obj) {
                  return myDateFormatter(obj.x) +', ' + obj.y;
              }
          },
          selection: { mode: 'x' }
      };

      function myLabelFunc(label) {
          return label;
      }

      function myDateFormatter(ctime) {
          myDate = Date(ctime);
          return myDate.toLocaleString();
      }

      function myDraw() {
          function drawGraph(opts) {
              var o = Object.extend(Object.clone(options_xact), opts || {});
              return Flotr.draw(
                  $('xact'),
                  [
                      {
                          label: 'Commit',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'Rollback',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      }
                  ],
                  o
              );
          }

          var f = drawGraph();

          $('xact').observe('flotr:select', function(evt) {
              var area = evt.memo[0];

              f = drawGraph({
                  xaxis: {
                      min: area.x1,
                      max: area.x2,
                      tickFormatter: myDateFormatter
                  },
                  yaxis: { min: area.y1, max: area.y2, title: 'Backends' }
              });
          });

          $('reset-postgresql-xact').observe('click',
                  function() { drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>""" % (data['commit'], data['rollback'])

    return literal(js)
