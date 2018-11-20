import json

import salt.client
import tornado.gen
import login, apps, services

from login import auth_only, create_user_api
from va_master.handlers.app_handler import handle_app_action
from salt.client import LocalClient 

def get_paths():
    paths = {
        'get' : {
            'panels' : {'function' : get_panels, 'args' : ['handler', 'dash_user']}, 
            'panels/stats' : {'function' : get_panels_stats, 'args' : ['handler', 'dash_user']},
            'panels/get_panel' : {'function' : get_panel_for_user, 'args' : ['handler', 'server_name', 'panel', 'provider', 'handler', 'args', 'dash_user']},
            'panels/users' : {'function' : get_users, 'args' : ['handler', 'users_type']},
            'panels/get_all_functions' : {'function' : get_all_functions, 'args' : ['handler']},
            'panels/get_all_function_groups' : {'function' : get_all_function_groups, 'args' : ['datastore_handler']},
            'panels/get_services_and_logs' : {'function' : get_services_and_logs, 'args' : ['datastore_handler']},
        },
        'post' : {
            'panels/sync_salt_minions' : {'function' : sync_salt_minions, 'args' : ['datastore_handler', 'dash_user']},
            'panels/remove_orphaned_servers' : {'function' : remove_orphaned_servers, 'args' : ['datastore_handler']},
            'panels/add_user_functions' : {'function' : add_user_functions, 'args' : ['datastore_handler', 'user', 'functions']},
            'panels/create_user_group' : {'function' : create_user_group, 'args' : ['datastore_handler', 'group_name', 'functions']},
            'panels/create_user_with_group' : {'function' : create_user_with_group, 'args' : ['handler', 'user', 'password', 'user_type', 'functions', 'groups']},
            'panels/delete_user' : {'function' : delete_user, 'args' : ['datastore_handler', 'user']}, 
            'panels/update_user' : {'function' : update_user, 'args' : ['datastore_handler', 'user', 'functions', 'groups', 'password']}, 

            'panels/delete_group' : {'function' : delete_user_group, 'args' : ['datastore_handler', 'group_name']},

            'panels/get_panel' : {'function' : get_panel_for_user, 'args' : ['server_name', 'panel', 'provider', 'handler', 'args', 'dash_user']},
            'panels/new_panel' : {'function' : new_panel, 'args' : ['datastore_handler', 'server_name', 'role']},
            'panels/remove_panel' : {'function' : remove_panel, 'args' : ['datastore_handler', 'server_name', 'role', 'dash_user']},

            'panels/action' : {'function' : panel_action, 'args' : ['handler', 'server_name', 'action', 'args', 'kwargs', 'module', 'dash_user']}, #must have server_name and action in data, 'args' : []}, ex: panels/action server_name=nino_dir action=list_users
            'panels/chart_data' : {'function' : get_chart_data, 'args' : ['server_name', 'args']},
            'panels/serve_file' : {'function' : salt_serve_file, 'args' : ['handler', 'server_name', 'action', 'args', 'kwargs', 'module']},
            'panels/serve_file_from_url' : {'function' : url_serve_file, 'args' : ['handler', 'server_name', 'url_function', 'module', 'args', 'kwargs']},
            'panels/get_panel_pdf' : {'function' : get_panel_pdf, 'args' : ['server_name', 'panel', 'pdf_file', 'provider', 'handler', 'args', 'kwargs', 'dash_user', 'filter_field']},
            'panels/export_table' : {'function' : export_table, 'args' : ['handler', 'panel', 'server_name', 'dash_user', 'export_type', 'table_file', 'args', 'provider', 'kwargs', 'filter_field']}
        }
    }
    return paths


def get_minion_role(minion_name = '*'):
    cl = LocalClient()
    role = cl.cmd(minion_name, 'grains.get', arg = ['role'])
    if minion_name != '*': 
        role = role[minion_name]
    return role


@tornado.gen.coroutine
def new_panel(datastore_handler, server_name, role):
    """ Adds the panel_name to the list of servers for the specified role. """

    yield datastore_handler.add_panel(server_name, role)


@tornado.gen.coroutine
def remove_orphaned_servers(datastore_handler):
    servers = yield datastore_handler.datastore.get_recurse('server/')
    providers = yield datastore_handler.datastore.get_recurse('providers/')
    providers = [x['provider_name'] for x in providers]

    for server in servers: 
        if server.get('provider_name', '') not in providers: 
            print ('Server ', server['server_name'], ' has : ', server.get('provider_name'), ' not in ', providers, ' deleting. ')
            yield datastore_handler.delete_object(object_type = 'server', server_name = server['server_name'])

