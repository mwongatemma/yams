from webhelpers.html import literal

from uuid import uuid4

class Flotr:
    def __init__(self, data=None, title=None, xlabel=None, ylabel=None,
                 ymax=None, legend=None, width=600, height=300):
        self.data = data

        if title is not None:
            self.title = title
        else:
            self.title = ''

        self.legend = legend

        if xlabel is not None:
            self.xlabel = xlabel
        else:
            self.xlabel = ''

        if ylabel is not None:
            self.ylabel = 'title: \'%s\',' % ylabel
        else:
            self.ylabel = ''

        if ymax is None:
            self.ymax = ''
        else:
            self.ymax = 'max: %d,' % ymax

        self.width = width
        self.height = height

        self.button_name = 'id' + uuid4().hex
        self.options_name = 'id' + uuid4().hex
        self.div_name = 'id' + uuid4().hex

    def code_button(self):
        return """    <button id="%s">Reset</button>
    <div id="%s" style="width:%dpx;height:%dpx;"></div>""" % \
                (self.button_name, self.div_name, self.width, self.height)

    def code_draw(self):
        return """        function myDraw() {
            function drawGraph(opts) {
                var o = Object.extend(Object.clone(%s), opts || {});
                return Flotr.draw(
                    $('%s'),
                    [
%s
                    ],
                    o
                );
            }

            var f = drawGraph();

            $('%s').observe('flotr:select', function(evt) {
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

            $('%s').observe('click', function() { drawGraph() });

        }""" % (self.options_name, self.div_name, self.data_series(),
                self.div_name, self.button_name)

    def code_options(self):
        return """       var %s = {
            title: '%s',
            xaxis: {
                title: '%s',
                tickFormatter: myDateFormatter
            },
            yaxis: {
                %s
                %s
                min: 0
            },
            legend: {
                position: 'nw',
                labelFormatter: myLabelFunc
            },
            mouse: {
                track: true,
                lineColor: 'purple',
                sensibility: 1000,
                trackDecimals: 2,
                trackFormatter: function(obj) {
                    return myDateFormatter(obj.x) + ', ' + obj.y;
                }
            },
            selection: { mode: 'x' }
        };""" % (self.options_name, self.title, self.xlabel, self.ylabel,
                 self.ymax)

    def code_script(self):
        return """    <script type="text/javascript" charset="utf-8">
 %s

        function myLabelFunc(label) {
            return label;
        }

        function myDateFormatter(ctime) {
            myDate = new Date();
            myDate.setTime(ctime);
            return myDate.toLocaleString();
        }

%s

        document.observe('dom:loaded', myDraw);
    </script>""" % (self.code_options(), self.code_draw())

    def data_series(self):
        raw_format = ''
        i = 0
        for datum in self.data:
            try:
                label = 'label: \'%s\',' % self.legend[i]
            except:
                label = ''
            if i > 0:
                raw_format +=""",
"""
            raw_format += """                        {
                            %s
                            data: [ %s ],
                            lines: { show: true },
                            points: { show: false }
                        }""" % (label, datum)
            i += 1
        return raw_format

    def javascript(self):
        if self.data is None or len(self.data) == 0:
            return None

        return literal("""%s
%s""" % (self.code_button(), self.code_script()))
