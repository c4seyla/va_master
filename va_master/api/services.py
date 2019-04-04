import requests, json, subprocess, os

import tornado.gen
from salt.client import LocalClient
import apps

consul_url = 'http://localhost:8500/v1'

consul_dir = '/etc/consul.d'

def get_paths():
    paths = {
        'get' : {
            'get_va_master_version' : {'function' : get_version, 'args' : ['handler']},

            'services' : {'function' : list_services, 'args' : []},
            'services/full_status' : {'function' : get_services_and_monitoring, 'args' : []},
            'services/by_status' : {'function' : get_services_with_status, 'args' : ['status']},
            'services/by_service' : {'function' : get_service, 'args' : ['service']},
            'services/get_monitoring_status' : {'function' : get_all_monitoring_data, 'args' : ['datastore_handler']},
            'services/get_services_table_data' : {'function' : get_services_table_data, 'args' : ['datastore_handler']},
            'services/get_services_with_checks' : {'function' : get_all_checks, 'args' : []},
            'services/get_service_presets' : {'function' : get_presets, 'args' : ['datastore_handler']},
        },
        'post' : {
            'services/add' : {'function' : add_services, 'args' : ['services', 'server']},
            'services/add_service_with_presets' : {'function' : add_service_with_presets, 'args' : ['datastore_handler', 'presets', 'server', 'name', 'address', 'tags', 'port']},

        },
        'delete' : {
            'services/delete' : {'function' : delete_service, 'args' : ['name']},
        }
    }
    return paths

def get_formatted_string_arguments(s):
    arguments = [x[1] for x in s._formatter_parser() if x[1]] #Using weird python string formatting methods ftw!
    return arguments

@tornado.gen.coroutine
def get_presets(datastore_handler):
    check_presets = yield datastore_handler.datastore.get_recurse('service_presets/')

    raise tornado.gen.Return(check_presets)

@tornado.gen.coroutine
def get_service_definition(service_name):
    service_path = '/etc/consul.d/%s.json' % (service_name)
    with open(service_path) as f: 
        service_definition = json.load(f)

    service_definition = service_definition.get('service', service_definition)

    raise tornado.gen.Return(service_definition)

@tornado.gen.coroutine
def get_all_service_definitions():
    services = yield list_services()
    services = services.keys()
    definitions = yield [get_service_definition(x) for x in services]
#    definitions = [{"name" : x, "definition" : services[x]} for x in services]
    raise tornado.gen.Return(definitions)

@tornado.gen.coroutine
def get_services_table_data(datastore_handler):
    """
        description: Returns Services in a format which is dashboard-friendly. 
        output: '{"name" : "service_name", "address": "127.0.0.1", "port" : 22, "check" : ["list", "of", "checks"], "tags" : ["list", "of", "tags"]}'
    """
    definitions = yield get_all_service_definitions()
    checks = yield get_all_checks()

    services = [x for x in definitions if x.get('name') != 'consul' and x.get('name')]

    for service in services: 
        check_results = [checks[x] for x in checks if x == service['name']][0]
        if len(check_results) != len(service['checks']):
            service['checks'] = [{
                'interval' : 'n/a',
                'name' : 'n/a',
                'id' : 'n/a',
                'timeout' : 'n/a',
                'Status' : 'Critical', 
                'Output' : 'Could not receive health check data for ' + service['name']
            }]
        else:
            for i in range(len(service['checks'])):
                service['checks'][i].update(check_results[i])

    services_table = [{
        'name' : s['name'], 
        'address' : s['address'], 
        'port' : s['port'], 
        'check' : [{'interval' : c.get('interval'), 'name' : c['id'], 'status' : c['Status'], 'output' : c.get('Output')} for c in s['checks']],
        'tags' : ', '.join(s['tags']), 
    } for s in services]

    presets = yield get_presets(datastore_handler)
    presets = [{"label" : x['name'], 'value' : x['name']} for x in presets]
    result = {'services' : services_table, 'presets' : presets}
    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def get_version(handler):
    version = handler.config.pretty_version()

    raise tornado.gen.Return(version)

#These two functions are for inside use in the API. 
def reload_systemctl():
    subprocess.call(['systemctl', 'daemon-reload'])

def restart_consul():
    subprocess.call(['consul', 'reload'])

