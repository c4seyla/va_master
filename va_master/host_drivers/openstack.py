try: 
    from . import base
    from .base import Step, StepResult
except: 
    import base
    from base import Step, StepResult

from base import bytes_to_int, int_to_bytes

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import tornado.gen
import json, datetime, subprocess, os

import novaclient
from novaclient import client

from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneauth1 import identity
from keystoneauth1.identity import v3

PROVIDER_TEMPLATE = '''VAR_PROVIDER_NAME:
  minion:
    master: VAR_THIS_IP
    master_type: str
  # The name of the configuration profile to use on said minion
  driver: openstack
  auth_version: 2
  compute_name: nova
  protocol: ipv4
  ssh_key_name: VAR_KEYPAIR_NAME
  ssh_key_file: VAR_SSH_FILE
  ssh_interface: private_ips
  use_keystoneauth: True
  user: VAR_USERNAME
  tenant: VAR_TENANT
  password: VAR_PASSWORD
  identity_url: VAR_IDENTITY_URL
  compute_region: VAR_REGION
'''


PROFILE_TEMPLATE = '''VAR_PROFILE_NAME:
    provider: VAR_PROVIDER_NAME
    image: VAR_IMAGE
    size: VAR_SIZE
    securitygroups: VAR_SEC_GROUP
    ssh_username: VAR_USERNAME

    minion:
        master: VAR_THIS_IP
        grains:
            role: VAR_ROLE
    networks:
      - fixed:
          - VAR_NETWORK_ID 
'''

class OpenStackDriver(base.DriverBase):
    def __init__(self, provider_name = 'openstack_provider', profile_name = 'openstack_profile', host_ip = '192.168.80.39', key_name = 'va_master_key', key_path = '/root/va_master_key', datastore_handler = None):
        """ The standard issue init method. Borrows most of the functionality from the BaseDriver init method, but adds a self.regions attribute, specific for OpenStack hosts. """

        kwargs = {
            'driver_name' : 'openstack',
            'provider_template' : PROVIDER_TEMPLATE,
            'profile_template' : PROFILE_TEMPLATE,
            'provider_name' : provider_name,
            'profile_name' : profile_name,
            'host_ip' : host_ip,
            'key_name' : key_name,
            'key_path' : key_path, 
            'datastore_handler' : datastore_handler
            }
        self.regions = ['RegionOne', ]
        self.keypair_name = ''
        super(OpenStackDriver, self).__init__(**kwargs)

    @tornado.gen.coroutine
    def driver_id(self):
        """ Pretty simple. """
        raise tornado.gen.Return('openstack')

    @tornado.gen.coroutine
    def friendly_name(self):
        """ Pretty simple """
        raise tornado.gen.Return('OpenStack')


    @tornado.gen.coroutine
    def export_env_variables(self, username, tenant, url, password):
        """ A method I made to help call nova commands, but not being used actively. Keeping it here in case it's needed some time. """

        os.environ['OS_USERNAME'] = self.provider_vars['VAR_USERNAME']
        os.environ['OS_PROJECT_NAME'] = self.provider_vars['VAR_TENANT']
        os.environ['OS_AUTH_URL'] = self.provider_vars['VAR_IDENTITY_URL']
        os.environ['PASSWORD'] = self.provider_vars['VAR_PASSWORD']

    @tornado.gen.coroutine
    def get_steps(self):
        """ Adds a provider_ip, tenant and region field to the first step. These are needed in order to get OpenStack values. """

        steps = yield super(OpenStackDriver, self).get_steps()
        steps[0].add_fields([
            ('provider_ip', 'Keystone provider_ip:port (xx.xx.xxx.xx:35357)', 'str'),
            ('tenant', 'Tenant', 'str'),
            ('region', 'Region', 'options', False, {'region' : self.regions}),
        ])
        self.steps = steps
        raise tornado.gen.Return(steps)

    @tornado.gen.coroutine
    def get_token(self, field_values):
        """ 
            Gets a token from an OpenStack server which is used to get OpenStack values 

            Arguments: 
            field_values -- A dictionary containing information about the provider. It must have a provider_ip, username, password and tenant value. The provider_ip should be the base ip with the port, for instance 192.168.80.16:5000. 
        """

        provider, username, password, tenant = (field_values['provider_ip'],
            field_values['username'], field_values['password'],
            field_values['tenant'])
        url = 'http://%s/v2.0/tokens' % provider

        data = {
            'auth': {
                'tenantName': tenant,
                'passwordCredentials': {
                    'username': username,
                    'password': password
                }
            }
        }
        req = HTTPRequest(url, 'POST', body=json.dumps(data), headers={
            'Content-Type': 'application/json'
        })
        try:
            resp = yield self.client.fetch(req)
        except:
            import traceback
            print ('Error getting token with %s. ' % (url))
            traceback.print_exc()
            raise Exception('Error getting openstack token on %s. ' % (url))
        body = json.loads(resp.body)
        token = body['access']['token']['id']
        services = {}
        for serv in body['access']['serviceCatalog']:
            for endpoint in serv['endpoints']:
                if 'publicURL' not in endpoint: continue
                services[serv['type']] = endpoint['publicURL']
        raise tornado.gen.Return((token, services))


    @tornado.gen.coroutine
    def get_openstack_value(self, token_data, token_value, url_endpoint, method = 'GET', data = {}):
        """
            Gets a specified value by using the OpenStack REST api. 

            Arguments: 
            token_data -- The token data from which we can extract the URLs for various resources. This is the data received with the get_token() method. 
            token_value -- The resource that we need to take. Check the OpenStack REST API documentation for reference, or some of this driver's methods which use this (get_networks, get_images etc. )
            url_endpoint -- The specific values we want to get. It varies from resource to resource so again, check the OpenStack documentation, or the other methods. 
        """

        url = token_data[1][token_value]
        req = HTTPRequest('%s/%s' % (url, url_endpoint), method, headers={
            'X-Auth-Token': token_data[0],
            'Accept': 'application/json'
        })
        if data: 
            req.data = data
        try:
            resp = yield self.client.fetch(req)
        except:
            import traceback;
            print ('Error getting openstack value for url %s and endpoint %s. ' % (url, url_endpoint))
            traceback.print_exc()
            raise Exception('Error getting openstack value for endpoint %s. ' % (url_endpoint))

        result = json.loads(resp.body)
        raise tornado.gen.Return(result)


    @tornado.gen.coroutine
    def create_keypair(self, username, password, tenant, host_ip):
        auth_url = 'http://' + host_ip + '/v2.0'
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=auth_url, username=username, password=password, project_name=tenant)
        sess = session.Session(auth=auth)
        nova_cl = client.Client('2.0', session=sess)

