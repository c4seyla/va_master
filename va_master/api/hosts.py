from .login import auth_only
import tornado.gen
import json
import panels

#@auth_only(user_allowed = True)
@tornado.gen.coroutine
def list_hosts(handler):
    hosts = yield handler.config.deploy_handler.list_hosts()
    print ('Host instances are : ', [host['instances'] for host in hosts])
    for host in hosts: 
        driver = yield handler.config.deploy_handler.get_driver_by_id(host['driver_name'])
        host['instances'] = yield driver.get_instances(host)

    handler.json({'hosts': hosts})


@tornado.gen.coroutine
def reset_hosts(handler):
    yield handler.config.deploy_handler.datastore.insert('hosts', [])


@tornado.gen.coroutine
def delete_host(handler):
    print ('Data : ', handler.data)
    host = handler.data['hostname']
    hosts = yield handler.config.deploy_handler.datastore.get('hosts')
    hosts = [x for x in hosts if not x['hostname'] == host]
    yield handler.config.deploy_handler.datastore.insert('hosts', hosts)

@auth_only
@tornado.gen.coroutine
def list_drivers(handler):
    drivers = yield handler.config.deploy_handler.get_drivers()
    out = {'drivers': []}
    for driver in drivers:
        driver_id = yield driver.driver_id()
        name = yield driver.friendly_name()
        steps = yield driver.get_steps()
        steps = [x.serialize() for x in steps]
        out['drivers'].append({'id': driver_id,
            'friendly_name': name, 'steps': steps})
    handler.json(out)

@auth_only
@tornado.gen.coroutine
def validate_newhost_fields(handler):
    ok = True
    try:
        body = json.loads(handler.request.body)
        driver_id = str(body['driver_id'])
        field_values = dict(body['field_values'])
        step_index = int(body['step_index'])

    except Exception as e:
        handler.json({'error': 'bad_body', 'msg' : e}, 400)
        raise tornado.gen.Return(None)

    found_driver = yield handler.config.deploy_handler.get_driver_by_id(driver_id)

    if found_driver is None:
        handler.json({'error': 'bad_driver'}, 400)
    else:
        try:
            driver_steps = yield found_driver.get_steps()
        except: 
            import traceback
            traceback.print_exc()
        if step_index >= len(driver_steps):
            handler.json({'error': 'bad_step'}, 400)
        else:
            if step_index < 0 or driver_steps[step_index].validate(field_values):
                try:
                    result = yield found_driver.validate_field_values(step_index, field_values)
                    if result.new_step_index == -1:
                        print ('Adding new host')
                        handler.config.deploy_handler.create_host(found_driver)
                    handler.json(result.serialize())
                except: 
                    import traceback
                    traceback.print_exc()
            else:
                handler.json({
                    'errors': ['Some fields are not filled.'],
                    'new_step_index': step_index,
                    'option_choices': None
                })


@auth_only
@tornado.gen.coroutine
def create_host(handler):
    try:
        body = json.loads(handler.request.body)
        host_name = str(body['host_name'])
        driver = str(body['driver_id'])
        field_values = dict(body['field_values'])
    except:
        handler.json({'error' 'bad_body'}, 400)
    else:
        handler.config.deploy_handler.create_host(host_name, driver, field_values)


@tornado.gen.coroutine
def get_host_info(handler):
    data = handler.data
    deploy_handler = handler.config.deploy_handler
    store = deploy_handler.datastore

    required_hosts = data.get('hosts')
    hosts = yield store.get('hosts')

    if required_hosts: 
        hosts = [host for host in hosts if host['hostname'] in required_hosts]

    hosts_info = []
    for host in hosts: 
        driver = yield deploy_handler.get_driver_by_id(host['driver_name'])

        info = yield driver.get_host_data(host)
        info['hostname'] = host['hostname']

        hosts_info.append(info)

    handler.json(hosts_info)

