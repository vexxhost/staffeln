import errno
import glob
import os
import re
import sys
import uuid
from typing import Optional  # noqa: H301

from oslo_log import log
from staffeln import conf, exception
from tooz import coordination

CONF = conf.CONF
LOG = log.getLogger(__name__)


class LockManager(object):
    def __init__(self):
        self.coordinator = COORDINATOR

    def __enter__(self):
        self.coordinator.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.coordinator.stop()


class Lock(object):
    def __init__(self, lock_manager, lock_name, remove_lock=False):
        self.lock_manager = lock_manager
        self.lock_name = lock_name
        self.lock = None
        self.acquired = False
        self.remove_lock = remove_lock

    def __enter__(self):
        self.lock = self.lock_manager.coordinator.get_lock(self.lock_name)
        self.acquired = self.lock.acquire(blocking=False)
        if not self.acquired:
            LOG.debug(f"Failed to lock for {self.lock_name}")
        LOG.debug(f"acquired lock for {self.lock_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.lock.release()
            LOG.debug(f"released lock for {self.lock_name}")
            if self.remove_lock:
                self.lock_manager.coordinator.remove_lock(self.lock_name)
                LOG.debug(f"removed lock file (if any) for {self.lock_name}")


class Coordinator(object):
    """Tooz coordination wrapper.

    Coordination member id is created from concatenated
    `prefix` and `agent_id` parameters.

    :param str agent_id: Agent identifier
    :param str prefix: Used to provide member identifier with a
        meaningful prefix.
    """

    def __init__(self, agent_id: Optional[str] = None, prefix: str = ""):
        self.coordinator = None
        self.agent_id = agent_id or str(uuid.uuid4())
        self.started = False
        self.prefix = prefix
        self._file_path = None

    def _get_file_path(self, backend_url):
        if backend_url.startswith("file://"):
            path = backend_url[7:]
            # Copied from TooZ's _normalize_path to get the same path they use
            if sys.platform == "win32":
                path = re.sub(r"\\(?=\w:\\)", "", os.path.normpath(path))
            return os.path.abspath(os.path.join(path, self.prefix))
        return None

    def start(self) -> None:
        if self.started:
            return

        backend_url = CONF.coordination.backend_url

        # member_id should be bytes
        member_id = (self.prefix + self.agent_id).encode("ascii")
        self.coordinator = coordination.get_coordinator(backend_url, member_id)
        assert self.coordinator is not None
        self.coordinator.start(start_heart=True)
        self._file_path = self._get_file_path(backend_url)
        self.started = True

    def stop(self) -> None:
        """Disconnect from coordination backend and stop heartbeat."""
        if self.started:
            if self.coordinator is not None:
                self.coordinator.stop()
            self.coordinator = None
            self.started = False

    def get_lock(self, name: str):
        """Return a Tooz backend lock.

        :param str name: The lock name that is used to identify it
            across all nodes.
        """
        # lock name should be bytes
        lock_name = (self.prefix + name).encode("ascii")
        if self.coordinator is not None:
            return self.coordinator.get_lock(lock_name)
        else:
            raise exception.LockCreationFailed("Coordinator uninitialized.")

    def remove_lock(self, glob_name):
        # Most locks clean up on release, but not the file lock, so we manually
        # clean them.

        def _err(file_name: str, exc: Exception) -> None:
            LOG.warning(f"Failed to cleanup lock {file_name}: {exc}")

        if self._file_path:
            files = glob.glob(self._file_path + glob_name)
            for file_name in files:
                try:
                    os.remove(file_name)
                except OSError as exc:
                    if exc.errno != errno.ENOENT:
                        _err(file_name, exc)
                except Exception as exc:
                    _err(file_name, exc)


COORDINATOR = Coordinator(prefix="staffeln-")
