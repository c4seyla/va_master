import time, sys
from va_api import APIManager
import warnings
from va_integration_base import VATestBase

class VAStatesTests(VATestBase):
    def __init__(self, *args, **kwargs):
        super(VAStatesTests, self).__init__(*args, **kwargs)

        self.test_functions = [
            (self.test_states_stores, {}),
        ]

    def test_states_stores(self):
        states = self.api.api_call('/states', method='get', data={})
        self.assert_success(states)
        required_keys = {'name', 'icon', 'dependency', 'version', 'path', 'description'}
        warning_keys = {'module', 'panels'}

        self.test_keys_in_set(states['data'], required_keys, warning_keys, data_id_key = 'name')

t = VAStatesTests(va_url = 'https://127.0.0.1:443')
t.do_tests()