@tornado.gen.coroutine
def get_services_and_monitoring():
    """
        description: Returns a list of all services as well as monitoring data from all connected monitoring minions.
    """
    services = yield list_services()
    result = yield get_all_monitoring_data()
    result.update(services)

    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def list_services():
    """description: Returns a list of services and their statuses from the consul REST API"""
    try:
        services_url = consul_url + '/catalog/services'
        services = requests.get(services_url)
        services = services.json()
    except: 
        import traceback
        print ('Error when getting services with %s' % (services_url))
        traceback.print_exc()
        raise Exception('There was an error attempting to list consul services. ')

    raise tornado.gen.Return(services)

@tornado.gen.coroutine
def get_all_checks():
    """
        description: Returns a list of services along with all their checks.
        output: 
          test_check: 
            - Node: va-master
              CheckID: "service:test_check"
              Name: "Service 'test_check' check"
              ServiceName: test_check
              Notes: ""
              ModifyIndex: 180652
              Status: passing 
              ServiceID: test_check
              Output: ""
              CreateIndex: 180652
        visible: True 
    """
    services = yield list_services()
    all_checks = yield {x : get_service(x) for x in services.keys()}
    raise tornado.gen.Return(all_checks)

@tornado.gen.coroutine
def get_services_with_status(status = 'passing'):
    """
        description: Returns a list of services with the specified status. 
        arguments: 
          - name: status
            type: string
            required: False
            default: passing
            example: passing
        output: 
          - Node: va-master
            CheckID: serfHealth
            Name: Serf Health Status
            ServiceName: ""
            Notes: ""
            ModifyIndex: 4
            Status: passing
            ServiceID: ""
            Output: Agent alive and reachable
            CreateIndex: 4}
          - Node: va-master
            CheckID: service:test_check
            Name: "Service 'test_check' check"
            ServiceName: test_check
            Notes: ""
            ModifyIndex: 180653
            Status: passing
            ServiceID: test_check
            Output: ""
            CreateIndex: 180652
        visible: True
    """
    try:
        status_url = consul_url + '/health/state/%s' % (status)
        services = requests.get(status_url)
        services = services.json()
    except: 
        import traceback
        print ('Error when trying to get all services with status %s with url %s. ' % (status, status_url))
        traceback.print_exc()
        raise Exception('There was an error trying to get all services with status %s. ' % (status))

    raise tornado.gen.Return(services)

@tornado.gen.coroutine
def get_service(service):
    """
        description: Returns the service with the specified service name. 
    """
    try:
        service_url = consul_url + '/health/checks/%s' % (service)
        service = requests.get(service_url)
        service = service.json()
    except: 
        import traceback
        print ('Error trying to get data for service %s with url %s. ' % (status, service_url))
        traceback.print_exc()
        raise Exception('There was an error getting data for the service %s. ' % (service))

    raise tornado.gen.Return(service)

#Example for how to add services: 
#{"services": [{"name": "va-os", "tags": ["hostsvc", "web", "http"], "address": "192.168.80.16", "port": 5000, "check": {"id": "tcp", "name": "TCP connection to port", "tcp": "192.168.80.16:5000", "interval": "30s", "timeout": "10s"}}, {"name": "imconfus", "tags": ["hostsvc", "web", "http"], "address": "192.168.80.16", "port": 5000, "check": {"id": "tcp", "name": "TCP connection to port", "tcp": "192.168.80.16:5000", "interval": "30s", "timeout": "10s"}}]}


@tornado.gen.coroutine
def create_service_from_state(state_name, service_name, service_address, service_port, server_name):
    """Creates a service from the specified state. Not used currently. """
    all_states = yield datastore_handler.get_states_data()
    state = [x for x in all_states if x['name'] == state_name][0]

    state_service = state['service']
    services = state_service['services']
    for service in services: 
        for check in services[service]:
            for k in services[service][k]:
                if 'VAR_' in services[service][k]:
                    #Somehow do work with var
                    pass

    yield add_service_with_definition(service_definition, server_name)

#TODO check if the definition is alright, raise exception if not. 
@tornado.gen.coroutine
def add_service_with_definition(service_definition, service_name):
    """Adds a service with a definition. The definition has the standard consul service format. """
    service_text = json.dumps(service_definition)
    service_conf = consul_dir + '/%s.json' % service_name
    with open(service_conf, 'w') as f:
        f.write(service_text)

    reload_systemctl()
    restart_consul()

