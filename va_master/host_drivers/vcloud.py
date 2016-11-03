from . import base
from .base import Step, StepResult
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import tornado.gen
import json
import subprocess

PROVIDER_TEMPLATE = '''VAR_PROVIDER_NAME:
    driver: vmware
    user: VAR_USER
    password: VAR_PASSWORD
    url: vdc.neocloud.mk/
'''

PROFILE_TEMPLATE = '''VAR_PROFILE_NAME:
    provider: VAR_PROVIDER_NAME
'''

class VCloudDriver(base.DriverBase):
    def __init__(self, provider_name = 'vcloud_provider', profile_name = 'vcloud_profile', host_ip = '192.168.80.39', key_name = '', key_path = '/root/openstack_key'):

        self.field_values = {
                'driver_name' : 'openstack',
            }
           

        if not key_name: 
            #probably use uuid instead
            key_name = 'openstack_key_name'

        self.key_path = key_path + ('/' * (not key_path[-1] == '/')) + key_name
        self.key_name = key_name

        provider_vars = {'VAR_PROVIDER_NAME' : provider_name, 'VAR_SSH_NAME' : key_name, 'VAR_SSH_FILE' : self.key_path + '.pem'}
        profile_vars = {'VAR_PROVIDER_NAME' : provider_name, 'VAR_PROFILE_NAME' : profile_name}
        super(VCloudDriver, self).__init__(PROVIDER_TEMPLATE, PROFILE_TEMPLATE, provider_vars, profile_vars)

    @tornado.gen.coroutine
    def driver_id(self):
        raise tornado.gen.Return('vcloud')

    @tornado.gen.coroutine
    def friendly_name(self):
        raise tornado.gen.Return('vcloud')

    @tornado.gen.coroutine
    def new_host_step_descriptions(self):
        raise tornado.gen.Return([
            {'name': 'Host info'},
        ])

    @tornado.gen.coroutine
    def get_salt_configs(self):
        yield super(VCloudDriver, self).get_salt_configs()
        
        provider_conf = '/etc/salt/cloud.providers.d/' + self.provider_vars['VAR_PROVIDER_NAME']
        profile_conf = '/etc/salt/cloud.profiles.d/' + self.profile_vars['VAR_PROFILE_NAME']

        with open(provider_conf, 'w') as f: 
            f.write(self.provider_template + '.conf')
        with open(profile_conf, 'w') as f: 
            f.write(self.profile_template + '.conf')

        self.field_values['provider_conf'] = self.provider_vars['VAR_PROVIDER_NAME'] 
        self.field_values['profile_conf'] = self.profile_vars['VAR_PROFILE_NAME']

    @tornado.gen.coroutine
    def get_steps(self):
        host_info = Step('Host info')
        host_info.add_field('hostname', 'Name for the host', type = 'str')
        host_info.add_field('host_url', 'URL for the server', type = 'str')
        host_info.add_field('username', 'Username', type = 'str')
        host_info.add_field('password', 'Password', type = 'str')

        raise tornado.gen.Return([host_info])


    @tornado.gen.coroutine
    def validate_field_values(self, step_index, field_values):
        if step_index < 0:
            raise tornado.gen.Return(StepResult(
                errors=[], new_step_index=0, option_choices={}
            ))

        elif step_index == 0:
            self.field_values['hostname'] = field_values['hostname']
            self.provider_vars['VAR_USERNAME'] = field_values['username']
            self.provider_vars['VAR_PASSWORD'] = field_values['password']
            self.provider_vars['VAR_URL'] =field_values['host_url']

            yield self.get_salt_configs()

            raise tornado.gen.Return(StepResult(
                errors=[], new_step_index=-1, option_choices={}
            ))

