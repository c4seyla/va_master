import tornado
import functools
import pkg_resources
import logging
import os
from va_master.consul_kv import datastore
from va_master.handlers import datastore_handler, drivers_handler
#folder_pwd = os.path.join(os.path.dirname(os.path.realpath(__file__)), '')

folder_pwd = os.getcwd()
def get_server_static():
    # get the server assets static path
    return pkg_resources.resource_filename('va_dashboard', 'static')

class Config(object):
    """A `Config` contains the configuration options for the whole master. It doesn't
    need explicit options and provides smart defaults."""

    def __init__(self, **kwargs):
        # Defaults first:
        self.version = (1, 0, 0)
        self.consul_port = 0
        self.datastore = datastore.ConsulStore()
        self.logger = logging.getLogger('deployer')
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('[%(asctime)-15s] %(message)s'))
        self.logger.addHandler(ch)
        self.server_port = 80
        self.https_port = 443
        self.server_static_path = get_server_static()
        self.deploy_pool_count = 3
        self.ssh_key_path = os.path.expanduser('~/.ssh/')
        self.ssh_key_name = 'va-master' 

        self.ssl_folder = folder_pwd + '/ssl'
        self.https_crt = folder_pwd + '/ssl/https.crt'
        self.https_key = folder_pwd + '/ssl/https.key'

        self.datastore_handler = datastore_handler.DatastoreHandler(datastore = self.datastore, config = self)
        self.drivers_handler = drivers_handler.DriversHandler(self.datastore_handler, ssh_key_path = self.ssh_key_path, ssh_key_name = self.ssh_key_name, ssl_path = self.ssl_folder)

        # Now dynamically inject any kwargs
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])

    def pretty_version(self):
        return '.'.join([str(x) for x in self.version])