@tornado.gen.coroutine
def sync_salt_minions(datastore_handler, dash_user):
    minions = get_minion_role('*')
    print ('Minions are : ', minions)
    unresponsive_minions = []
    for user_type in ['user', 'admin']: 
        for minion in minions: 
            panel_type = user_type + '_panel'
            panel = yield datastore_handler.get_object(object_type = panel_type, name = minions[minion])

            if not panel: 
                print ('No panel for ', minion, minions[minion])
                continue

            if not minions[minion]: 
                unresponsive_minions.append([minion, minions[minion]])
                continue

            print ('Panel : ', panel, ' for ', minions[minion])
            if minion not in panel['servers']: 
                print ('Panel servers are : ', panel['servers'], ' and adding ', minion)
                panel['servers'].append(minion)
            yield datastore_handler.insert_object(object_type = panel_type, name = minions[minion], data = panel)

        panels = yield datastore_handler.get_panels(user_type)
        print ('Now clearing panels')
        for panel in panels: 
            panel_type = user_type + '_panel'

            for server in panel['servers']:
                server_role = minions.get(server, '')

                if server not in minions or server_role != panel['name']: 
                    print (server, ' not in ', minions, ' so removing it. ')
                    panel['servers'] = [x for x in panel['servers'] if x != server]
            yield datastore_handler.insert_object(object_type = panel_type, name = panel['name'], data = panel)


    if unresponsive_minions: 
        raise tornado.gen.Return({'success' : True, 'message' : 'There were unresponsive minions. ', 'data' : unresponsive_minions})
    else: 
        raise tornado.gen.Return({'success' : True, 'message' : '', 'data' : {}})

@tornado.gen.coroutine
def remove_panel(datastore_handler, server_name, dash_user, role = None):
    server_role = role or get_minion_role(server_name)
    panel_type = dash_user['type'] + '_panel'
    panel = yield datastore_handler.get_object(object_type = panel_type, name = server_role)
    panel['servers'] = [x for x in panel['servers'] if x != server_name]
    panels = yield datastore_handler.insert_object(object_type = panel_type, name = server_role, data = panel)

@tornado.gen.coroutine
def list_panels(datastore_handler, dash_user):
    """ Returns a list of the panels for the logged in user. """
    panels = yield datastore_handler.get_panels(dash_user['type'])

    raise tornado.gen.Return(panels)

@tornado.gen.coroutine
def panel_action_execute(handler, server_name, action, args = [], dash_user = '', kwargs = {}, module = None, timeout = 30):
    """ 
    Executes the function from the action key on the minion specified by server_name by passing the args and kwargs. 
    If module is not passed, looks up the panels and retrieves the module from there. 
    """
    datastore_handler = handler.datastore_handler

    server = yield datastore_handler.get_object(object_type = 'server', server_name = server_name)

    if server.get('app_type', 'salt') == 'salt': 
        state = get_minion_role(server_name) 

        if dash_user.get('username'):
            user_funcs = yield datastore_handler.get_user_salt_functions(dash_user['username'])
            if action not in user_funcs and dash_user['type'] != 'admin':
                print ('Function not supported')
                raise Exception('User attempting to execute a salt function but does not have permission. ')

        if not module:
            state = yield datastore_handler.get_state(name = state)
            if not state: state = {'module' : 'openvpn'}
            module = state['module']

        cl = salt.client.LocalClient()
        print ('Calling salt module ', module + '.' + action, ' on ', server_name, ' with args : ', args, ' and kwargs : ', kwargs)
        result = cl.cmd(server_name, module + '.' + action , arg = args, kwarg = kwargs, timeout = timeout)
        print ('Result returned : ', result)

        result = result.get(server_name)
    #        raise Exception('Calling %s on %s returned an error. ' % (module + '.' + action, server_name))

    else: 
        result = yield handle_app_action(datastore_handler, server, action, args, kwargs)

    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def salt_serve_file(handler, server_name, action, args = [], dash_user = '', kwargs = {}, module = None):
    """Serves a file by using a salt module. The module function but be able to be called with range_from and range_to arguments. """
    datastore_handler = handler.datastore_handler
    server_info = yield apps.get_app_info(server_name)
    state = server_info['role']

    states = yield datastore_handler.get_states_and_apps()
    state = [x for x in states if x['name'] == state] or [{'module' : 'openvpn'}]
    state = state[0]

    if not module:
        module = state['module']

    yield handler.serve_file('test', salt_source = {"tgt" : server_name, "fun" : module + '.' + action, "arg" :  args})
    raise tornado.gen.Return({"data_type" : "file"})


