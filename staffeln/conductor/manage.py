import cotyledon
from futurist import periodics
from oslo_log import log
import staffeln.conf
import sys
import threading


LOG = log.getLogger(__name__)
CONF = staffeln.conf.CONF


class BackupService(cotyledon.Service):
    name = "conductor"

    def __init__(self, worker_id, conf):
        super(BackupService, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        LOG.error("%s init" % self.name)

    def run(self):
        LOG.error("%s run" % self.name)
        self._shutdown.wait()
        interval = CONF.conductor.backup_period
        @periodics.periodic(spacing=interval, run_immediately=True)
        def backup_engine():
            pass

    def terminate(self):
        LOG.error("%s terminate" % self.name)
        self._shutdown.set()
        sys.exit(42)

    def reload(self):
        LOG.error("%s reload" % self.name)
