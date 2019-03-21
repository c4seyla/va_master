import time, sys
from va_api import APIManager
import warnings
from va_integration_base import VATestBase

class VAVPNTests(VATestBase):
    def __init__(self, *args, **kwargs):
        super(VAVPNTests, self).__init__(*args, **kwargs)

        self.test_functions = [
            (self.test_list_vpn_users, {}), 
            (self.test_get_vpn_status, {}),
        ]

    def test_list_vpn_users(self):
        a = self.api.api_call('/apps/vpn_users', method='get', data={})
        self.assert_success(a)

    def test_get_vpn_status(self):
        a = self.api.api_call('/apps/vpn_status', method='get', data={})
        self.assert_success(a)

t = VAVPNTests()
t.do_tests()
