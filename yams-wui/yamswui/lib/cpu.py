from datetime import datetime
from time import gmtime, time

from webhelpers.html import literal

from sqlalchemy.sql.expression import text

from yamswui.model.meta import Session

def code_cpu(host):
    data = get_cpu(host)

    js = """
    <button id="reset-cpu">Reset</button>
    <div id="cpu" style="width:600px;height:300px;">
    </div>"""

    js += """
    <script type="text/javascript" charset="utf-8">
      var options_cpu = {
          title: 'Processor Utilization',
          xaxis: {
              title: 'Time',
              tickFormatter: myDateFormatter
          },
          yaxis: {
              title: 'Percent',
              min: 0,
              max: 100
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
              var o = Object.extend(Object.clone(options_cpu), opts || {});
              return Flotr.draw(
                  $('cpu'),
                  [
                      {
                          label: 'idle',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'interrupt',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'nice',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'softirq',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'steal',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'system',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'user',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                      {
                          label: 'wait',
                          data: [ %s ],
                          lines: { show: true },
                          points: { show: false }
                      },
                  ],
                  o
              );
          }

          var f = drawGraph();

          $('cpu').observe('flotr:select', function(evt) {
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

          $('reset-cpu').observe('click', function(){ drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>""" % (data['idle'], data['interrupt'], data['nice'],
                    data['softirq'], data['steal'], data['system'],
                    data['user'], data['wait'])

    return literal(js)

def get_cpu(host):
    ts = gmtime(time() - 86400)
    timestamp = datetime(ts.tm_year, ts.tm_mon, ts.tm_mday, ts.tm_hour,
                         ts.tm_min, ts.tm_sec)

    connection = Session.connection()
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
WHERE time > :timestamp
  AND host = :name
GROUP BY time
ORDER BY time ASC;"""), name=host, timestamp=timestamp)
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
