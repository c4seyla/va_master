import setuptools

setuptools.setup(
  name='vapourapps',
  packages=setuptools.find_packages(),
  version='1.0.2',
  description='This package contains the master server of VapourApps, a DevOps tool for corporate apps.',
  keywords=['vapourapps'],
  author='VapourApps',
  install_requires=[
    'tornado',
    'pyopenSSL',
    'salt',
    'apache-libcloud',
    'python-novaclient',
    'pbkdf2', 
    'pyVmomi', #for vmware
    'libvirt-python', #for, well, libvirt
    'boto3', #for aws
    'python-digitalocean',
    'pylxd',
    'gitpython',
    'watchdog', 
    'clc-sdk',
    'google-api-python-client',
    'paramiko', #for ssh connections
    'reportlab', #For generating PDF files
    'coloredlogs', #For pretty log printing. Can be left out in unsupported terminals. 
    'pyopenssl',
    'netifaces',
    'appdirs',
    'requests>=2.20.0',
    #'vapour_linux_amd64;platform_system=="Linux"',
    #'vapour_windows_amd64;platform_system=="Windows"',
  ],
  zip_safe=False,
  entry_points = {
    'console_scripts': [
        'vapourapps = va_master.cli:entry',
        'vapourapps-test = va_master.tests:run_tests'
    ]
  }
)
