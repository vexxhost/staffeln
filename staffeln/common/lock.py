import staffeln.conf
from oslo_log import log
from oslo_utils import uuidutils
from tooz import coordination

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


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


class Lock(object):
    def __init__(self, lock_manager, lock_name):
        self.lock_manager = lock_manager
        self.lock_name = lock_name
        self.lock = None
        self.acquired = False

    def __enter__(self):
        self.lock = self.lock_manager.coordinator.get_lock(self.lock_name)
        self.acquired = self.lock.acquire(blocking=False)
        if not self.acquired:
            LOG.debug(f"Failed to lock for {self.lock_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.lock.release()
