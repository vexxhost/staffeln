import staffeln.conf
import collections
from staffeln.common import constants

from openstack import exceptions
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
        self.discovered_backup_map = None
        self.queue_mapping = dict()
        self.volume_mapping = dict()

    def get_queues(self, filters=None):
        """Get the list of volume queue columns from the queue_data table"""
        queues = objects.Queue.list(self.ctx, filters=filters)
        return queues

    def create_queue(self):
        """Create the queue of all the volumes for backup"""
        queue_list = self.check_instance_volumes()
        for queue in queue_list:
            self._volume_queue(queue)

    # Backup the volumes attached to which has a specific metadata
    def filter_server(self, metadata):

        if not CONF.conductor.backup_metadata_key in metadata:
            return False

        return metadata[CONF.conductor.backup_metadata_key].lower() == constants.BACKUP_ENABLED_KEY

    # Backup the volumes in in-use and available status
    def filter_volume(self, volume_id):
        volume = conn.get_volume_by_id(volume_id)
        return volume['status'] in ("available", "in-use")

    def check_instance_volumes(self):
        """Get the list of all the volumes from the project using openstacksdk
        Function first list all the servers in the project and get the volumes
        that are attached to the instance.
        """
        queues_map = []
        projects = get_projects_list()
        for project in projects:
            servers = conn.compute.servers(
                details=True, all_projects=True, project_id=project.id
            )
            for server in servers:
                if not self.filter_server(server.metadata): continue
                server_id = server.id
                volumes = server.attached_volumes
                for volume in volumes:
                    if not self.filter_volume(volume["id"]): continue
                    queues_map.append(
                        QueueMapping(
                            volume_id=volume["id"],
                            backup_id="NULL",
                            instance_id=server_id,
                            backup_status=constants.BACKUP_PLANNED,
                        )
                    )
        return queues_map

    def _volume_queue(self, task):
        """Saves the queue data to the database."""

        # TODO(Alex): Need to escalate discussion
        # When create the task list, need to check the WIP backup generators
        # which are created in the past backup cycle.
        # Then skip to create new tasks for the volumes whose backup is WIP
        volume_queue = objects.Queue(self.ctx)
        volume_queue.backup_id = task.backup_id
        volume_queue.volume_id = task.volume_id
        volume_queue.instance_id = task.instance_id
        volume_queue.backup_status = task.backup_status
        volume_queue.create()

    def volume_backup_initiate(self, queue):
        """Initiate the backup of the volume
        :params: queue: Provide the map of the volume that needs
                  backup.
        This function will call the backupup api and change the
        backup_status and backup_id in the queue table.
        """
        backup_id = queue.backup_id
        if backup_id == "NULL":
            try:
                volume_backup = conn.block_storage.create_backup(
                    volume_id=queue.volume_id, force=True
                )
                print(volume_backup)
                queue.backup_id = volume_backup.id
                queue.backup_status = constants.BACKUP_WIP
                queue.save()
            except exceptions as error:
                print("catch error")
                print(error)
        else:
            pass
            # TODO(Alex): remove this task from the task list
            #  Backup planned task cannot have backup_id in the same cycle
            #  Reserve for now because it is related to the WIP backup genenrators which
            #  are not finished in the current cycle

    def process_failed_task(self, task):
        LOG.error("Backup of the volume %s failed." % task.id)
        # 1. TODO(Alex): notify via email
        # 2. TODO(Alex): remove failed backup instance from the openstack
        # 3. remove failed task from the task queue
        queue_delete = objects.Queue.get_by_id(self.ctx, task.id)
        queue_delete.delete_queue()

    def process_success_backup(self, task):
        LOG.info("Backup of the volume %s is successful." % task.volume_id)
        # 1. save success backup in the backup table
        self._volume_backup(
            BackupMapping(
                volume_id=task.volume_id,
                backup_id=task.backup_id,
                instance_id=task.instance_id,
                backup_completed=1,
            )
        )
        # 2. remove from the task list
        queue_delete = objects.Queue.get_by_id(self.ctx, task.id)
        queue_delete.delete_queue()
        # 3. TODO(Alex): notify via email

    def check_volume_backup_status(self, queue):
        """Checks the backup status of the volume
        :params: queue: Provide the map of the volume that needs backup
                 status checked.
        Call the backups api to see if the backup is successful.
        """
        for backup_gen in conn.block_storage.backups(volume_id=queue.volume_id):
            if backup_gen.id == queue.backup_id:
                if backup_gen.status == "error":
                    self.process_failed_task(queue)
                elif backup_gen.status == "success":
                    self.process_success_backup(queue)
                else:
                    # TODO(Alex): Need to escalate discussion
                    # How to proceed WIP bakcup generators?
                    # To make things worse, the last backup generator is in progress till
                    # the new backup cycle
                    LOG.info("Waiting for backup of %s to be completed" % queue.volume_id)

    def _volume_backup(self, task):
        # matching_backups = [
        #     g for g in self.available_backups if g.backup_id == task.backup_id
        # ]
        # if not matching_backups:
        volume_backup = objects.Volume(self.ctx)
        volume_backup.backup_id = task.backup_id
        volume_backup.volume_id = task.volume_id
        volume_backup.instance_id = task.instance_id
        volume_backup.backup_completed = task.backup_completed
        volume_backup.create()