@tornado.gen.coroutine
def add_services(services, server):
    service_keys = ['name', 'tags', 'address', 'port', 'check']
    for key in service_keys:
        if not all([x.get(key) for x in services]):
            raise tornado.gen.Return({"success" : False, "message" : "All services need to define a value for the keys: " + ', '.join(service_keys) + '; Missing key : ' + key, 'data' : {}})

    yield add_service_with_definition(services, server)

@tornado.gen.coroutine
def generate_check_from_preset(preset, server, **kwargs):
    #We generate the check name as server_name_tcp or server_name_ping or whatever
    preset['id'] = '%s_%s' % (server, preset['name'])

    #If tcp is set, it's the address
    if preset.get('tcp'): 
        preset['tcp'] = kwargs['address']
    
    #If the preset uses a script, it should be formatted with the required arguments, like "script" : "ping -c1 {address} > /dev/null"
    if preset.get('script'):
        available_args = locals() #TODO not sure if locals() is the way to go. We should probably restrict the available variables...
        expected_args = get_formatted_string_arguments(preset['script'])
        available_args.update(kwargs)
        script_kwargs = {x : available_args[x] for x in expected_args} 
        preset['script'] = preset['script'].format(**script_kwargs)
        preset['args'] = preset.pop('script').split(' ')

    #Finally, if there are any keys in the preset that are empty, those are values we want to take from the dashboard, such as timeout, interval etc. 
    for key in preset: 
        if not preset[key]: 
            preset[key] = kwargs[key]

    raise tornado.gen.Return(preset)


#TODO finish function. 
#kwargs should hold values as such : {"address" : "", "interval" : "", "timeout" : "", "port" : 443, "tags" : [], "other_arg" : "something"}
@tornado.gen.coroutine
def add_service_with_presets(datastore_handler, presets, server, name = '', address = '', port = 443, tags = ''):
    """Creates services based on several presets and the info for the server. The info is required to get the id and the IP of the server. """

    name = name or server + '_services'
    port = port or 443
    tags = tags.split(',')

    if not address: 
        #If server is a string, and address is not set, we assume the server is a salt minion and we just take the data from mine. 
        minion_info = {}
        if type(server) in [str, unicode] and server: 
            minion_info = yield apps.get_app_info(server)


        if not minion_info: 
            raise Exception ("No `address` argument found, and %s did not return mine data (maybe it's not a minion?). Either use the ip address of the server or its minion id. " % (server))
        address = minion_info['ip4_interfaces']['eth0'][0]

    checks = []

    for preset in presets:
        preset = yield datastore_handler.get_object('service_preset', name = preset)

        check = yield generate_check_from_preset(preset, server, address = address, tags = tags, port = int(port))
        checks.append(check)

    service = {"service": {"name": name, "tags": tags, "address": address, "port": int(port), "checks" : [preset]}}
    yield add_service_with_definition(service, name)


@tornado.gen.coroutine
def get_presets(datastore_handler):
    presets = yield datastore_handler.datastore.get_recurse('service_presets/')
    for preset in presets:
        preset_arguments = [x for x in preset if not preset.get(x)]
        if preset.get('script'):
            preset_arguments += get_formatted_string_arguments(preset['script'])
        preset['arguments'] = preset_arguments

    raise tornado.gen.Return(presets)

@tornado.gen.coroutine
def delete_service(name):
    """Deletes all services for a server. """
    service_conf = consul_dir + '/%s.json' % name
    os.remove(service_conf)

    reload_systemctl()
    restart_consul()

@tornado.gen.coroutine
def get_all_monitoring_data(datastore_handler):
    """
        description: Returns all icinga data from connected monitoring minions. 
    """
    cl = LocalClient()
    result = cl.cmd('G@role:monitoring', fun = 'va_monitoring.icinga2', tgt_type = 'compound')
    monitoring_errors = []

    for minion in result: 
        if type(result[minion]) == str:
            print ('Error getting monitoring data for %s, salt returned %s, but will go on as usual. ' % (minion, result[minion]))
            monitoring_errors.append(minion)
            continue
        for host in result[minion]: 
            if 'va_master' in host['host_name']: 
                panel = {'icon' : 'fa-circle'}
            else: 
                panel = yield datastore_handler.find_panel_for_server(host['host_name'])
            host['icon'] = panel['icon']

    if monitoring_errors: 
        monitoring_errors = 'There was an error with the monitoring server(s): ' + ', '.join(monitoring_errors)
        result = {'success' : True, 'data' : result, 'message' : monitoring_errors}
    raise tornado.gen.Return(result)
