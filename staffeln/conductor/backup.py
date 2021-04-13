import staffeln.conf


CONF = staffeln.conf.CONF


def check_vm_backup_metadata(metadata):
    if not CONF.conductor.backup_metadata_key in metadata:
        return False
    return metadata[CONF.conductor.backup_metadata_key].lower() in ['true']

def backup_volumes_in_project(conn, project_name):
    # conn.list_servers()
    pass