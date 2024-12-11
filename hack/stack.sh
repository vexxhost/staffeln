#!/bin/bash -xe
# shellcheck disable=SC1091

# Install dependencies
sudo apt-get update

# Setup folders for DevStack
sudo mkdir -p /opt/stack
sudo chown -R "${USER}". /opt/stack

# Clone repository if not present, otherwise update
if [ ! -f /opt/stack/stack.sh ]; then
    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack
else
    pushd /opt/stack
    git pull
    popd
fi

# Create DevStack configuration file

sudo mkdir /etc/staffeln
sudo chown -R "${USER}". /etc/staffeln
cat <<EOF > /opt/stack/local.conf
[[local|localrc]]
KEYSTONE_ADMIN_ENDPOINT=true
DATABASE_PASSWORD=secrete123
RABBIT_PASSWORD=secrete123
SERVICE_PASSWORD=secrete123
ADMIN_PASSWORD=secrete123
LIBVIRT_TYPE=kvm
VOLUME_BACKING_FILE_SIZE=50G
GLANCE_LIMIT_IMAGE_SIZE_TOTAL=10000
CINDER_BACKUP_DRIVER=swift
SWIFT_HASH=66a3d6b56c1f479c8b4e70ab5c2000f5
SWIFT_REPLICAS=1
enable_plugin neutron https://opendev.org/openstack/neutron
#swift
enable_service s-proxy s-object s-container s-account
# Cinder
enable_service c-bak
[[post-config|/etc/neutron/neutron.conf]]
[DEFAULT]
advertise_mtu = True
global_physnet_mtu = 1400
EOF

# Start DevStack deployment
/opt/stack/stack.sh

# Create staffeln configuration file
cat <<EOF > /etc/staffeln/staffeln.conf
[DEFAULT]
debug = True
[conductor]
backup_workers = 1
rotation_workers = 1
backup_service_period = 1200
retention_service_period = 1200
backup_cycle_timout = 5min
retention_time = 2w3d
backup_metadata_key="__staffeln_backup"
retention_metadata_key="__staffeln_retention"
full_backup_depth = 4

[database]
backend = sqlalchemy
connection = "mysql+pymysql://staffeln:password@localhost:3306/staffeln"
mysql_engine = InnoDB

[coordination]
backend_url = "file:///tmp/staffeln_locks"
EOF

# Create staffeln database
mysql -e 'CREATE DATABASE staffeln;' || echo "Database for staffeln already exists."
mysql -e 'CREATE USER "staffeln"@"%" IDENTIFIED BY "password";' || echo "DB user staffeln already exists."
mysql -e 'GRANT ALL PRIVILEGES ON staffeln.* TO "staffeln"@"%";'

# Install staffeln
pip install -U setuptools pip
"${HOME}"/.local/bin/pip3 install -e .

# Start staffeln conductor
"${HOME}"/.local/bin/staffeln-db-manage --config-file /etc/staffeln/staffeln.conf create_schema
 #staffeln-db-manage upgrade head

echo You can fetch authroize with command: source /opt/stack/openrc admin admin
echo You can now run staffeln conductor with: "${HOME}"/.local/bin/staffeln-conductor --config-file /etc/staffeln/staffeln.conf
echo You can now run staffeln api with: "${HOME}"/.local/bin/staffeln-api --config-file /etc/staffeln/staffeln.conf
