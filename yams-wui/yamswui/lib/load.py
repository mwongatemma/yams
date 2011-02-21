from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def code_load(host):
    data = get_load(host)

    js = """
    <button id="reset-load">Reset</button>
    <div id="load" style="width:600px;height:300px;">
    </div>"""

    if data is not None:
        js += """
    <script type="text/javascript" charset="utf-8">
      var options_load = {
          title: 'Load',
          xaxis: {
              title: 'Time',
              tickFormatter: myDateFormatter
          },
          yaxis: {
              min: 0
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
                  return myDateFormatter(obj.x) + ', ' + obj.y;
              }
          },
          selection: { mode: 'x' }
      };

      function myLabelFunc(label) {
          return label;
      }

      function myDateFormatter(mytime) {
          myDate = new Date();
          myDate.setTime(mytime);
          return myDate.toLocaleString();
      }

      function myDraw() {
          function drawGraph(opts) {
              var o = Object.extend(Object.clone(options_load), opts || {});
              return Flotr.draw(
                  $('load'),
                  [
                      {
                          label: '%s',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: '%s',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
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

          $('load').observe('flotr:select', function(evt) {
              var area = evt.memo[0];

              f = drawGraph({
                  xaxis: {
                      min: area.x1,
                      max: area.x2,
                      tickFormatter: myDateFormatter
                  },
                  yaxis: { min: area.y1, max: area.y2 }
              });
          });

          $('reset-load').observe('click', function(){ drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>""" % (data['dsnames'][0], data['load1'], data['dsnames'][1],
                    data['load5'], data['dsnames'][2], data['load15'])
    return literal(js)

def get_load(host):
    ts = gmtime(time() - 86400)
    timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                         ts.tm_min, ts.tm_sec)

    connection = Session.connection()
    connection.execute('BEGIN;')
    tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time, dsnames, values
FROM vl_load
WHERE time > :timestamp
  AND host = :name
ORDER BY time ASC;"""), name=host, timestamp=timestamp)
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
