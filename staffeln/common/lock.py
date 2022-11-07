import staffeln.conf
from oslo_utils import uuidutils
from tooz import coordination

CONF = staffeln.conf.CONF


class LockManager(object):
    def __init__(self, node_id=None):
        self.db_url = CONF.database.tooz_connection
        self.node_id = uuidutils.generate_uuid() if node_id is None else node_id
        # get_coordinator(backend_url, member_id)
        self.coordinator = coordination.get_coordinator(self.db_url, node_id)

    def __enter__(self):
        self.coordinator.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.coordinator.stop()