#This is just temporary - trying to get backup download working properly. 
@tornado.gen.coroutine
def salt_serve_file_get(handler, server_name, action, hostname, backupnumber, share, path, module = None):
    datastore_handler = handler.datastore_handler
    server_info = yield apps.get_app_info(server_name)
    state = server_info['role']

    states = yield datastore_handler.get_states_and_apps()
    state = [x for x in states if x['name'] == state] or [{'module' : 'openvpn'}]
    state = state[0]

    if not module:
        module = state['module']

    kwargs = {
        'hostname' : hostname, 
        'backupnumber' : backupnumber, 
        'share' : share, 
        'path' : path, 
        'range_from' : 0,
    }

    yield handler.serve_file('test', salt_source = {"tgt" : server_name, "fun" : module + '.' + action, "kwarg" : kwargs})
    raise tornado.gen.Return({"data_type" : "file"})

    if not module:
        module = state['module']

    yield handler.serve_file('test', salt_source = {"tgt" : server_name, "fun" : module + '.' + action, "arg" :  args})
    raise tornado.gen.Return({"data_type" : "file"})


#This is just temporary - trying to get backup download working properly. 
@tornado.gen.coroutine
def url_serve_file(handler, server_name, url_function, module = None, args = [], kwargs = {}):
    """Serves a file by utilizing a url. The server must have a function which returns the url. This will call that function with the supplied args and kwargs. """
    datastore_handler = handler.datastore_handler
    server_info = yield apps.get_app_info(server_name)
    state = server_info['role']

    states = yield datastore_handler.get_states_and_apps()
    state = [x for x in states if x['name'] == state] or [{'module' : 'openvpn'}]
    state = state[0]

    if not module:
        module = state['module']

    cl = salt.client.LocalClient()
    url = cl.cmd(server_name, module + '.' + url_function, arg = args, kwarg = kwargs).get(server_name)

    yield handler.serve_file('test', url_source = url)
    raise tornado.gen.Return({"data_type" : "file"})

@tornado.gen.coroutine
def get_chart_data(server_name, args = ['va-directory', 'Ping']):
    """Gets chart data for the specified server."""
    cl = salt.client.LocalClient()

    result = cl.cmd(server_name, 'monitoring_stats.parse' , args)
    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def panel_action(handler, actions_list = [], server_name = '', action = '', args = [], kwargs = {}, module = None, dash_user = {}, call_functions = []):
    """Performs a list of actions on multiple servers. If actions_list is not supplied, will use the rest of the arguments to call a single function on one server. """
    #NOTE temporary fix for a bug - some forms return action as a list of one value, for example ['add_multiple_user_recipients'], where it should just be a string. 
    if type(action) == list: 
        if len(action) == 1: 
            action = action[0]

    if not actions_list: 
        actions_list = [{"server_name" : server_name, "action" : action, "args" : args, 'kwargs' : kwargs, 'module' : module}]

    servers = [x['server_name'] for x in actions_list]
    results = {x : None for x in servers}
    for action in actions_list:
        server_key = action['server_name']
        server_result = yield panel_action_execute(handler, server_name = action['server_name'], \
            dash_user = dash_user, \
            action = action['action'], \
            args = action['args'], \
            kwargs = action['kwargs'], \
            module = action['module'])
        results[server_key] = server_result

        #call_functions is a list of functions to call at the end of the action. Usually used with actions such as va_directory.add_user, which then wants to get the data of list_users
        if call_functions: 
            results[server_key] = {}
            for f in call_functions: 
                new_result = yield panel_action_execute(handler, server_name = action['server_name'], dash_user = dash_user, action = f['action'], module = action['module'])[server_key]
                results[server_key][f['table_name']] = new_result

    if len(results.keys()) == 1: 
        results = results[results.keys()[0]]
    raise tornado.gen.Return(results)



