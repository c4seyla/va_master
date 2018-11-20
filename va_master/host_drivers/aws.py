from . import base
from .base import Step, StepResult
from base import bytes_to_int, int_to_bytes
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
import tornado.gen
import json

import subprocess, datetime, calendar

import boto3

PROVIDER_TEMPLATE = '''VAR_PROVIDER_NAME:
  id: VAR_AWS_ACCESS_KEY_ID 
  key: VAR_AWS_SECRET_ACCESS_KEY
  keyname: VAR_SSH_NAME
  private_key: VAR_SSH_FILE
  driver: ec2

  minion:
    master: VAR_THIS_IP
    master_type: str

  grains: 
    node_type: broker
    release: 1.0.1

  # The name of the configuration profile to use on said minion
  #ubuntu if deploying on ubuntu
  ssh_username: ubuntu

#  These are optional
  location: VAR_REGION
#  availability_zone: VAR_AVAILABILITY_ZONE
'''


PROFILE_TEMPLATE = '''VAR_PROFILE_NAME:
    provider: VAR_PROVIDER_NAME
    ssh_interface: public_ips 
    image: VAR_IMAGE
    size: VAR_SIZE
    securitygroup: VAR_SEC_GROUP'''


AWS_CONFIG_TEMPLATE = '''[profile VAR_PROVIDER_NAME]
aws_access_key_id=VAR_APP_ID
aws_secret_access_key=VAR_APP_KEY
region=VAR_REGION
output=json
'''

class AWSDriver(base.DriverBase):

    def __init__(self, datastore_handler = None, provider_name = 'aws_provider', profile_name = 'aws_profile', host_ip = '192.168.80.39', key_name = 'va_master_key', key_path = '/root/va_master_key'):
        kwargs = {
            'driver_name' : 'aws', 
            'provider_template' : PROVIDER_TEMPLATE, 
            'profile_template' : PROFILE_TEMPLATE, 
            'provider_name' : provider_name, 
            'profile_name' : profile_name, 
            'host_ip' : host_ip,
            'key_name' : key_name,
            'key_path' : key_path, 
            'datastore_handler' : datastore_handler,
        }
        self.aws_client = None

        self.image_options = ['ami-00c2af73', ]
        self.size_options = ['t1.micro', ]
        self.regions = ['ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-1', 'sa-east-1', 'us-east-1', 'us-west-1', 'us-west-2']

        super(AWSDriver, self).__init__(**kwargs)
        self.aws_config = AWS_CONFIG_TEMPLATE


    def get_session(self, provider):
        session = boto3.session.Session(aws_access_key_id = provider['aws_access_key_id'], aws_secret_access_key = provider['aws_secret_access_key'], region_name = provider['region'])
        return session
       

    def get_client(self, provider):
        session = self.get_session(provider)
        client = session.client('ec2')
        self.aws_client = client
        return client

    @tornado.gen.coroutine
    def driver_id(self):
        raise tornado.gen.Return('aws')

    @tornado.gen.coroutine
    def friendly_name(self):
        raise tornado.gen.Return('AWS')

    @tornado.gen.coroutine
    def new_provider_step_descriptions(self):
        raise tornado.gen.Return([
            {'name': 'Host Info'},
            {'name': 'Security and region'}, 
            {'name': 'Image and size'}, 
        ])

    @tornado.gen.coroutine
    def get_steps(self):
        """ Adds a provider_ip, tenant and region field to the first step. These are needed in order to get OpenStack values. """

        steps = yield super(AWSDriver, self).get_steps()
        steps[0].add_fields([
            ('region', 'Region', 'options'),
            ('aws_access_key_id', 'AWS access key IDD', 'str'),
            ('aws_secret_access_key', 'AWS secret access key', 'str'),
        ])
        self.steps = steps
        raise tornado.gen.Return(steps)

    @tornado.gen.coroutine
    def get_images(self):
        #ec2 hiccups at images for the moment, no idea why
        #images_result = self.aws_client.describe_images()
        #images = images_result['Images']
        return self.image_options

    @tornado.gen.coroutine
    def get_sizes(self):
        #TODO find a way to list sizes properly
        return self.size_options
    
    @tornado.gen.coroutine
    def get_sec_groups(self):
        sec_result = self.aws_client.describe_security_groups()
        sec_groups = sec_result['SecurityGroups']
        return [x['GroupName'] for x in sec_groups]
   
    @tornado.gen.coroutine
    def get_networks(self):
        net_result = self.aws_client.describe_network_interfaces()
        networks = net_result['NetworkInterfaces']
        networks = [x['NetworkInterfaceId'] for x in networks] or ['default']
        return networks

    @tornado.gen.coroutine
    def get_servers(self, provider):
        session = self.get_session(provider)
        client = self.get_client(provider)
        rs = session.resource('ec2')
        pricing = session.client('pricing')

        reservations = client.describe_instances()
        reservations = reservations['Reservations']
        if not reservations:
            raise tornado.gen.Return([])

        print ('Reservations are : ', reservations)
        instances = reservations[0].get('Instances', [])


        instance_hdd = lambda instance: sum([rs.Volume(i['Ebs']['VolumeId']).size for i in instance['BlockDeviceMappings']])
