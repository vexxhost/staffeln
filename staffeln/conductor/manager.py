import cotyledon
from futurist import periodics
from oslo_log import log
import staffeln.conf
import sys
import threading
import time

from staffeln.common import auth
from staffeln.conductor import backup
from staffeln.common import context


LOG = log.getLogger(__name__)
CONF = staffeln.conf.CONF


class BackupManager(cotyledon.Service):
    name = "Staffeln conductor backup controller"

    def __init__(self, worker_id, conf):
        super(BackupManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        self.ctx = context.make_context()
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)
        periodic_callables = [
            (self.backup_engine, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(periodic_callables)
        periodic_thread = threading.Thread(
            target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(BackupManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    @periodics.periodic(spacing=CONF.conductor.backup_period, run_immediately=True)
    def backup_engine(self):
        LOG.info("backing... %s" % str(time.time()))
        LOG.info("%s periodics" % self.name)
        queue = backup.Queue().get_queues()
        queues_to_start = backup.Queue().get_queues(
            filters={'backup_status': 0})
        queues_started = backup.Queue().get_queues(
            filters={'backup_status': 1})
        queue_completed = backup.Queue().get_queues(
            filters={'backup_status': 2})
        if len(queue) == 0:
            create_queue = backup.Queue().create_queue()
        elif len(queues_started) != 0:
            for queue in queues_started:
                LOG.info("Waiting for backup of %s to be completed" %
                         queue.volume_id)
                backup_volume = backup.Backup_data().volume_backup(queue)
        elif len(queues_to_start) != 0:
            for queue in queues_to_start:
                LOG.info("Started backup process for %s" % queue.volume_id)
                backup_volume = backup.Backup_data().volume_backup(queue)
        elif len(queue_completed) == len(queue):
            pass


class RotationManager(cotyledon.Service):
    name = "Staffeln conductor rotation controller"

    def __init__(self, worker_id, conf):
        super(RotationManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)
        interval = CONF.conductor.rotation_period

        periodic_callables = [
            (self.rotation_engine, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(periodic_callables)
        periodic_thread = threading.Thread(
            target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(RotationManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    @periodics.periodic(spacing=CONF.conductor.rotation_period, run_immediately=True)
    def rotation_engine(self):
        print("rotating... %s" % str(time.time()))
        LOG.info("%s rotation_engine" % self.name)
