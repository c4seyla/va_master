# VA_Master
This is the core project of VapourApps, the master which contains:
* Consul (monitoring the apps and KV store)
* Salt Master (provisioning)
* The scheduler (containing API and dashboard)

## Installing in production
Requirements:
* Debian Server 9 or any derivative (such as Ubuntu Server)
* Unbound ports: tcp/80, tcp/443, tcp/8600, tcp/8500, tcp/8400, tcp/8300
* Python 2.7, pip, setuptools

**Debian dependencies:** There are some OS-level dependencies (libssl source, supervisor daemon, build-essential compiler suite, HashiCorp Consul) that you can install, using the following command:

```bash
curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
sudo apt-get update && sudo apt-get install -y build-essential python-dev libssl-dev libffi-dev libzmq-dev unzip supervisor curl python-libvirt nodejs xorriso pythpon-setuptools
sudo easy_install pip
```

For 32bit server:
```bash
sudo curl https://releases.hashicorp.com/consul/0.7.0/consul_0.7.0_linux_386.zip > consul.zip && sudo unzip -d /usr/bin -o consul.zip consul"
```

For 64bit server:
```bash
sudo curl https://releases.hashicorp.com/consul/0.7.0/consul_0.7.0_linux_amd64.zip > consul.zip && sudo unzip -d /usr/bin -o consul.zip consul"
```

**The software itself:** Install the software.

```bash
pip install vapourapps
vapourapps init
```

## Installing for development
Requirements:
* the requirements for production (see above)
* git (to get the code)
* NodeJS (to build dashboard JavaScript code)
* npm (to build dashboard JavaScript code)

```bash
git clone https://github.com/VapourApps/va_master.git
cd va_master
pip install -e .
vapourapps init
# Build dashboard JavaScript
cd va_dashboard
npm install --no-bin-links && node build.js
# Detach it from supervisor and manually run code
sudo supervisorctl stop va_master
sudo virtualenv/bin/python -m va_master start
```

## Docs

The docs are available [here](docs/)

## Testing
At the moment we are working on a test suite, which should contain unit tests and integration tests (with Salt-Cloud and Consul).

## License
This project is distributed under [the GPL v3 license](http://www.gnu.org/licenses/gpl-3.0.en.html).
