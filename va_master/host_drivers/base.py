import salt.cloud
import abc, subprocess
import tornado.gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from va_master.utils.va_utils import bytes_to_int, int_to_bytes
import time

class Step(object):
    def __init__(self, name):
        self.name = name
        self.fields = []

    def add_field(self, id_, name, type, blank = False, option_choices = []): 
        new_field = {'type': type, 'id': id_, 'name': name, 'blank' : blank}
        if option_choices: 
            new_field['option_choices'] = option_choices
        self.fields.append(new_field)

    def add_fields(self, list_of_fields):
        for field in list_of_fields: 
            self.add_field(*field)

    def remove_fields(self, list_of_fields):
        for field in list_of_fields: 
            remove_field_index = [i for i in range(len(self.fields)) if self.fields[i]['id'] == field]
            if not remove_field_index: 
                print ('Tried to remove field ', field, ' but step does not contain it. Ignoring. ')
            remove_field_index = remove_field_index[0]
            self.fields.pop(remove_field_index)

    def add_str_field(self, id_, name):
        self.fields.append({'type': 'str', 'id': id_, 'name': name})

    def add_options_field(self, id_, name, choices = []):
        self.fields.append({'type': 'options', 'id': id_, 'name': name})

    def add_description_field(self, id_, name):
        self.fields.append({'type': 'description', 'id': id_, 'name': name})

    def validate(self, field_values):
        no_error = True
        for field in self.fields:
            if field['type'] in ('str', 'options'):
                # Check if exists at all
                if field['id'] not in field_values:
                    no_error = False
                else:
                    if len(field_values[field['id']]) < 1 and not field.get('blank'):
                        no_error = False
        return no_error

    def serialize(self):
        return {'name': self.name, 'fields': self.fields}

class StepResult(object):
    def __init__(self, errors, new_step_index, option_choices):
        self.errors = errors
        self.new_step_index = new_step_index
        self.option_choices = option_choices

    def set_option_choices(self, options):
        self.option_choices = options

    def serialize(self):
        return {'errors': self.errors, 'new_step_index': self.new_step_index,
            'option_choices': self.option_choices}

class DriverBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def  __init__(self, driver_name,  provider_template, profile_template, provider_name, profile_name, host_ip, key_name, key_path, datastore_handler):
        """
            Initialize method for the base driver. Subclassing drivers should be overwriting this and calling it with custom arguments if they are needed. 
            Takes care of the salt key, writing salt provider and profile configurations and so on. 


            Keyword arguments: 
            driver_name -- The computer friendly driver name, for server "my_driver". Used to find the driver when performing API requests. 
            provider_template -- A sample of how the provider configuration should look, with variable names which will be substituted from the profile_vars. 
            
            For instance, if you want to substitute an image, you should place VAR_IMAGE in the configuration, and if you're subclassing this class, the driver will replace it when generating the configuration. For custom template variables, you may need to add them to the self.provider_vars manually. 
            Example: 
                my_var = self.get_var_valule()
                self.provider_vars['MY_VAR'] = my_var
            And then you need to have MY_VAR in the provider template. 

            profile_template -- Same as provider_template, except with the profile instead. 
            provider_name -- The name of the provider for which the driver works, for server: openstack_provider, or aws_provider. 
            profile_name -- The name of the profile. The profile configuration is generated when a server is created, and the final name is profile_name + server_name. 
            host_ip -- The host ip of the machine that this runs on. It can and should be taken from the datastore (the deploy_handler passes it as a default kwarg).
            key_name -- The name of the keypair that will be used to connect to created servers. Example: va_master_key
            key_path - The entire path minus the key name. Example: /root/va_master_key/, if the full path is /root/va_master_key/va_master_key.pem. 
            datastore -- A Key/Value datastore. It can be None, but drivers that use it will misbehave. 
        """

        self.field_values = {
                'driver_name' : driver_name,
                'servers' : [],
                'defaults' : {},
            }
          
        self.app_fields = {} 
        self.datastore_handler = datastore_handler
        self.host_ip = host_ip

        self.key_path = key_path + ('/' * (not key_path[-1] == '/')) + key_name
        self.key_name = key_name

        self.provider_vars = {'VAR_THIS_IP' : host_ip, 'VAR_PROVIDER_NAME' : provider_name, 'VAR_SSH_NAME' : key_name, 'VAR_SSH_FILE' : self.key_path + '.pem'}
        self.profile_vars = {'VAR_PROVIDER_NAME' : provider_name, 'VAR_PROFILE_NAME' : profile_name, 'VAR_THIS_IP' : host_ip}

        self.provider_template = provider_template
        self.profile_template = profile_template
        self.client = AsyncHTTPClient()


    @abc.abstractmethod
    @tornado.gen.coroutine
    def driver_id(self):
        """
            The driver_id, recognized by the API and used in various methods. Example: my_driver
        """
        pass

    @abc.abstractmethod
    @tornado.gen.coroutine
    def friendly_name(self):
        """
            Friendly name, shown in the website. Example: My beautiful Driver
        """
        pass

    @tornado.gen.coroutine
    def new_provider_step_descriptions(self):
        """
            Shows these descriptions when creating a new provider. Does not need to be overwritten. 
        """
        raise tornado.gen.Return([
            {'name': 'Provider info'},
            {'name': 'Pick a Network'},
            {'name': 'Security'}
        ])


    @tornado.gen.coroutine
    def get_salt_configs(self, skip_provider = False, skip_profile = False, base_profile = False):
        """
            Creates configurations for salt implementations. Does not need to be overwritten. 
            
            Arguments: 
            skip_provider -- If set to True, it will not create the provider configuration. This happens when creating a server. 
            skip_profile -- If set to True, it will not create the profile configuration. 
            base_profile -- If set to True, it will not replace the profile name for the configuration. This happens when creating a new provider to create a base profile template. This template is then read when creating a new server, and the profile name is set. 
        """

        if not (self.profile_template or self.provider_template): 
            raise tornado.gen.Return(None)
        if not skip_profile: 
            self.field_values['profile_conf'] = self.profile_vars['VAR_PROFILE_NAME']
            for var_name in self.profile_vars: 
                if not (base_profile and var_name == 'VAR_PROFILE_NAME') and self.profile_vars[var_name]: 
                    self.profile_template = self.profile_template.replace(var_name, self.profile_vars[var_name])

 
        if not skip_provider: 
            self.field_values['provider_conf'] = self.provider_vars['VAR_PROVIDER_NAME'] 
            for var_name in self.provider_vars: 
                self.provider_template = self.provider_template.replace(var_name, self.provider_vars[var_name])

    @tornado.gen.coroutine
    def write_configs(self, skip_provider=False, skip_profile=False):
        """ 
            Writes the saved configurations. If any of the arguments are set, the corresponding configuration will not be written. Does not need to be overwritten 
        """
        if not skip_provider and self.provider_template: 
            with open('/etc/salt/cloud.providers.d/' + self.provider_vars['VAR_PROVIDER_NAME'] + '.conf', 'w') as f: 
                f.write(self.provider_template)
        if not skip_profile and self.profile_template:
             profile_conf_dir =  '/etc/salt/cloud.profiles.d/' + self.profile_vars['VAR_PROFILE_NAME'] + '.conf'
             self.field_values['profile_conf_dir'] = profile_conf_dir
             with open(profile_conf_dir, 'w') as f: 
                f.write(self.profile_template)


    @tornado.gen.coroutine
    def get_steps(self):
        """ 
            These are the arguments entered when creating a new provider, split into separate steps. Does not need to be overwritten, but probably should be in order to add other types of fields. You can just call this in your implementation and add fields to whichever step you want. 
        """

        provider_info = Step('Provider info')
        provider_info.add_fields([
            ('provider_name', 'Name for the host', 'str'),
            ('username', 'Username', 'str'),
            ('password', 'Password', 'str'),
            ('location', "Enter the host's location", 'str')
        ])


        net_sec = Step('Network & security group')
        net_sec.add_fields([
            ('netsec_desc', 'Current connection info', 'description'),
            ('network', 'Pick network', 'options'),
            ('sec_group', 'Pick security group', 'options'),
        ])


        imagesize = Step('Image & size')
        imagesize.add_fields([
            ('image', 'Image', 'options'),
            ('size', 'Size', 'options'),
        ])

        self.steps = [provider_info, net_sec, imagesize]
        raise tornado.gen.Return(self.steps)

    @tornado.gen.coroutine
    def get_networks(self):
        """ 
            Gets a list of all the networks for the specific implementation. This _needs_ to be overwritten. 
        """
        networks = [] 
        raise tornado.gen.Return(networks)

    @tornado.gen.coroutine
    def get_sec_groups(self):
        """ 
            Gets a list of all the security groups for the specific implementation. This _needs_ to be overwritten. 
        """
       	sec_groups =[] 
    	raise tornado.gen.Return(sec_groups)

    @tornado.gen.coroutine
    def get_images(self):
        """ 
            Gets a list of all the images used to create servers. This _needs_ to be overwritten. 
        """
        try:
            cl = salt.cloud.CloudClient(path = '/etc/salt/cloud')
            provider_name = self.provider_vars['VAR_PROVIDER_NAME']
            images = cl.list_images(provider = provider_name)[provider_name]
            images = images[images.keys()[0]]
            images = [images[x]['name'] for x in images]
        except: 
            import traceback
            print ('There was an error in get_images() in the base driver for %s. ' % (provider_name))
            traceback.print_exc()
            images = ['No images']
        raise tornado.gen.Return(images)

    @tornado.gen.coroutine
    def get_sizes(self):
        """     
            Gets a list of all sizes (flavors) used to create servers. This _needs_ to be overwritten. 
        """
        try:
            cl = salt.cloud.CloudClient(path = '/etc/salt/cloud')
            provider_name = self.provider_vars['VAR_PROVIDER_NAME']
            sizes = cl.list_sizes(provider = provider_name)[provider_name]
            sizes = sizes[sizes.keys()[0]]
            sizes = [x['name'] for x in sizes]
        except: 
            import traceback
            print ('There was an error in get_sizes() in the base driver for %s. ' % (provider_name))
            traceback.print_exc()
            sizes = ['No sizes']
        raise tornado.gen.Return(sizes)

    @tornado.gen.coroutine
    def server_action(self, provider, server_name, action):
        """ 
            Performs an action for the server. This function is a stub of how such a function _could_ look, but it depends on implementation. This _needs_ to be overwritten. 
        """
        server_action = {
            'delete' : 'delete_function', 
            'reboot' : 'reboot_function', 
            'start' : 'start_function', 
            'stop' : 'stop_function', 
        }
        if action not in server_action: 
            raise tornado.gen.Return({'success' : False, 'message' : 'Action not supported : ' + action})

        success = server_action[action](server_name)
        raise tornado.gen.Return({'success' : True, 'message' : ''})


    @tornado.gen.coroutine
    def get_provider_status(self, provider):
        """ 
            Tries to estabilish a connection with the provider. You should overwrite this method so as to properly return a negative value if the provider is inaccessible. 
        """
        raise tornado.gen.Return({'success' : True, 'message': ''})


    @tornado.gen.coroutine
    def get_servers(self, provider):
        """
            Gets a list of servers in the following format. The keys are fairly descriptive. used_ram is in mb, used_disk is in GB
        """
        servers =  [{
            'hostname' : '',
            'ip' : 'n/a',
            'size' : '',
            'status' : 'SHUTOFF',
            'provider' : '',
            'used_ram' : 0,
            'used_cpu': 0,
            'used_disk' : 0,

        }]
        raise tornado.gen.Return(servers)
       

    @tornado.gen.coroutine
    def get_provider_data(self, provider, get_servers = True, get_billing = True):
        """ 
            Returns information about usage for the provider and servers. The format of the data is in this function. This should be overwritten so you can see this data on the overview.
         """
        try: 
            provider_data = {
                'servers' : [], 
                'provider_usage' : {},
            }
            #Functions that connect to provider here. 
        except Exception as e: 
            provider_data['status'] = {'success' : False, 'message' : 'Could not get data. ' + e}
            raise tornado.gen.Return(provider_data)

        provider_usage =  {
            'max_cpus' : 0, 
            'used_cpus' : 0, 
            'max_ram' : 0,  # in MB
            'used_ram' : 0, # still in MB
            'max_disk' : 0, # in GB this time
            'used_disk' : 0, 
            'free_disk' : 0, 
            'max_servers' : 0, 
            'used_servers' : 0,
        }
        provider_usage['free_cpus'] = provider_usage['max_cpus'] - provider_usage['used_cpus']
        provider_usage['free_ram'] = provider_usage['max_ram'] - provider_usage['used_ram']

        servers = yield self.get_servers(self, provider)

        provider_info = {
            'servers' : servers,
            'provider_usage' : provider_usage,
            'status' : {'success' : True, 'message': ''}
        }
        raise tornado.gen.Return(provider_data)

    @tornado.gen.coroutine
    def validate_field_values(self, step_index, field_values, options = {}):
        """ 
            Validates and saves field values entered when adding a new provider. This does not need to be overwritten, but you may want to do so. 

            Arguments: 
                step_index -- The current step that is being evaluated. The first (or 0th) step is after the driver has been chosen. 
                field_values -- The results that are being evaluated. 

            When the last step has been reached (the steps are defined in the get_steps() method), the results are evaluated, and everything that has been saved to self.field_values will be saved to the datastore and then used for performing server actions, or creating servers. Make sure to add any custom values there. 
        """
        if step_index < 0:
            raise tornado.gen.Return(StepResult(
                errors=[], new_step_index=0, option_choices=options
            ))

        elif step_index == 0:
            for key in field_values: 
                if field_values[key]: 
                    self.field_values[key] = field_values[key]

            self.provider_vars['VAR_USERNAME'] = field_values.get('username', '')
            self.provider_vars['VAR_PASSWORD'] = field_values.get('password', '')

            yield self.get_salt_configs(skip_profile = True)
            yield self.write_configs(skip_profile = True)	

            self.field_values['networks'] = yield self.get_networks()
            self.field_values['sec_groups'] = yield self.get_sec_groups()

            self.field_values['location'] = field_values.get('location', 'va_master')
            self.provider_vars['VAR_LOCATION'] = field_values.get('location', '')
            options.update({
                    'network': self.field_values['networks'],
                    'sec_group': self.field_values['sec_groups'],
                })

            raise tornado.gen.Return(StepResult(
                errors = [], new_step_index =1,
                option_choices = options
            ))

        elif step_index == 1:
            self.profile_vars['VAR_NETWORK_ID'] = field_values['network']
            self.profile_vars['VAR_SEC_GROUP'] = field_values['sec_group']

            self.field_values['defaults']['network'] = field_values['network']
            self.field_values['defaults']['sec_group'] = field_values['sec_group']

            self.field_values['images'] = yield self.get_images()
            self.field_values['sizes']= yield self.get_sizes()

            options.update({
                    'image': self.field_values['images'],
                    'size': self.field_values['sizes'],
            })
            raise tornado.gen.Return(StepResult(
                errors =[], new_step_index =2, option_choices = options
            ))
        else: 
            self.profile_vars['VAR_IMAGE'] = field_values['image']
            self.profile_vars['VAR_SIZE'] = field_values['size']

            self.field_values['defaults']['image'] = field_values['image']
            self.field_values['defaults']['size'] = field_values['size']

            if self.provider_template and self.profile_template:
                yield self.get_salt_configs(base_profile = True)
                yield self.write_configs()	

            raise tornado.gen.Return(StepResult(
                errors = [], new_step_index = -1, option_choices = options
            ))


    @tornado.gen.coroutine
    def create_minion(self, provider, data):
        """
            Creates a minion from the provider data received from the datastore, and from data received from the panel. 
            
            Arguments: 
            provider - The datastore information about the provider. It's important that it has the profile_conf_dir value, which is the base profile configuration. 
            data - Data about the image. It's a dictionary with the following information: 
                'role': The role with which the server can be recognized, for instance va-directory
                'image': The image used to create the server, for instance VAInstance
                'size': The size (flavor) used to create the server, for instance va-small
                'new_profile': The name of the profile, for instance my-directory
                'server_name': The name of the server, for instance my_directory

            This method will work with proper configurations and data, but only for salt-supported technology. You _need_ to overwrite this method if the technology of your driver does not work with salt. 
        """
        profile_dir = provider['profile_conf_dir']
        profile_template = ''

        with open(profile_dir) as f: 
            profile_template = f.read()

        self.profile_vars['VAR_ROLE'] = data.get('role', '')
        self.profile_vars['VAR_IMAGE'] = data['image']
        self.profile_vars['VAR_SIZE'] = data['size']
        self.profile_vars['VAR_NETWORK_ID'] = data['network']
        if '|' in data['network']: 
            self.profile_vars['VAR_NETWORK_ID'] = data['network'].split('|')[1]

        new_profile = data['server_name'] + '-profile'
        self.profile_vars['VAR_PROFILE_NAME'] = new_profile
        self.profile_vars['VAR_SEC_GROUP'] = 'default'
        self.profile_vars['VAR_USERNAME'] = data.get('username', 'admin')

        if self.profile_template:
            yield self.get_salt_configs(skip_provider = True)
            yield self.write_configs(skip_provider = True)

        #probably use salt.cloud somehow
        new_minion_cmd = ['salt-cloud', '-p', new_profile, data['server_name']]
        minion_apply_state = ['salt', data['server_name'], 'state.highstate']

        try:
            new_minion = subprocess.call(new_minion_cmd)
            if data.get('role'): 
                new_minion_state = subprocess.check_output(minion_apply_state)
        except Exception as e: 
            import traceback
            traceback.print_exc()

            raise Exception('Error creating minion. ' + e.message)

        raise tornado.gen.Return(True)


    @tornado.gen.coroutine
    def validate_app_fields(self, step, steps_fields = [], **fields):
        #These are passed by the handler, but we do not need them. 
        fields.pop('dash_user')
        fields.pop('path')
        fields.pop('method')

        step -= 1
        self.app_fields.update(fields)
    
        if fields.get('role'): 
            states = yield self.datastore_handler.get_states_and_apps()
            state = [x for x in states if x['name'] == fields.get('role')][0]
            self.app_fields['state'] = state
            state_fields = [x['name'] for x in state.get('fields', [])]
        else: 
            state_fields = []
        # steps_fields is a list of lists such that the index of an element is the required fields for that step. We check if the app_fields contain all of those. 
        if not steps_fields: 
            steps_fields = [['role', 'server_name'], state_fields, ['sec_group', 'image', 'size', 'network']]
        if not all([x in self.app_fields.keys() for x in steps_fields[step]]):
            error_msg = 'Expected fields: %s, but only have data for: %s. ' % (steps_fields[step], self.app_fields.keys())
            print ('Fields expected are : ', steps_fields[step], ' but have : ', self.app_fields.keys())
            print ('Entire fields data : ', fields)
            raise Exception(error_msg)
    
        raise tornado.gen.Return(self.app_fields)
