from yamswui.tests import *

class TestPostgresqlController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='postgresql', action='index'))
        # Test response...
