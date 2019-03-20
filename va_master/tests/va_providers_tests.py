import json, os, time, sys
from va_api import APIManager
from va_integration_base import VATestBase

import warnings

script_dir = os.path.dirname(os.path.realpath(__file__))

class VAProvidersTests(VATestBase):

    def __init__(self, *args, **kwargs):
        super(VAProvidersTests, self).__init__(*args, **kwargs)

        self.providers_config_file = script_dir + '/providers.json'

        self.test_functions = [
            (self.test_list_providers, {}),
            (self.test_providers, {}),
        ]


    def test_step(self, provider_name, driver_id, step_index, field_values):
        step_data = {
            'driver_id' : driver_id, 
            'step_index' : step_index, 
            'field_values' : field_values
        }
        validated = self.api.api_call('/providers/new/validate_fields', method = 'post', data =  step_data)
        self.assert_success(validated)

    def test_add_provider(self, provider_name, driver_id, steps):
        for step in steps:
            self.test_step(provider_name, driver_id, step['step_index'], step['field_values'])

        new_providers = self.api.api_call('/providers/info', method = 'post', data = {})
        self.assert_success(new_providers)
        new_providers_names = [x['provider_name'] for x in new_providers['data']]
        assert any([name == provider_name for name in new_providers_names]), "Provider %s not found in %s " % (provider_name, str(new_providers_names))

    def test_delete_provider(self, provider_name):
        delete_result = self.api.api_call('/providers/delete', method = 'post', data = {'provider_name' : provider_name})
        providers_after_delete = self.api.api_call('/providers/info', method = 'post', data = {})
        self.assert_success(providers_after_delete)
        providers_names = [x['provider_name'] for x in providers_after_delete['data']]
        assert (not any([name == provider_name for name in providers_names])), "Provider %s was supposed to be deleted, but is still in list: " % (provider_name, str(providers_names))

    def test_provider(self, provider_name, driver_id, steps):
        self.test_add_provider(provider_name, driver_id, steps)
        self.test_delete_provider(provider_name)


    def test_providers(self):
        providers_config = json.load(open(self.providers_config_file))
        for provider_config in providers_config:
            self.test_provider(**provider_config)

    def test_list_providers(self):
        providers = self.api.api_call('/providers/info', method='post', data={})
        self.assert_success(providers)

        required_keys = ['status', 'provider_name', 'servers', 'provider_usage']
        self.handle_keys_in_set(providers['data'], required_keys, data_id_key = 'provider_name')



t = VAProvidersTests(va_url = 'https://127.0.0.1:443')
t.do_tests()
