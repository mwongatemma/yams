<%inherit file="/base.mako" />

<%def name="head_tags()">
    <title>YAMS: Systems Under Monitor</title>
</%def>

    <h1>YAMS: Systems Under Monitor</h1>
    <hr/>
    <p>
      <a href="/system/add">Add System Under Monitor</a>
    </p>
    <hr/>
    <p>
      <table border="1">
        <th>Host</th><th>Logical Processors</th>
      % for system in c.systems:
        <tr>
          <td><a href="/system/detail/${system.name}">${system.name}</a></td>
          <td>${system.lprocs}</a></td>
        </tr>
      % endfor
      </table>
    </p>
