import tornado.web, tornado.websocket
import tornado.gen

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor   # `pip install futures` for python2

from . import url_handler
from login import get_current_user, user_login
import json, datetime, syslog, pytz
import dateutil.relativedelta
import dateutil.parser

from va_master.datastore_handler import DatastoreHandler

def invalid_url(deploy_handler, path, method):
    raise Exception('Invalid URL : ' + path +' with method : ' + method)

class ApiHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers= 4)

    def initialize(self, config, include_version=False):
        self.config = config
        self.datastore = config.datastore
        self.data = {}
        self.paths = url_handler.gather_paths()
        self.datastore_handler = DatastoreHandler(datastore = self.datastore, datastore_spec_path = '/opt/va_master/consul_spec.json')

    def json(self, obj, status=200):
        self.set_header('Content-Type', 'application/json')
        self.set_status(status)
#        print ('I am in json with ', json.dumps(obj))
        self.write(json.dumps(obj))
        self.finish()


    def has_error(self, result):
        """ Returns True if result is a string which contains a salt error. May need more work, but is fine for now. """
        exceptions = [
            "The minion function caused an exception",
            "is not available",
            "Passed invalid arguments to",
            "ERROR",
        ]
        if type(result) == str: 
            return any([i in result for i in exceptions])
        else: return False


    def formatted_result(self, result):
        """ Returns True if the result is formatted properly. The format for now is : {'data' : {'field' : []}, 'success' : :True/False, 'message' : 'Information. Usually empty if successful. '} """
        try: 
            result_fields = ['data', 'success', 'message']
            result = (set (result.keys()) == set(result_fields))
            return result
        except: 
#            print ('Error with testing formatted result - probably is ok. ')
            return False


    @tornado.gen.coroutine
    def handle_user_auth(self):
        auth_successful = True
        try: 
            user = yield get_current_user(self)

            if not user: 
                self.json({'success' : False, 'message' : 'User not authenticated properly. ', 'data' : {}})
                auth_successful = False
            elif user['type'] == 'user' and path not in self.paths.get('user_allowed', []): 
                self.json({'success' : False, 'message' : 'User does not have appropriate privileges. ', 'data' : {}})
                auth_successful = False
        except Exception as e: 
            import traceback
            traceback.print_exc()

            self.json({'success' : False, 'message' : 'There was an error retrieving user data. ' + e.message, 'data' : {}})
            auth_successful = False
    
        raise tornado.gen.Return(auth_successful)   

    @tornado.gen.coroutine
    def handle_func(self, api_func, data):
        try:
            api_func, api_kwargs = api_func.get('function'), api_func.get('args')       
            api_kwargs = {x : data.get(x) for x in api_kwargs if data.get(x)} or {}
            print ('My kwargs is : ', api_kwargs, ' for ', api_func)

            print ('Calling with kwargs : ', api_kwargs)
            result = yield api_func(**api_kwargs)

            if type(result) == dict: 
                if result.get('data_type', 'json') == 'file' : 
                    raise tornado.gen.Return(None)
            if self.formatted_result(result) or self.data.get('plain_result'): 
                pass 
            elif self.has_error(result): 
                result = {'success' : False, 'message' : result, 'data' : {}} 
            else: 
                result = {'success' : True, 'message' : '', 'data' : result}
        except tornado.gen.Return: 
            raise
        except Exception as e: 
            import traceback
            traceback.print_exc()

            result = {'success' : False, 'message' : 'There was an error performing a request : ' + str(e.message), 'data' : {}}
        raise tornado.gen.Return(result)
        



    @tornado.gen.coroutine
    def exec_method(self, method, path, data):
        try:
            self.data = data
            self.data['method'] = method
            self.data['handler'] = self
            self.data['path'] = path
            self.data['datastore_handler'] = self.datastore_handler
            self.data['deploy_handler'] = self.config.deploy_handler
            self.data['datastore'] = self.config.deploy_handler.datastore


            user = yield get_current_user(self)
            data['dash_user'] = user

            api_func = self.fetch_func(method, path, data)
            if api_func['function'] not in [user_login]:#, url_serve_file_test]: 
                auth_successful = yield self.handle_user_auth(path)
                if not auth_successful: 
                    raise tornado.gen.Return()

            result = yield self.handle_func(api_func, data)

            yield self.log_message(path = path, data = data, func = api_func['function'], result = result)

            self.json(result)
        except: 
            import traceback
            traceback.print_exc()

    @tornado.gen.coroutine
    def get(self, path):
        args = self.request.query_arguments
        t_args = args
        for x in t_args: 
            if len(t_args[x]) == 1: 
                args[x] = args[x][0]
        try:
            result = yield self.exec_method('get', path, args)

        except: 
            import traceback
            traceback.print_exc()

    @tornado.gen.coroutine
    def delete(self, path):
        try: 
            data = json.loads(self.request.body)
            result = yield self.exec_method('delete', path, data)
        except: 
            import traceback
            traceback.print_exc()

    @tornado.gen.coroutine
    def post(self, path):
        try: 
            try: 
                if 'json' in self.request.headers['Content-Type']: 
                    try:
                        data = json.loads(self.request.body)
                    except: 
                        print ('Bad json in post request : ', self.request.body)
                        raise tornado.gen.Return()
                else:
                    data = {self.request.arguments[x][0] for x in self.request.arguments}
                    data.update(self.request.files)
            except ValueError: 
                import traceback
                traceback.print_exc()
                data = {}

            yield self.exec_method('post', path, data)

        except: 
            import traceback
            traceback.print_exc()


    @tornado.gen.coroutine
    def log_message(self, path, data, func, result):

        data = {x : str(data[x]) for x in data}
        user = yield url_handler.login.get_current_user(self)
        if not user: 
            user = {'username' : 'unknown', 'type' : 'unknown'}
        message = json.dumps({
            'type' : data['method'], 
            'function' : func.func_name,
            'user' : user.get('username', 'unknown'), 
            'user_type' : user['type'], 
            'path' : path, 
            'data' : data, 
            'time' : str(datetime.datetime.now()),
            'result' : result,
        })
        try:
            syslog.syslog(syslog.LOG_INFO | syslog.LOG_LOCAL0, message)
        except: 
            import traceback
            traceback.print_exc()


    @tornado.gen.coroutine
    def send_data(self, source, kwargs, chunk_size):
        offset = 0
        while True:
           print ('Calling ', source, ' with ', kwargs)
           data = source(**kwargs)
           offset += chunk_size
           if not data:
               break
           if type(data) == dict: #If using salt, it typically is formatted as {"minion" : "data"}
               data = data[kwargs.get('tgt')]
