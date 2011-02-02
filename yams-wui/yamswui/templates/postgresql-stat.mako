<%inherit file="/base.mako" />

<%def name="head_tags()">
    <title>YAMS: PostgreSQL ${c.host}</title>
    <script type="text/javascript" src="/js/prototype-1.6.0.2.js"></script>
    <script type="text/javascript" src="/js/flotr-0.2.0-alpha.js"></script>
</%def>

    <h1>PostgreSQL: ${c.host}</h1>

    ${h.postgresql_backend(c.host, c.dbname)}
    ${h.postgresql_xact(c.host, c.dbname)}
