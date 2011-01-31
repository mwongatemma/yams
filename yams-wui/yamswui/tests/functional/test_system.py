from yamswui.tests import *

class TestSystemController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='system', action='index'))
        # Test response...
