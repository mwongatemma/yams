<!doctype html>
<html>
  <head>
    <title>YAMS: ${c.host}</title>
    <script type="text/javascript" src="/js/prototype-1.6.0.2.js"></script>
    <script type="text/javascript" src="/js/flotr-0.2.0-alpha.js"></script>
  </head>
  <body>
    <h1>System Details: ${c.host}</h1>

    <button id="reset-load">Reset</button>
    <div id="load" style="width:600px;height:300px;">
    </div>

  % if c.plot_load is True:
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
              var o = Object.extend(Object.clone(options_load), opts || {});
              return Flotr.draw(
                  $('load'),
                  [
                      {
                          label: '${c.load_dsnames[0]}',
                          data: [ ${c.load1} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: '${c.load_dsnames[1]}',
                          data: [ ${c.load5} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: '${c.load_dsnames[2]}',
                          data: [ ${c.load15} ],
                          lines: { show: true },
                          points: { show: true }
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
    </script>
  % endif

    <button id="reset-cpu">Reset</button>
    <div id="cpu" style="width:600px;height:300px;">
    </div>

  % if c.plot_cpu is True:
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
                  return myDateFormatter(obj.x) +', ' + obj.y + '%';
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
                          data: [ ${c.idle} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'interrupt',
                          data: [ ${c.interrupt} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'nice',
                          data: [ ${c.nice} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'softirq',
                          data: [ ${c.softirq} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'steal',
                          data: [ ${c.steal} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'system',
                          data: [ ${c.system} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'user',
                          data: [ ${c.user} ],
                          lines: { show: true },
                          points: { show: true }
                      },
                      {
                          label: 'wait',
                          data: [ ${c.wait} ],
                          lines: { show: true },
                          points: { show: true }
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
                  yaxis: {min: area.y1, max: area.y2, title: 'Percent' }
              });
          });

          $('reset-cpu').observe('click', function(){ drawGraph() });
      }

      document.observe('dom:loaded', myDraw);
    </script>
  % endif
  </body>
</html>