@tornado.gen.coroutine
def get_services_and_logs(datastore_handler):
    logfile = '/var/log/vapourapps/va-master.log'
    with open(logfile) as f:
        logs = f.read().split('\n')

    serv = yield services.get_all_checks()
    passing_services, crit_services, warn_services = 0, 0, 0
    info_logs, critical_logs = 0, 0

    info_severities = ['info', 'notices', 'debug', 'warning']
    crit_severities = ['err', 'crit', 'alert', 'emerg']

    for service in serv: 
        for check in serv[service]: 
            if check.get('Status', '') in ['passing']: 
                passing_services += 1
            elif check.get('Status', '') in ['critical']: 
                crit_services += 1
            elif check.get('Status') in ['warning']: 
                warn_services += 1

    for log in logs: 
        if not log: continue
        log = json.loads(log)
        if log['severity'] in info_severities: 
            info_logs += 1
        elif log['severity'] in crit_severities: 
            critical_logs += 1

    warning_logs = 10

    raise tornado.gen.Return({"critical_logs" : critical_logs, "info_logs" : info_logs, "warning_logs" : warning_logs, "passing_services" : passing_services, "critical_services" : crit_services, "warning_services" : warn_services})


@tornado.gen.coroutine
def get_panels_stats(handler, dash_user):
    datastore_handler = handler.datastore_handler
    providers = yield datastore_handler.list_providers()
    providers = [x for x in providers if x['provider_name'] != 'va_standalone_servers']
    servers = yield datastore_handler.datastore.get_recurse('server/')
    serv = yield services.list_services()
    serv = len(serv) - 1 #One service is the default consul one, which we don't want to be counted
#    vpn = yield apps.get_openvpn_users()
    vpn = {'users' : []}
    states = yield apps.get_states(handler, dash_user)
    
    result = {'providers' : len(providers), 'servers' : len(servers), 'services' : serv, 'vpn' : len(vpn['users']), 'apps' : len(states)}
    raise tornado.gen.Return(result)


@tornado.gen.coroutine
def get_panels(handler, dash_user):
    """Returns all panels for the logged in user. """
    datastore_handler = handler.datastore_handler
    panels = yield list_panels(datastore_handler, dash_user)

    panels.sort(key = lambda x: x.get('sort_key', ''))

    raise tornado.gen.Return(panels)

@tornado.gen.coroutine
def get_panel_for_user(handler, panel, server_name, dash_user, args = [], provider = None, kwargs = {}):
    """Returns the required panel from the server for the logged in user. A list of args may be provided for the panel. """

    datastore_handler = handler.datastore_handler
    user_panels = yield list_panels(datastore_handler, dash_user)
    state = get_minion_role(server_name) 
    #This is usually for get requests. Any arguments in the url that are not arguments of this function are assumed to be keyword arguments for salt.
    #TODO Also this is pretty shabby, and I need to find a better way to make GET salt requests work. 
    ignored_kwargs = ['datastore', 'handler', 'datastore_handler', 'drivers_handler', 'panel', 'instance_name', 'dash_user', 'method', 'server_name', 'path', 'args']
    if not kwargs: 
        kwargs = {x : handler.data[x] for x in handler.data if x not in ignored_kwargs}

    state = yield datastore_handler.get_state(name = state)
    action = 'get_panel'
    if type(args) != list and args: 
        args = [args]
    args = [panel] + args
    args = [state['module']] + args
    panel  = yield panel_action_execute(handler, server_name, action, args, dash_user, kwargs = kwargs, module = 'va_utils')
    raise tornado.gen.Return(panel)

@tornado.gen.coroutine
def export_table(handler, panel, server_name, dash_user, export_type = 'pdf', table_file = '/tmp/table', args = [], provider = None, kwargs = {}, filter_field = ''):
    table_func = 'va_utils.get_%s' % export_type
    table_file = table_file + '.' + export_type
    if not args: 
        args = list(args)
    cl = LocalClient()
    panel = yield get_panel_for_user(handler = handler, panel = panel, server_name = server_name, dash_user = dash_user, args = args, provider = provider, kwargs = kwargs)
    print ('Getting ', export_type, '  with filter : ', filter_field)
    result = cl.cmd('G@role:va-master', fun = table_func, tgt_type = 'compound', kwarg = {'panel' : panel, 'table_file' : table_file, 'filter_field' : filter_field})
    print ('Result is : ', result)
    yield handler.serve_file(table_file)


@tornado.gen.coroutine
def get_panel_pdf(handler, panel, server_name, dash_user, pdf_file = '/tmp/table.pdf', args = [], provider = None, kwargs = {}, filter_field = ''):
    if not args: 
        args = list(args)
    cl = LocalClient()
    panel = yield get_panel_for_user(handler = handler, panel = panel, server_name = server_name, dash_user = dash_user, args = args, provider = provider, kwargs = kwargs)
    result = cl.cmd('va-master', 'va_utils.get_pdf', kwarg = {'panel' : panel, 'pdf_file' : pdf_file, 'filter_field' : filter_field})
    if not result['va-master']: 
        yield handler.serve_file(pdf_file)
        raise tornado.gen.Return({'data_type' : 'file'})
    raise Exception('PDF returned a value - probably because of an error. ')

