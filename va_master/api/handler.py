import tornado.web, tornado.websocket
import tornado.gen

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
#from . import status, login, hosts, apps, panels
from . import url_handler
from login import get_current_user
import json, datetime, syslog

#This will probably not be used anymore, keeping it here for reasons. 


class ApiHandler(tornado.web.RequestHandler):
    def initialize(self, config):
        self.config = config
        self.datastore = config.datastore
        self.data = {}

        self.paths = url_handler.gather_paths()

    def json(self, obj, status=200):
        self.set_header('Content-Type', 'application/json')
        self.set_status(status)
        print ('Writing ', obj)
        self.write(json.dumps(obj))
        self.finish()

    @tornado.gen.coroutine
    def exec_method(self, method, path, data):
        self.data = data
        try: 
            print ('User in handler: ')
            user = yield get_current_user(self)

            print ('User in handler is : ', user)
            if not user: 
                self.json({'success' : False, 'message' : 'User not authenticated properly. ', 'data' : {}})

        except: 
            import traceback
            traceback.print_exc()

#        try: 
        result = yield self.paths[method][path](self)
#            print ('Got result: ', result, ' for function ', api_func)
#        except tornado.gen.Return as e:
#            print ('Got Return')
#            print (e)
#            result = 'boobs'
#        except tornado.gen.Return:
#            raise
#        except Exception as e: 
#            result = json.loads(e.message)
#            import traceback
#            traceback.print_exc()
#            print ('Exception is : ', e)
        self.json(result)

    @tornado.gen.coroutine
    def get(self, path):
        args = self.request.query_arguments
        result = yield self.exec_method('get', path, {x : args[x][0] for x in args})

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
#            yield self.log_message(path, data)

        except: 
            import traceback
            traceback.print_exc()


    @tornado.gen.coroutine
    def log_message(self, path, data):

        user = yield url_handler.login.get_current_user(self)
        message = json.dumps({
            'type' : 'POST', 
            'user' : user['username'], 
            'user_type' : user['type'], 
            'path' : path, 
            'data' : data, 
            'time' : str(datetime.datetime.now()),
        })
#        message = '[info]Action:type=POST,user=' +  user['username'] + '|type=' +  user['type'] +'|path=' +  path + '|data=' + str(data) + '|time=' + str(datetime.datetime.now())

#        print ('Logging: ', message)
        syslog.syslog(syslog.LOG_INFO | syslog.LOG_LOCAL0, message)


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
        log_file = event.src_path
        with open(log_file) as f: 
            log_file = [x for x in f.read().split('\n') if x]
        last_line = log_file[-1]
        print ('Last line is : ', last_line)
        self.socket.write_message(json.dumps(last_line))


class LogMessagingSocket(tornado.websocket.WebSocketHandler):

    #Socket gets messages when opened
    @tornado.web.asynchronous
    @tornado.gen.engine
    def open(self, no_messages = 5, logfile = '/var/log/vapourapps/va-master.log'):
        print ('I am open')
        self.logfile = logfile
        with open(logfile) as f: 
            self.messages = f.read().split('\n')
        self.messages = self.messages
        self.write_message(json.dumps(self.messages[-no_messages:]))

        log_handler = LogHandler(self)
        observer = Observer()
        observer.schedule(log_handler, path = '/var/log/vapourapps/')
        observer.start()
        
    def get_messages(message):
        return self.messages[-message['number_of_messages']:]

    def check_origin(self, origin): 
        return True

    @tornado.gen.coroutine
    def on_message(self, message): 
        message = json.loads(message)
        reply = {
            'get_messages' : self.get_messages
        }[message['action']]
        self.write_message(reply(message))

