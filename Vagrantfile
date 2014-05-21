# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

$script = <<END
set -e

echo "Updating apt packages..."
apt-get update -y

echo "Installing basic system requirements..."
apt-get install -y curl git vim libxml2-dev libxslt1-dev

echo "Installing Python system requirements..."
apt-get install -y python2.7 python2.7-dev python-pip python-software-properties
pip install virtualenv

echo "Installing FireFox and xvfb (for JavaScript tests)..."
add-apt-repository "ppa:ubuntu-mozilla-security/ppa"
apt-get install -y firefox dbus-x11 xvfb

cat > /etc/init/xvfb.conf <<XVFB_UPSTART
    description     "Xvfb X Server"
    start on (net-device-up and local-filesystems and runlevel [2345])
    stop on runlevel [016]
    exec /usr/bin/Xvfb :1 -screen 0 1024x768x24
    respawn
    respawn limit 15 5
XVFB_UPSTART
start xvfb || true

echo "Installing RabbitMQ..."
add-apt-repository "deb http://www.rabbitmq.com/debian/ testing main"
cd /tmp && wget http://www.rabbitmq.com/rabbitmq-signing-key-public.asc && apt-key add rabbitmq-signing-key-public.asc
apt-get update -y
apt-get install -y rabbitmq-server

echo "Installing NodeJS..."
add-apt-repository ppa:chris-lea/node.js
apt-get update -y
apt-get install -y nodejs

su vagrant <<EOF
    set -e

    echo "Creating a virtualenv..."
    mkdir -p /home/vagrant/.virtualenvs
    virtualenv /home/vagrant/.virtualenvs/edx-ora2
    source /home/vagrant/.virtualenvs/edx-ora2/bin/activate

    echo "Configuring login script..."
    cat > /home/vagrant/.bash_profile <<LOGIN_SCRIPT
        source /home/vagrant/.virtualenvs/edx-ora2/bin/activate
        export NLTK_DATA=/home/vagrant/data/nltk_data
        export DISPLAY=:1
LOGIN_SCRIPT

    echo "Installing EASE..."
    if [ ! -d /home/vagrant/ease ]; then
        git clone https://github.com/edx/ease.git /home/vagrant/ease
    fi
    cat /home/vagrant/ease/apt-packages.txt | xargs sudo apt-get -y install
    pip install -r /home/vagrant/ease/pre-requirements.txt
    pip install -r /home/vagrant/ease/requirements.txt
    cd /home/vagrant/ease && python setup.py install

    echo "Downloading NLTK corpus..."
    mkdir -p /home/vagrant/data
    curl -o /home/vagrant/data/nltk.tmp.tar.tz http://edx-static.s3.amazonaws.com/nltk/nltk-data-20131113.tar.gz
    tar zxf /home/vagrant/data/nltk.tmp.tar.tz

    echo "Install edx-ora2..."
    cd /home/vagrant/edx-ora2 && ./scripts/install.sh

EOF

END

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"

  config.vm.network "forwarded_port", guest: 80, host: 8082
  config.vm.network "private_network", ip: "192.168.44.10"
  config.vm.synced_folder ".", "/home/vagrant/edx-ora2"

  config.vm.provision "shell", inline: $script

end
