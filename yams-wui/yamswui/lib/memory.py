from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def code_memory(host):
    data = get_memory(host)

    js = """
    <button id="reset-memory">Reset</button>
    <div id="memory" style="width:600px;height:300px;">
    </div>"""

    js += """
    <script type="text/javascript" charset="utf-8">
      var options_memory = {
          title: 'Memory',
          xaxis: {
              title: 'Time',
              tickFormatter: myDateFormatter
          },
          yaxis: {
              title: 'Megabytes',
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
                  return myDateFormatter(obj.x) +', ' + obj.y + '%%';
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
              var o = Object.extend(Object.clone(options_memory), opts || {});
              return Flotr.draw(
                  $('memory'),
                  [
                      {
                          label: 'buffered',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'cached',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'free',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'used',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                  ],
                  o
              );
          }

          var f = drawGraph();

          $('memory').observe('flotr:select', function(evt) {
              var area = evt.memo[0];

              f = drawGraph({
                  xaxis: {
                      min: area.x1,
                      max: area.x2,
                      tickFormatter: myDateFormatter
                  },
                  yaxis: { min: area.y1, max: area.y2, title: 'Percent' }
              });
          });

          $('reset-memory').observe('click', function(){ drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>""" % (data['buffered'], data['cached'], data['free'],
                    data['used'])

    return literal(js)

def get_memory(host):
    data = dict()
    ts = gmtime(time() - 86400)
    timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                         ts.tm_min, ts.tm_sec)

    connection = Session.connection()
    connection.execute('BEGIN;')
    for type_instance in ['buffered', 'cached', 'free', 'used']:
        tuples = connection.execute(text(
"""SELECT EXTRACT(EPOCH FROM time) * 1000 AS time,
       values[1]::NUMERIC / (1024 * 1024)::NUMERIC AS value
FROM vl_memory
WHERE time > :timestamp
  AND host = :name
  AND type_instance = :type_instance
ORDER BY time ASC;"""), name=host, timestamp=timestamp,
                        type_instance=type_instance)
        vl = list()
        for row in tuples:
            ctime = int(row['time'])
            vl.append('[%d, %f]' % (ctime, float(row['value'])))
        data[type_instance] = ', '.join(vl)
    connection.execute('COMMIT;')

    return data
