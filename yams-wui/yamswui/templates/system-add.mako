<%inherit file="/base.mako" />

<%def name="head_tags()">
    <title>YAMS: Add System Under Monitor</title>
</%def>

    <h1>YAMS: Add System Under Monitor</h1>

    <form name="system_add" method="POST" action="/system/insert">
      System Name: <input type="text" name="name" />
      <input type="submit" name="submit" value="Submit" />
    </form>

    <p>
	  This name must match the host name used by collectd, otherwise no results
      will be returned by YAMS.
    </P.
