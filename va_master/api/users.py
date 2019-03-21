import json, yaml, subprocess, importlib, inspect, socket

import salt.client
import tornado.gen
import login, apps, services, documentation

from login import auth_only, create_user_api
from va_master.handlers.app_handler import handle_app_action
from salt.client import LocalClient 

def get_paths():
    paths = {
        'get' : {
            'panels/users' : {'function' : get_users, 'args' : ['handler', 'dash_user', 'users_type']},
            'panels/get_all_function_groups' : {'function' : get_all_function_groups, 'args' : ['datastore_handler']},
            'panels/get_user' : {'function' : get_user, 'args' : ['datastore_handler', 'username']},
        },
        'post' : {
            'panels/add_user_functions' : {'function' : add_user_functions, 'args' : ['datastore_handler', 'user', 'functions']},
            'panels/create_user_group' : {'function' : create_user_group, 'args' : ['datastore_handler', 'group_name', 'functions']},
            'panels/create_user_with_group' : {'function' : create_user_with_group, 'args' : ['handler', 'user', 'password', 'user_type', 'functions', 'groups']},
            'panels/delete_user' : {'function' : delete_user, 'args' : ['datastore_handler', 'user']}, 
            'panels/update_user' : {'function' : update_user, 'args' : ['datastore_handler', 'user', 'functions', 'groups', 'password']}, 

            'panels/delete_group' : {'function' : delete_user_group, 'args' : ['datastore_handler', 'group_name']},
            'panels/add_args' : {'function' : add_predefined_argument_to_func, 'args' : ['datastore_handler', 'username', 'func_path', 'kwargs']},
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
def get_users(handler, dash_user, user_type = 'users'):
    """Returns a list of users along with their allowed functions and user groups. """
    datastore_handler = handler.datastore_handler
    users = yield datastore_handler.get_users(user_type)
    result = []
    documented_functions = yield documentation.get_all_functions(handler)
    documented_functions = {
        func['func_name'] : func
    for func in documented_functions}
    print (documented_functions.keys())
    for u in users: 
        u_all_functions = yield datastore_handler.get_user_functions(u)

        for u_func in u_all_functions: 
            u_func.update(documented_functions.get(u_func['func_path'], {}))

        u_groups = [x.get('func_name') for x in u_all_functions if x.get('func_type', '') == 'function_group']
#        u_functions = [x.get('func_path') for x in u_all_functions if x.get('func_path')]
        user_data = {
            'user' : u, 
            'functions' : u_all_functions, 
            'groups' : u_groups
        }
        result.append(user_data)

    raise tornado.gen.Return(result)


@tornado.gen.coroutine
def get_user(datastore_handler, username):
    user = yield datastore_handler.get_object(object_type = 'user', username = username)
    functions = yield datastore_handler.datastore.get_recurse('function_doc')
    functions = {x['func_name'] : x for x in functions}
    for function in user['functions']:
        function['doc'] = functions[function['func_path']]
    raise tornado.gen.Return(user)

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
    if functions: 
        #If functions are pure strings, we convert them to {'func_path' : endpoint} dicts
        functions = [{'func_path' : x} if type(x) in [str, unicode] else x for x in functions]

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
    yield create_user_api(datastore_handler, user, password, user_type)
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


@tornado.gen.coroutine
def add_predefined_argument_to_func(datastore_handler, username, func_path, kwargs):
    user = yield datastore_handler.get_object(object_type = 'user', username = username)
    user_function = [x for x in user.get('functions', []) if x['func_path'] == func_path]
    if not user_function: 
        raise Exception('User does not have permissions to use ' + func_path)

    user_function = user_function[0]
    predef_args = user_function.get('predefined_arguments', {})
    predef_args.update(kwargs)
    user_function['predefined_arguments'] = predef_args
    yield datastore_handler.insert_object(object_type = 'user', username = username, data = user) 


@tornado.gen.coroutine
def get_predefined_arguments(datastore_handler, dash_user, func_name):
    user_func = [x for x in dash_user.get('functions', []) if x.get('func_name', x['func_path']) == func_name]
    if not user_func: 
        #Function is not in user_allowed functions but we assume it is in user_allowed. Maybe we need a better way to deal with this? 
        #TODO potentially find a betetr way to check this. 
        raise tornado.gen.Return({})
    user_func = user_func[0]
    predef_args = user_func.get('predefined_arguments', {})

    raise tornado.gen.Return(predef_args)
