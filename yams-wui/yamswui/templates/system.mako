<!DOCTYPE html>
<title>YAMS: Systems Under Monitor</title>
<h1>YAMS: Systems Under Monitor</h1>
<hr/>
<p>
  <a href="/system/add">Add System Under Monitor</a>
</p>
<hr/>
<p>
  <table>
  % for system in c.systems:
    <tr>
      <td><a href="/system/detail/${system}">${system}</a></td>
    </tr>
  % endfor
  </table>
</p>