#        nova = client.Client('2', username, password, tenant, 'http://' + host_ip + '/v2.0')
#        sess = session.Session = 
        with open(self.key_path + '.pub') as f: 
            key = f.read()
        try:
            keypair = nova_cl.keypairs.create(name = self.keypair_name, public_key = key)
        except Exception as e:
            import traceback
            print ('Error creating keypair with name %s and key %s. ' % (self.keypair_name, key))
            traceback.print_exc()
            #raise Exception('Error creating a nova keypair with name %s. Message was: %s. ' % (self.keypair_name, e.message))


    @tornado.gen.coroutine
    def get_networks(self):
        """ Gets the networks using the get_openstack_value() method. """
        try: 
            tenants = yield self.get_openstack_value(self.token_data, 'identity', 'projects')
            tenant = [x for x in tenants['projects'] if x['name'] == self.field_values['tenant']][0]

        except: 
            tenants = yield self.get_openstack_value(self.token_data, 'identity', 'tenants')
            tenant = [x for x in tenants['tenants'] if x['name'] == self.field_values['tenant']][0]
          

        tenant_id = tenant['id']

        networks = yield self.get_openstack_value(self.token_data, 'network', 'v2.0/networks?tenant_id=%s'%(tenant_id))
        networks = ['|'.join([x['name'], x['id']]) for x in networks['networks']]
        raise tornado.gen.Return(networks)

    @tornado.gen.coroutine
    def get_sec_groups(self):
        """ Gets the security groups using the get_openstack_value() method. """
       	sec_groups = yield self.get_openstack_value(self.token_data, 'compute', 'os-security-groups')
        sec_groups = ['|'.join([x['name'], x['id']]) for x in sec_groups['security_groups']]
        raise tornado.gen.Return(sec_groups)

    @tornado.gen.coroutine
    def get_images(self):
        """ Gets the images using the get_openstack_value() method. """
        images = yield self.get_openstack_value(self.token_data, 'image', 'v2.0/images')
        print ('Images are : ', images)
        images = [x['name'] for x in images['images']]
        raise tornado.gen.Return(images)

    @tornado.gen.coroutine
    def get_sizes(self):
        """ Gets the sizes using the get_openstack_value() method. """
        sizes = yield self.get_openstack_value(self.token_data, 'compute', 'flavors')
        sizes = [x['name'] for x in sizes['flavors']]
        raise tornado.gen.Return(sizes)


    @tornado.gen.coroutine
    def get_servers(self, provider):
        """ Gets various information about the servers so it can be returned to provider_data. The format of the data for each server follows the same format as in the base driver description """
        try:
            self.token_data = yield self.get_token(provider)

            flavors = yield self.get_openstack_value(self.token_data, 'compute', 'flavors/detail')
            flavors = flavors['flavors']

            nova_servers = yield self.get_openstack_value(self.token_data, 'compute', 'servers/detail')
            nova_servers = nova_servers['servers']

            try: 
                tenants = yield self.get_openstack_value(self.token_data, 'identity', 'projects')
                tenant = [x for x in tenants['projects'] if x['name'] == provider['tenant']][0]

            except: 
                tenants = yield self.get_openstack_value(self.token_data, 'identity', 'tenants')
                tenant = [x for x in tenants['tenants'] if x['name'] == provider['tenant']][0]
             

            tenant_id = tenant['id']
            tenant_usage = yield self.get_openstack_value(self.token_data, 'compute', 'os-simple-tenant-usage/' + tenant_id)# + '?start=2017-02-02T09:49:58')
            tenant_usage = tenant_usage['tenant_usage']
