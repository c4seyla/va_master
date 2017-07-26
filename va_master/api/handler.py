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


def invalid_url(deploy_handler, path, method):
    raise Exception('Invalid URL : ' + path +' with method : ' + method)

class ApiHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers= 4)

    def initialize(self, config, include_version=False):
        self.config = config
        self.datastore = config.datastore
        self.data = {}
        try:
            self.paths = url_handler.gather_paths()
        except: 
            import traceback
            traceback.print_exc()
            return
        self.salt_client = None

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
    def exec_method(self, method, path, data):
        self.data = data
        self.data['method'] = method
        self.data['handler'] = self
        api_func = self.paths[method].get(path)

        print ('Getting a call at ', path, ' with data ', data, ' and will call function: ', api_func)

        if not api_func: 
            data = {'path' : path, 'method' : method}
            api_func = {'function' : invalid_url, 'args' : ['path', 'method']}
        elif api_func['function'] != user_login: 
            try: 
                yield self.log_message(path = path, data = data, func = api_func['function'])

                user = yield get_current_user(self)

                if not user: 
                    self.json({'success' : False, 'message' : 'User not authenticated properly. ', 'data' : {}})
                elif user['type'] == 'user' and path not in self.paths.get('user_allowed', []): 
                    self.json({'success' : False, 'message' : 'User does not have appropriate privileges. ', 'data' : {}})
            except: 
                import traceback
                traceback.print_exc()
        try:
            api_func, api_kwargs = api_func.get('function'), api_func.get('args')       
            api_kwargs = {x : data.get(x) for x in api_kwargs if data.get(x)} or {}
            print ('Kwargs are : ', api_kwargs)
            result = yield api_func(self.config.deploy_handler, **api_kwargs)
            if type(result) == dict: 
                if result.get('data_type', 'json') == 'file' : 
                    raise tornado.gen.Return(None)
#            print ('result is : ', result)
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

        self.json(result)

    @tornado.gen.coroutine
    def get(self, path):
        args = self.request.query_arguments
        t_args = args
        for x in t_args: 
            if len(t_args[x]) == 1: 
                args[x] = args[x][0]
        try:
#            result = yield self.exec_method('get', path, {x : args[x][0] for x in args})
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
                    data = json.loads(self.request.body)
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
    def log_message(self, path, data, func):

        data = {x : str(data[x]) for x in data}
        user = yield url_handler.login.get_current_user(self)
        message = json.dumps({
            'type' : data['method'], 
            'function' : func.func_name,
            'user' : user.get('username', 'unknown'), 
            'user_type' : user['type'], 
            'path' : path, 
            'data' : data, 
            'time' : str(datetime.datetime.now()),
        })
        try:
            syslog.syslog(syslog.LOG_INFO | syslog.LOG_LOCAL0, message)
        except: 
            import traceback
            traceback.print_exc()


    @tornado.gen.coroutine
    def serve_file(self, file_path, chunk_size = 4096):
        try: 
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=' + file_path)
            with open(file_path, 'r') as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    self.write(data)
            self.finish()
        except: 
            import traceback
            traceback.print_exc()

class LogHandler(FileSystemEventHandler):
    def __init__(self, socket):
        self.socket = socket
        super(LogHandler, self).__init__()

    def on_modified(self, event):
        log_file = event.src_path + '/va-master.log'
        print ('Log file is : ', log_file)
        with open(log_file) as f: 
            log_file = [x for x in f.read().split('\n') if x]
        last_line = json.loads(log_file[-1])
        try:
            msg = {"type" : "update", "message" : last_line}
            self.socket.write_message(json.dumps(msg))
        except: 
            pass


class LogMessagingSocket(tornado.websocket.WebSocketHandler):

    #Socket gets messages when opened
    @tornado.web.asynchronous
    @tornado.gen.engine
    def open(self, no_messages = 0, logfile = '/var/log/vapourapps/va-master.log'):
        print ('Trying to open socket. ')
        try: 
            self.logfile = logfile
            try:
                with open(logfile) as f: 
                    self.messages = f.read().split('\n')
            except: 
                self.messages = []
            json_msgs = []
            for message in self.messages: 
                try:
                    j_msg = json.loads(message)
                except: 
                    pass
                json_msgs.append(j_msg)
            self.messages = json_msgs 
            yesterday = datetime.datetime.now() + dateutil.relativedelta.relativedelta(days = -1)

            init_messages = self.get_messages(yesterday, datetime.datetime.now())
            msg = {"type" : "init", "logs" : init_messages}
            self.write_message(json.dumps(msg))

            log_handler = LogHandler(self)
            observer = Observer()
            observer.schedule(log_handler, path = '/'.join(logfile.split('/')[:-1]))
            observer.start()
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
