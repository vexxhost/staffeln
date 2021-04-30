import openstack


def create_connection():
    return openstack.connect(cloud="envvars")