@tornado.gen.coroutine
def get_users(handler, user_type = 'users'):
    """Returns a list of users along with their allowed functions and user groups. """
    datastore_handler = handler.datastore_handler
    users = yield datastore_handler.get_users(user_type)
    result = []
    for u in users: 
        u_all_functions = yield datastore_handler.get_user_functions(u)
        u_groups = [x.get('func_name') for x in u_all_functions if x.get('func_type', '') == 'function_group']
        u_functions = [x.get('func_path') for x in u_all_functions if x.get('func_path')]
        user_data = {
            'user' : u, 
            'functions' : u_functions, 
            'groups' : u_groups
        }
        result.append(user_data)
    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def get_all_functions(handler):
    """Gets all functions returned by the get_functions methods for all the api modules and formats them properly for the dashboard. """
    functions = {m : handler.paths[m] for m in ['post', 'get']}
    states = yield handler.datastore_handler.get_states_and_apps()

    cl = LocalClient()

    all_salt_functions = cl.cmd('G@role:va-master', fun = 'sys.doc', tgt_type = 'compound')
    states_functions = {
        state['module'] : {x.split('.')[1] : {'doc' : all_salt_functions[x] or 'No description available. '} for x in all_salt_functions if x.startswith(state['module'])}
    for state in states}


    salt_functions = {state['module'] : {
        x : states_functions[state['module']][x] for x in states_functions[state['module']] if x in state.get('salt_functions', [])
    } for state in states}


    functions.update(salt_functions)

    functions = [
        { 
                'label' : f, 
                'options' : [
                    {
                        'label' : i, 
                        'value' : i, 
                        'description' : functions[f][i].get('doc') or functions[f][i]['function'].__doc__}
                    for i in functions[f]
                ] 
        } for f in functions]

    raise tornado.gen.Return(functions)


@tornado.gen.coroutine
def get_all_function_groups(datastore_handler):
    """Returns all user function groups from the datastore. """
    groups = yield datastore_handler.get_user_groups()
    print ('Groups are : ', groups)
    for g in groups:
        g['functions'] = [x.get('value') for x in g['functions']]
    raise tornado.gen.Return(groups)

@tornado.gen.coroutine
def update_user(datastore_handler, user, functions = [], groups = [], password = ''):
    """Updates a user, allowing an admin to change the password or set functions / user groups for the user. """
    if password: 
        yield datastore_handler.update_user(user, password)
    group_funcs = [datastore_handler.get_user_group(x) for x in groups]
    group_funcs = yield group_funcs
    [x.update({'func_type' : 'function_group'}) for x in group_funcs]
    functions += group_funcs

    yield datastore_handler.set_user_functions(user, functions)


#functions should have format [{"func_path" : "/panels/something", "func_type" : "salt"}, ...]
@tornado.gen.coroutine
def add_user_functions(datastore_handler, user, functions):
    """Adds the list of functions to the list of functions already in the datastore. """
    for i in range(len(functions)): 
        f = functions[i]
        if not type(f) == dict: 
            functions[i] = {'func_path' : f}

    yield datastore_handler.add_user_functions(user, functions)
    
@tornado.gen.coroutine
def create_user_group(datastore_handler, group_name, functions):
    """Creates a new user group with the specified group_name and list of functions. """
    yield datastore_handler.create_user_group(group_name, functions)

@tornado.gen.coroutine
def delete_user_group(datastore_handler, group_name):
    yield datastore_handler.delete_object('user_group', group_name = group_name)

@tornado.gen.coroutine
def create_user_with_group(handler, user, password, user_type, functions = [], groups = []):
    """Creates a new user and adds the functions and user groups to the user's allowed functions. """
    datastore_handler = handler.datastore_handler
    yield create_user_api(handler, user, password, user_type)
    all_groups = yield datastore_handler.get_user_groups()
    for g in groups: 
        if g: 
            required_group = [x for x in all_groups if x.get('func_name', '') == g]
            functions += required_group
        required_group = [x for x in all_groups if x.get('func_name', '') == g]
        functions += required_group

    yield add_user_functions(datastore_handler, user, functions)

@tornado.gen.coroutine
def delete_user(datastore_handler, user):
    """Deletes the user from the datastore. """
    yield datastore_handler.delete_user(user)