#           print ('Keys are : ', data.keys())

           self.set_header('Content-Type', 'application/octet-stream')
           self.set_header('Content-Disposition', 'attachment; filename=test.zip')

           self.write(unicode(data, "ISO-8859-1"))
           self.flush()
       


    @tornado.gen.coroutine
    def serve_file(self, source, chunk_size = 10**6, salt_source = []):
        try: 
            offset = 0

            if salt_source: 
                client = LocalClient()
                source = client.cmd
                kwargs = salt_source
            else:
                f = open(source, 'r')
                source = f.read
                kwargs = [chunk_size]

            yield self.send_data(source, kwargs, chunk_size)
#            self.finish()
        except: 
            import traceback
            traceback.print_exc()

class LogHandler(FileSystemEventHandler):
    def __init__(self, socket):
        self.socket = socket
        super(LogHandler, self).__init__()

    def on_modified(self, event):
        log_file = event.src_path
        with open(log_file) as f: 
            log_file = [x for x in f.read().split('\n') if x]
        try:
            last_line = log_file[-1]
            last_line = json.loads(last_line)

            msg = {"type" : "update", "message" : last_line}
#            self.socket.write_message(json.dumps(msg))
        except: 
            import traceback
            traceback.print_exc()


class LogMessagingSocket(tornado.websocket.WebSocketHandler):

    #Socket gets messages when opened
    @tornado.web.asynchronous
    @tornado.gen.engine
    def open(self, no_messages = 0, log_path = '/var/log/vapourapps/', log_file = 'va-master.log'):
        print ('Trying to open socket. ')
        try: 
            self.logfile = log_path + log_file
            try:
                with open(self.logfile) as f: 
                    self.messages = f.read().split('\n')
            except: 
                self.messages = []
            json_msgs = []
            for message in self.messages: 
                try:
                    j_msg = json.loads(message)
                except: 
                    continue
                json_msgs.append(j_msg)
            self.messages = json_msgs 
            yesterday = datetime.datetime.now() + dateutil.relativedelta.relativedelta(days = -1)

            init_messages = self.get_messages(yesterday, datetime.datetime.now())

            msg = {"type" : "init", "logs" : init_messages}
            self.write_message(json.dumps(msg))

            log_handler = LogHandler(self)
            observer = Observer()
            observer.schedule(log_handler, path = log_path)
            observer.start()
            print ('Started observer. ')
        except: 
            import traceback
            traceback.print_exc()

    def get_messages(self, from_date, to_date):
        messages = [x for x in self.messages if from_date < dateutil.parser.parse(x['timestamp']).replace(tzinfo = None) <= to_date]
        return messages

    def check_origin(self, origin): 
        return True

    @tornado.gen.coroutine
    def on_message(self, message): 
        try:
            message = json.loads(message)
        except: 
            self.write_message('Error converting message from json; probably not formatted correctly. Message was : ', message)
            raise tornado.gen.Return(None)

        try:
            from_date = message.get('from_date')
            date_format = '%Y-%m-%d'
            if from_date:
                from_date = datetime.datetime.strptime(from_date, date_format)
            else: 
                from_date = datetime.datetime.now() + dateutil.relativedelta.relativedelta(days = -2)

            to_date = message.get('to_date')
            if to_date: 
                to_date = datetime.datetime.strptime(to_date, date_format)
            else: 
                to_date = datetime.datetime.now()

            messages = self.get_messages(from_date, to_date)
            messages = {'type' : 'init', 'logs' : messages}
            self.write_message(json.dumps(messages))

        except: 
            import traceback
            traceback.print_exc()
