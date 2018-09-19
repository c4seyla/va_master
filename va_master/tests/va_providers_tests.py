import unittest
import time
import sys
from va_api import APIManager
from va_test_base import VATestClass

import warnings

providers_file = 'providers.json'

class VAProvidersTests(VATestClass):
#    api = APIManager(va_url='https://127.0.0.1/api',token='1a882c9e22c2462d95dcadb8a127bb8d', verify=False)
    api = APIManager(va_url='https://127.0.0.1:443', va_user='admin', va_pass='admin', verify=False)
    warnings = []

    def setUp(self):
        super(VAProvidersTests, self).setUp()
        with open(providers_file) as f: 
            providers = f.read()

        self.providers = json.loads(providers)


    def tearDown(self):
        if self.warnings: 
            print "\nWARNINGS\n================\n"
            warnings.warn('\n'.join(self.warnings))


    def handle_keys_in_set(self, data, required_keys, warning_keys = {}, data_id_key = ''):
        for d in data:
            self.assertTrue(set(d.keys()).issuperset(required_keys), msg = "Failed key test for " + d.get(data_id_key, str(d)) + " : " + str(d.keys()) + " don't contain " + str(required_keys))
            if not set(d.keys()).issuperset(warning_keys):
                warning_str = "Expected to see " + str(warning_keys) + " in " + d.get(data_id_key, str(d)) + " but didn't. "
                self.warnings.append(warning_str)



    def test_list_providers(self):
        providers = self.api.api_call('/providers/info', method='post', data={})
        self.assertTrue(providers['success'])

        required_keys = ['status', 'provider_name', 'servers', 'provider_usage']
        self.handle_keys_in_set(providers['data'], required_keys, data_id_key = 'provider_name')



    def test_add_all_providers(self):
        for provider in self.providers: 
            add_provider(provider)

    def _test_provider_from_conf(self, provider):
        for step in provider['steps']: 
            new_step = self.api.api_call('/providers/new/validate_fields', method = 'post', data = step)
            self.assertFalse(new_step['data']['errors'])

        all_providers = self.api.api_call('/providers/info', method = 'post', data = {})
        self.assertIn(provider, all_providers)


#    @unittest.skip('Skipping temporarily. ')
    def test_add_provider(self):
        providers =  self.api.api_call('/providers/info', method='post', data={})

        init_step = self.api.api_call('/providers/new/validate_fields', method='post', data={"driver_id" : "openstack", "field_values" : {}, "step_index" : -1})
        self.assertFalse(init_step['data']['errors'])

        info_step = self.api.api_call('/providers/new/validate_fields', method='post', data={"driver_id" : "openstack", "field_values" : {"provider_name" : "va-os", "username" : "admin", "tenant" : "admin", "provider_ip" : "192.168.80.16:5000", "region" : "RegionOne", "password" : "zilxii4g2j", "location" : "Skopje"}, "step_index" : 0})

        self.assertFalse(info_step['data']['errors'])

        network_step = self.api.api_call('/providers/new/validate_fields', method='post', data={"driver_id" : "openstack", "field_values" : {"sec_group" : "default|26811978-5201-41e5-8860-f71607928114", "network" : "public|9bd9a1c4-c46d-4976-b5a8-41c6c670bef2"}, "step_index" : 1})
        self.assertFalse(network_step['data']['errors'])

        image_step = self.api.api_call('/providers/new/validate_fields', method='post', data={"driver_id" : "openstack", "field_values" : {"size" : "va-medium", "image" : "debian-jessie"}, "step_index" : 2})
        self.assertFalse(image_step['data']['errors'])


        new_providers = self.api.api_call('/providers/info', method='post', data={})
        diff_providers = [x for x in new_providers if x not in providers]
        self.assertNotEqual(len(providers['data']), len(new_providers['data']))

#    @unittest.skip('Skipping temporarily. ')
    def test_delete_provider(self):
        providers = self.api.api_call('/providers/info', method='post', data={})
        result = self.api.api_call('/providers/delete', method='post', data={"provider_name": "va-os"})
        new_providers = self.api.api_call('/providers/info', method='post', data={})
        self.assertNotEqual(len(providers['data']), len(new_providers['data']))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(VAProvidersTests)
    unittest.TextTestRunner(verbosity=5).run(suite)