#            print ('Usage is : ', tenant_usage)
            servers = [
                {
                    'hostname' : x['name'], 
                    'ip' : x['addresses'][x['addresses'].keys()[0]][0].get('addr', 'n/a'),
                    'size' : f['name'],
                    'used_disk' : y['local_gb'], 
                    'used_ram' : y['memory_mb'], 
                    'used_cpu' : y['vcpus'],
                    'status' : x['status'], 
                    'cost' : 0,  #TODO find way to calculate costs
                    'estimated_cost' : 0,
                    'provider' : provider['provider_name'], 
                } for x in nova_servers for y in tenant_usage['server_usages'] for f in flavors if y['name'] == x['name'] and f['id'] == x['flavor']['id']
            ]
        except Exception as e: 
            print ('Cannot get servers. ')
            import traceback
            print traceback.print_exc()
            raise tornado.gen.Return([])
        raise tornado.gen.Return(servers)



    @tornado.gen.coroutine
    def get_provider_status(self, provider):
        """ Tries to get the token for the provider. If not successful, returns an error message. """
        try:
            self.token_data = yield self.get_token(provider)
        except Exception as e:
            raise tornado.gen.Return({'success' : False, 'message' : 'Error connecting to libvirt provider. ' + e.message})

        raise tornado.gen.Return({'success' : True, 'message' : ''})


    @tornado.gen.coroutine
    def get_provider_billing(self, provider):
        #TODO provide should have some sort of costing mechanism, and we multiply used stuff by some price. 

        total_cost = 0
        servers = yield self.get_servers(provider)

        servers.append({
            'hostname' : 'Other Costs',
            'ip' : '',
            'size' : '',
            'used_disk' : 0,
            'used_ram' : 0,
            'used_cpu' : 0,
            'status' : '',
            'cost' : total_cost,
            'estimated_cost' : 0, 
            'provider' : provider['provider_name'],
        })

        total_memory = sum([x['used_ram'] for x in servers]) * 2**20
        total_memory = int_to_bytes(total_memory)
        total_disk = sum([x['used_disk'] for x in servers]) * 2**30
        total_disk = int_to_bytes(total_disk)

        provider['memory'] = total_memory
        provider['hdd'] = total_disk

        for server in servers: 
            pass
            server['used_ram'] = int_to_bytes(server['used_ram'] * (2 ** 20))
            server['used_disk'] = int_to_bytes(server['used_disk'] * (2 ** 30))

        billing_data = {
            'provider' : provider, 
            'servers' : servers,
            'total_cost' : total_cost
        }
        raise tornado.gen.Return(billing_data)




    @tornado.gen.coroutine
    def get_provider_data(self, provider, get_servers = True, get_billing = True):
        """ Gets various data about the provider and all the servers using the get_openstack_value() method. Returns the data in the same format as defined in the base driver. """
        try:
            self.token_data = yield self.get_token(provider)

            try: 
                tenants = yield self.get_openstack_value(self.token_data, 'identity', 'projects')
                tenant = [x for x in tenants['projects'] if x['name'] == provider['tenant']][0]
            except: 
                tenants = yield self.get_openstack_value(self.token_data, 'identity', 'tenants')
                tenant = [x for x in tenants['tenants'] if x['name'] == provider['tenant']][0]

            tenant_id = tenant['id']

            limits = yield self.get_openstack_value(self.token_data, 'compute', 'limits')
            tenant_limits = yield self.get_openstack_value(self.token_data, 'volumev2', 'limits')

            limits = limits['limits']['absolute']
            tenant_limits = tenant_limits['limits']['absolute']
        except Exception as e: 
            import traceback
            print traceback.print_exc()
            provider_data = {
                'servers' : [],
                'limits' : {},
                'provider_usage' : {},
                'status' : {'success' : False, 'message' : 'Could not connect to the libvirt provider. ' + e.message}
            }
            raise tornado.gen.Return(provider_data)

        if get_servers: 
            servers = yield self.get_servers(provider)
        else: 
            servers = []

        provider_usage = {
            'max_cpus' : limits['maxTotalCores'],
            'used_cpus' : limits['totalCoresUsed'], 
            'free_cpus' : limits['maxTotalCores'] - limits['totalCoresUsed'], 
            'max_ram' : limits['maxTotalRAMSize'], 
            'used_ram' : limits['totalRAMUsed'],
            'free_ram' : limits['maxTotalRAMSize'] - limits['totalRAMUsed'], 
            'max_disk' : tenant_limits['maxTotalVolumeGigabytes'], 
            'used_disk' : tenant_limits['totalGigabytesUsed'], 
            'free_disk' : tenant_limits['maxTotalVolumeGigabytes'] - tenant_limits['maxTotalVolumeGigabytes'],
            'max_servers' : limits['maxTotalInstances'], 
            'used_servers' : limits['totalInstancesUsed'], 
            'free_servers' : limits['maxTotalInstances'] - limits['totalInstancesUsed']
        }

        provider_data = {
            'servers' : servers, 
            'provider_usage' : provider_usage,
            'status' : {'success' : True, 'message': ''}
        }
        raise tornado.gen.Return(provider_data)


    @tornado.gen.coroutine
    def get_driver_trigger_functions(self):
        conditions = ['domain_full', 'server_can_add_memory', 'server_can_add_cpu']
        actions = ['server_new_terminal', 'server_cpu_full', 'server_memory_full', 'server_set_status', 'server_cpu_critical', 'server_cpu_warning', 'server_cpu_ok', 'server_memory_ok', 'server_memory_warning', 'server_memory_critical', 'server_cpu_full_ok', 'server_memory_full_ok']
        return {'conditions' : conditions, 'actions' : actions}


    @tornado.gen.coroutine
    def server_action(self, provider, server_name, action):
        """ Performs server actions using a nova client. """
        try:
            message = "Action %s performed on %s successfuly. " % (action, server_name)
            provider_url = 'http://' + provider['provider_ip'] + '/v2.0'
            auth = identity.Password(auth_url=provider_url,
                   username=provider['username'],
                   password=provider['password'],
                   project_name=provider['tenant'])
            sess = session.Session(auth = auth, verify = False)
            nova = client.Client(2, session = sess)
