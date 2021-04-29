import staffeln.conf
import collections

from openstack.block_storage.v2 import backup
from oslo_log import log
from staffeln.common import auth
from staffeln.common import context
from staffeln import objects
from staffeln.common import short_id

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


BackupMapping = collections.namedtuple(
    "BackupMapping", ["volume_id", "backup_id", "instance_id", "backup_completed"]
)

QueueMapping = collections.namedtuple(
    "QueueMapping", ["volume_id", "backup_id", "instance_id", "backup_status"]
)

conn = auth.create_connection()


def check_vm_backup_metadata(metadata):
    if not CONF.conductor.backup_metadata_key in metadata:
        return False
    return metadata[CONF.conductor.backup_metadata_key].lower() in ["true"]


def backup_volumes_in_project(conn, project_name):
    # conn.list_servers()
    pass


def get_projects_list():
    projects = conn.list_projects()
    return projects


class Backup(object):
    """Implmentations of the queue with the sql."""

    def __init__(self):
        self.ctx = context.make_context()
        self.discovered_map = None
        self.queue_mapping = dict()
        self._available_queues = None
        self._available_queues_map = None

    @property
    def available_queues(self):
        """Queues loaded from DB"""
        if self._available_queues is None:
            self._available_queues = objects.Queue.list(self.ctx)
        return self._available_queues

    @property
    def available_queues_map(self):
        """Mapping of backup queue loaded from DB"""
        if self._available_queues_map is None:
            self._available_queues_map = {
                QueueMapping(
                    backup_id=g.backup_id,
                    volume_id=g.volume_id,
                    instance_id=g.instance_id,
                    backup_status=g.backup_status,
                ): g
                for g in self.available_queues
            }
        return self._available_queues_map

    def get_queues(self, filters=None):
        """Get the list of volume queue columns from the queue_data table"""
        queues = objects.Queue.list(self.ctx, filters=filters)
        return queues

    def create_queue(self):
        """Create the queue of all the volumes for backup"""
        self.discovered_map = self.check_instance_volumes()
        queues_map = self.discovered_map["queues"]
        for queue_name, queue_map in queues_map.items():
            self._volume_queue(queue_map)

    def check_instance_volumes(self):
        """Get the list of all the volumes from the project using openstacksdk
        Function first list all the servers in the project and get the volumes
        that are attached to the instance.
        """
        queues_map = {}
        discovered_map = {"queues": queues_map}
        projects = get_projects_list()
        for project in projects:
            servers = conn.compute.servers(
                details=True, all_projects=True, project_id=project.id
            )
            for server in servers:
                server_id = server.host_id
                volumes = server.attached_volumes
                for volume in volumes:
                    queues_map["queues"] = QueueMapping(
                        volume_id=volume["id"],
                        backup_id="NULL",
                        instance_id=server_id,
                        backup_status=0,
                    )
        return discovered_map

    def _volume_queue(self, queue_map):
        """Saves the queue data to the database."""
        volume_id = queue_map.volume_id
        backup_id = queue_map.backup_id
        instance_id = queue_map.instance_id
        backup_status = queue_map.backup_status
        backup_mapping = dict()
        matching_backups = [
            g for g in self.available_queues if g.backup_id == backup_id
        ]
        if not matching_backups:
            volume_queue = objects.Queue(self.ctx)
            volume_queue.backup_id = backup_id
            volume_queue.volume_id = volume_id
            volume_queue.instance_id = instance_id
            volume_queue.backup_status = backup_status
            volume_queue.create()

    def volume_backup_initiate(self, queue):
        """Initiate the backup of the volume
        :params: queue: Provide the map of the volume that needs
                  backup.
        This function will call the backupup api and change the
        backup_status and backup_id in the queue table.
        """
        volume_info = conn.get_volume(queue.volume_id)
        backup_id = queue.backup_id
        if backup_id == "NULL":
            volume_backup = conn.block_storage.create_backup(
                volume_id=queue.volume_id, force=True
            )
            update_queue = objects.Queue.get_by_id(self.ctx, queue.id)
            update_queue.backup_id = volume_backup.id
            update_queue.backup_status = 1
            update_queue.save()

    def check_volume_backup_status(self, queue):
        """Checks the backup status of the volume
        :params: queue: Provide the map of the volume that needs backup
                 status checked.
        Call the backups api to see if the backup is successful.
        """
        for raw in conn.block_storage.backups(volume_id=queue.volume_id):
            backup_info = raw.to_dict()
            if backup_info.id == queue.id:
                if backup_info.status == error:
                    Log.error("Backup of the volume %s failed." % queue.id)
                    ## Call db api to remove the queue object.
                elif backup_info.status == "success":
                    LOG.info("Backup of the volume %s is successful." % queue.volume_id)
                    ## call db api to remove the queue object.
                    ## Call db api to add the backup status in volume_backup table.
                else:
                    pass
                    ## Wait for the backup to be completed.
