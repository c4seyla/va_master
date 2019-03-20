import time
import sys
from va_api import APIManager

import warnings

class VATestBase(object):
    # test_functions is a list of tuples
    # the first element in the tuple is the function, the second element are the keyword arguments
    test_functions = []

    # function_results is a list of tuples
    # the first element is the function, the second is the output
    function_results = []


    def __init__(self, va_url, va_user = 'admin', va_pass = 'admin', token = ''):
        if token: 
            self.api = APIManager(va_url = va_url, token = token, verify = False)
        else: 
            self.api = APIManager(va_url = va_url, va_user='admin', va_pass='admin', verify=False)
        
    def assert_success(self, result):
        assert type(result) == dict, "Result returned was not a dictionary: %s" % (str(result))
        assert(result['success']), "Result was unsuccessful - %s" % (str(result))

    def do_tests(self):
        for func in self.test_functions:
            try:
                output = func[0](**func[1])
            except AssertionError as e:
                output = 'Assertion error at %s: %s' % (func[0].func_name, e.message)

            self.function_results.append((func[0].func_name, output))

        self.output_results()

    def output_results(self):
        print self.function_results #TODO print prettier

    def handle_keys_in_set(self, data, required_keys, warning_keys = {}, data_id_key = ''):
        for d in data: 
            assert set(d.keys()).issuperset(required_keys), "Failed key test for " + d.get(data_id_key, str(d)) + " : " + str(d.keys()) + " don't contain " + str(required_keys)
#            if not set(d.keys()).issuperset(warning_keys):
#                warning_str = "Expected to see " + str(warning_keys) + " in " + d.get(data_id_key, str(d)) + " but didn't. "
#                self.warnings.append(warning_str)


