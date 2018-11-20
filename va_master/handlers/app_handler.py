import tornado, sys, subprocess, importlib


@tornado.gen.coroutine
def install_new_app(datastore_handler, app_json, path_to_app):
    success = yield install_app_package(path_to_app)
    if success: 
        yield add_app_to_store(datastore_handler, app_json)

@tornado.gen.coroutine
def remove_app(datastore_handler, app_name):
    success = yield uninstall_app_package(app_name)
    if success: 
        yield remove_app_from_store(datastore_handler, app_name)

@tornado.gen.coroutine
def change_app_type(datastore_handler, app_name, app_type):
    server = yield datastore_handler.get_object(object_type = 'server', server_name = app_name)
    server['type'] = 'app'
    server['app_type'] = app_type

    yield datastore_handler.insert_object(object_type = 'server', server_name = app_name, data = server)

@tornado.gen.coroutine
def add_app_to_store(datastore_handler, app_json):
    yield datastore_handler.insert_object(object_type = 'app', app_name = app_json['name'], data = app_json)
    empty_panel = {'admin' : [], 'user' : []}
    for user_type in ['user', 'admin']: 
        panel = {
            'name' : app_json['name'],
            'icon' : app_json['icon'],
            'servers' : [],
            'panels' : app_json.get('panels', empty_panel)[user_type]
        }
        yield datastore_handler.store_panel(panel, user_type)

@tornado.gen.coroutine
def remove_app_from_store(datastore_handler, app_name):
    yield datastore_handler.datastore.delete(app_name)

@tornado.gen.coroutine
def install_app_package(path_to_app):
    result = yield handle_app_package(path_to_app, 'install')
    raise tornado.gen.Return(result)

@tornado.gen.coroutine
def remove_app_package(path_to_app):
    result = yield handle_app_package(path_to_app, 'uninstall')
    raise tornado.gen.Return(result)

#After consulting several forum/SE threads, this is the prefered way to install pip packages.
#Evidently, pip.main has been moved to an internal command and is unsafe.
@tornado.gen.coroutine
def handle_app_package(path_to_app, action = 'install'):
    if action not in ['install', 'uninstall']:
        raise Exception('Attempted to handle app package with action: ' + str(action))

    install_cmd = [sys.executable, '-m', 'pip', 'install', path_to_app, '--upgrade']
    try:
        subprocess.call(install_cmd)
    except:
        raise tornado.gen.Return(False)

    raise tornado.gen.Return(True)


@tornado.gen.coroutine
def handle_app_action(datastore_handler, server, action, args, kwargs):
    app = yield datastore_handler.get_object('app', app_name = server['role'])
    app_action = app['functions'][action]
    app_kwargs = {x : server[x] for x in app_action.get('args', [])}
    kwargs.update(app_kwargs)

    app_module = app['module']
    app_module = importlib.import_module(app_module)

    result = getattr(app_module, action)(*args, **kwargs)
    raise tornado.gen.Return(result)