#            nova = client.Client('2', provider['username'], provider['password'], provider['tenant'], provider_url)
            servers = nova.servers.list()
            server = [x for x in servers if x.name == server_name][0]
        except Exception as e:
            import traceback
            traceback.print_exc()

            raise Exception('Could not get server' + server_name + '. ' + e.message)
        try:
            success = getattr(server, action)()
        except Exception as e:
            import traceback
            traceback.print_exc()

            raise Exception('Action ' + action + ' was not performed on ' + server_name + '. Reason: ' + e.message)

        raise tornado.gen.Return({'success' : True, 'message' : message, 'data' : {}})



    @tornado.gen.coroutine
    def validate_field_values(self, step_index, field_values):
        """ Uses the base driver method, but adds the region tenant and identity_url variables, used in the configurations. """
        if step_index < 0:
    	    raise tornado.gen.Return(StepResult(
        		errors=[], new_step_index=0, option_choices={'region' : self.regions,}
    	    ))
        elif step_index == 0:
    	    self.token_data = yield self.get_token(field_values)
            os_base_url = 'http://' + field_values['provider_ip'] + '/v2.0'

            self.provider_vars['VAR_TENANT'] = field_values['tenant']
            self.provider_vars['VAR_IDENTITY_URL'] = os_base_url
            if not '/tokens' in self.provider_vars['VAR_IDENTITY_URL']: 
                self.provider_vars['VAR_IDENTITY_URL'] += '/tokens'
            self.provider_vars['VAR_REGION'] = field_values['region']

            self.keypair_name = field_values['provider_name'] + '_key'
            self.provider_vars['VAR_KEYPAIR_NAME'] = self.keypair_name
            try:
                yield self.create_keypair(field_values['username'], field_values['password'], field_values['tenant'], field_values['provider_ip'])
            except: 
                print ('Tried to create keypair for ', field_values['provider_ip'], ' but it exists. ')

        elif step_index == 1:
            for field in ['network', 'sec_group']:
                field_values[field] = field_values[field].split('|')[1]

        try:
            step_result = yield super(OpenStackDriver, self).validate_field_values(step_index, field_values)
        except:
            import traceback
            traceback.print_exc()
        raise tornado.gen.Return(step_result)


    @tornado.gen.coroutine
    def create_server(self, host, data):
        """ Works properly with the base driver method, but overwritten for bug tracking. """
        try:
            yield super(OpenStackDriver, self).create_minion(host, data)

            #Once a server is created, we revert the templates to the originals for creating future servers. 
            self.profile_template = PROFILE_TEMPLATE
            self.provider_template = PROVIDER_TEMPLATE
        except:
            import traceback
            traceback.print_exc()

