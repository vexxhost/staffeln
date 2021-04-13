import cotyledon
from futurist import periodics
from oslo_log import log
import staffeln.conf
import sys
import threading
import time

from staffeln.common import auth
from staffeln.conductor import backup


LOG = log.getLogger(__name__)
CONF = staffeln.conf.CONF


class BackupManager(cotyledon.Service):
    name = "Staffeln conductor backup controller"

    def __init__(self, worker_id, conf):
        super(BackupManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
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
        print("backing... %s" % str(time.time()))
        LOG.info("%s periodics" % self.name)
        conn = auth.create_connection()
        projects = conn.list_projects()
        for project in projects:
            print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<Project>>>>>>>>>>>>>>>>>>>>>>>>>")
            print(project.id)
            servers = conn.list_servers(all_projects=True, filters={"project_id": project.id})
            for server in servers:
                if not backup.check_vm_backup_metadata(server.metadata):
                    continue
                for volume in server.volumes:
                    print("<<<<<<<<<<<Volume>>>>>>>>>>")
                    print(volume)
                    # 1 backup volume
                    conn.create_volume_backup(volume_id=volume.id, force=True)
                    # 2 store backup_id in the database


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
