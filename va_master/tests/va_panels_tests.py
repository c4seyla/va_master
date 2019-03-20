import time, sys, warnings
from va_integration_base import VATestBase

class VAPanelsTests(VATestBase):
    def __init__(self, *args, **kwargs):
        super(VAPanelsTests, self).__init__(*args, **kwargs)
        self.test_functions = [
            (self.test_list_panels, {}),
        ]

    def test_list_panels(self):
        panels = self.api.api_call('/panels', method='get', data={})

        self.assert_success(panels)

        required_keys = {'servers', 'panels', 'name', 'icon'}
        self.test_keys_in_set(panels['data'], required_keys, data_id_key = 'name')

t = VAPanelsTests(va_url = 'https://127.0.0.1:443')
t.do_tests()
