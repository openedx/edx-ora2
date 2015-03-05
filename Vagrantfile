Vagrant.require_version ">= 1.5.3"
unless Vagrant.has_plugin?("vagrant-vbguest")
  raise "Please install the vagrant-vbguest plugin by running `vagrant plugin install vagrant-vbguest`"
end

VAGRANTFILE_API_VERSION = "2"

MEMORY = 1048
CPU_COUNT = 2

$bashrc = <<SCRIPT
source "/edx/app/ora2/venvs/ora2/bin/activate"

# If X11 forwarding is enabled, then use the DISPLAY value
# already set and use the X11 session cookie
if [ -n "$DISPLAY" ]; then
    export XAUTHORITY="/home/vagrant/.Xauthority"

# Otherwise, configure the display to use the virtual frame buffer
else
    export DISPLAY=":1"
fi

cd "/edx/app/ora2/edx-ora2"
SCRIPT

$script = <<SCRIPT
export PYTHONUNBUFFERED=1

if id -u ora2 >/dev/null 2>&1; then
  echo "User ora2 exists."
else
  echo "Creating user ora2."
  mkdir -p /edx/app/ora2
  sudo useradd -d /edx/app/ora2 -s /bin/bash ora2
  sudo adduser --quiet ora2 admin
  chown -R ora2:ora2 /edx/app/ora2
  sudo -u ora2 echo "#{$bashrc}" >> /edx/app/ora2/.bashrc
fi

sudo apt-get install -y python-pip python-virtualenv

if [ -d "/edx/app/ora2/venvs/ora2" ]; then
  echo "Virtualenv exists in /edx/app/ora2/venvs/ora2. Skipping creating one."
else
  echo "Creating virtualenv in /edx/app/ora2/venvs/ora2."
  sudo -u ora2 virtualenv --clear -q /edx/app/ora2/venvs/ora2
fi

SCRIPT

ora_mount_dir = "edx-ora2"

if ENV['VAGRANT_MOUNT_BASE']

  ora_mount_dir = ENV['VAGRANT_MOUNT_BASE'] + "/" + ora_mount_dir

end

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Creates an edX devstack VM from an official release
  config.vm.box     = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"

  config.vm.network :private_network, ip: "192.168.33.11"
  config.vm.network :forwarded_port, guest: 9000, host: 9000
  config.vm.network :forwarded_port, guest: 9001, host: 9001
  config.ssh.insert_key = true

  # Enable X11 forwarding so we can interact with GUI applications
  if ENV['VAGRANT_X11']
    config.ssh.forward_x11 = true
  end

  config.vm.synced_folder "#{ora_mount_dir}", "/edx/app/ora2/edx-ora2",
    create: true, owner: "ora2", group: "ora2"

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", MEMORY.to_s]
    vb.customize ["modifyvm", :id, "--cpus", CPU_COUNT.to_s]

    # Allow DNS to work for Ubuntu 12.10 host
    # http://askubuntu.com/questions/238040/how-do-i-fix-name-service-for-vagrant-client
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  end

  # Use vagrant-vbguest plugin to make sure Guest Additions are in sync
  config.vbguest.auto_reboot = true
  config.vbguest.auto_update = true

  config.vm.provision "shell", inline: $script
end
