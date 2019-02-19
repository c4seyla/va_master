import tornado.httpserver
import tornado.ioloop
import sys
import os
import ssl
from va_master.va_master_project import config, httpserver
from OpenSSL import crypto, SSL
from socket import gethostname
from pprint import pprint
from time import gmtime, mktime
import uuid

#We use coloredlogs for limited prettier output. It may not be available for all terminals. 
try:
    import coloredlogs
except ImportError: 
    coloredlogs = None 

def generate_keys(master_config, crt_path, key_path):
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "MG"
    cert.get_subject().ST = "World St."
    cert.get_subject().L = "World"
    cert.get_subject().O = "Master server"
    cert.get_subject().OU = "No organization"
    cert.get_subject().CN = gethostname()
    cert.set_serial_number(int(uuid.uuid4()))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    #cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha1')

    with open(crt_path, 'w') as crtf:
        crtf.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open(key_path, 'w') as keyf:
        keyf.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

def bootstrap(master_config):
    """Starts the master with all its components, and provides the configuration
    data to all the components."""

    if coloredlogs: 
        print ('Instaling coloredlogs')
        coloredlogs.install(logger = master_config.logger)
        print ('Done. ')

    master_config.logger.info('Bootstrap initiated. ')
    app = httpserver.get_app(master_config)
    print ('Doing certs')
    if True: 
#    if None in (master_config.https_crt, master_config.https_key):
        crt_path = os.path.join(master_config.ssl_folder, 'https.crt')
        key_path = os.path.join(master_config.ssl_folder, 'https.key')
        master_config.logger.info('No certificate found, will generate at %s' % (master_config.ssl_folder))

        try:
            with open(crt_path):
                with open(key_path):
                    master_config.logger.info('Loading self-signed ' \
                            'certificates...')
        except:
            master_config.logger.info('Generating self-signed certificate...')
            generate_keys(master_config, crt_path, key_path)
    else:
        master_config.logger.info('Using certificates from config : %s and %s. ' % (master_config.https_crt, master_config.https_key))
        crt_path = master_config.https_crt
        key_path = master_config.https_key

    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(crt_path, key_path)
    print ('Importing consul. ')
    from va_master.consul_kv import consul
#    consul.ConsulProcess(master_config).start()
    my_serv = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
    my_serv.listen(master_config.https_port)
    print ("Started server. ")
    master_config.logger.info('Server is listening at : %s. ' % str(master_config.https_port))
    master_config.logger.info('Starting server. ')
#    try:
    print ('Doing ioloop')
    tornado.ioloop.IOLoop.current().start()
#    except: 
#        master_config.logger.info('Caught exception in ioloop: ')
#        import traceback
#        traceback.print_exc()


