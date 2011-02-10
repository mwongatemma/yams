"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
# Import helpers as desired, or define your own, ie:
from yamswui.lib.cpu import code_cpu, code_cpu_n
from yamswui.lib.load import code_load
from yamswui.lib.postgresql import postgresql_backend, postgresql_xact
