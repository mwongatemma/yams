<%inherit file="/base.mako" />

<%def name="head_tags()">
    <title>YAMS: ${c.host}</title>
    <script type="text/javascript" src="/js/prototype-1.6.0.2.js"></script>
    <script type="text/javascript" src="/js/flotr-0.2.0-alpha.js"></script>
</%def>

    <h1>System Details: ${c.host}</h1>

    ${h.code_load(c.host)}
    ${h.code_cpu(c.host)}
% for cpu in c.lprocs:
    ${h.code_cpu_n(c.host, cpu)}
% endfor