#        instance_hdd = lambda instance: instance['BLockDeviceMappings']

        #We create filters for each different instance_type so we can get their pricing information. 
        instance_types = [x['InstanceType'] for x in instances]
        filters = [{"Type" : "TERM_MATCH", "Field" : "instanceType", "Value" : x} for x in instance_types]
        filters.append({"Type" : "TERM_MATCH", "Field" : "productFamily", "Value" : "Compute Instance"})


        pricing_kwargs = {'ServiceCode' : 'AmazonEC2', 'Filters' : filters}
        pricing_data_page = pricing.get_products(**pricing_kwargs)

        pricing_data = [json.loads(p)['product']['attributes'] for p in pricing_data_page['PriceList']]

        new_pricing_data = []

        for element in pricing_data:
            if element['instanceType'] not in [x['instanceType'] for x in new_pricing_data]: 
                new_pricing_data.append(element)

        status_map = {
            'pending' : 'PENDING', 
            'running' : 'ACTIVE', 
            'stopped' : 'SHUTOFF', 
        }

        servers = [{
                    'hostname' : i['PublicDnsName'],
                    'ip' : i.get('PublicIpAddress', ''),
                    'size' : i['InstanceType'],
                    'used_disk' : instance_hdd(i),
                    'used_ram' : p['memory'],
                    'used_cpu' : int(p['vcpu']),
                    'status' : status_map.get(i['State']['Name'], i['State']['Name']),
                    'cost' : 0,  #TODO see if I can actually get the cost. 
                    'estimated_cost' : 0, 
                    'provider' : provider['provider_name'],
                } 
        for i in instances for p in new_pricing_data if i['InstanceType'] == p['instanceType']]

        print ('servers are ', servers)
        raise tornado.gen.Return(servers)

    @tornado.gen.coroutine
    def get_provider_data(self, provider, get_servers = True, get_billing = True):
        client = self.get_client(provider)
        provider_usage = {
            'total_disk_usage_gb' : 0, 
            'current_disk_usage_mb' : 0, 
            'cpus_usage' : 0
        }
        servers = []
        if get_servers:
            servers = yield self.get_servers(provider)
        provider_data = {
            'servers' : servers, 
            'provider_usage' : provider_usage, 
            'status' : {'success' : True, 'message' : ''},
        }
        raise tornado.gen.Return(provider_data)


    @tornado.gen.coroutine
    def get_provider_billing(self, provider):
        session = self.get_session(provider)
        cw = session.client('cloudwatch')
        
        now = datetime.datetime.now()
        number_days = calendar.monthrange(now.year, now.month)[1]

        start = datetime.datetime(day = 1, month = now.month, year = now.year)
        end = datetime.datetime(day = number_days, month = now.month, year = now.year)

        #This looks really iffy, but I think it works kinda ok. 

        result = cw.get_metric_statistics(Namespace = 'AWS/Billing', Dimensions = [{"Name" : "Currency", "Value" : "USD"}], MetricName = 'EstimatedCharges', StartTime = start, EndTime = end, Period = 60 * 60 * 24 * number_days, Statistics = ['Sum'])
        total_cost = result['Datapoints'][0]['Sum']

        total_cost = float("{0:.2f}".format(total_cost))
        servers = yield self.get_servers(provider)
        for server in servers: 
            server['used_disk'] = server['used_disk'] * (2**30)


        total_memory = sum([bytes_to_int(s['used_ram']) for s in servers])
        total_memory = int_to_bytes(total_memory)

        total_disk = sum([bytes_to_int(s['used_disk']) for s in servers])
        total_disk = int_to_bytes(total_disk)

        provider['memory'] = total_memory
        provider['hdd'] = total_disk

        servers.append({
            'hostname' : 'Other costs',
            'ip' : '',
            'size' : '',
            'used_disk' : 0,
            'used_ram' : 0,
            'used_cpu' : 0,
            'status' : '',
            'cost' : total_cost,
            'estimated_cost' : total_cost, 
            'provider' : provider['provider_name'],
        })


        billing_data = {
            'provider' : provider, 
            'servers' : servers,
            'total_cost' : total_cost
        }
        raise tornado.gen.Return(billing_data)
        

    @tornado.gen.coroutine
    def validate_field_values(self, step_index, field_values):
        """ Uses the base driver method, but adds the region tenant and identity_url variables, used in the configurations. """
        if step_index < 0:
            raise tornado.gen.Return(StepResult(
                errors=[], new_step_index=0, option_choices={'region' : self.regions,}
            ))
        elif step_index == 0:
            self.provider_vars['VAR_REGION'] = field_values['region']
            provider = {}
            for x in ['aws_access_key_id', 'aws_secret_access_key', 'region']:
                provider[x] = field_values[x]
                self.provider_vars['VAR_' + x.upper()] = field_values[x]

            self.get_client(provider)
            self.field_values.update(provider)
        try:
            step_result = yield super(AWSDriver, self).validate_field_values(step_index, field_values)
        except:
            import traceback
            traceback.print_exc()
        raise tornado.gen.Return(step_result)

#            Probablt not important right now but might come in handy. 
#            cmd_aws_import  = ['aws', 'ec2', 'import-key-pair', '--key-name', self.key_name, '--public-key-material',  'file://' + self.key_path + '.pub', '--profile', 'aws_provider']

    @tornado.gen.coroutine
    def create_server(self, host, data):
        """ Works properly with the base driver method, but overwritten for bug tracking. """
        try:
            yield super(AWSDriver, self).create_minion(host, data)

            #Once a server is created, we revert the templates to the originals for creating future servers. 
            self.profile_template = PROFILE_TEMPLATE
            self.provider_template = PROVIDER_TEMPLATE
        except:
            import traceback
            traceback.print_exc()

