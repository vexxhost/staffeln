import staffeln.conf
import collections

from oslo_log import log
from staffeln.common import auth
from staffeln.common import context
# from staffeln.objects import backup as backup_api
from staffeln import objects
from staffeln.common import short_id

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


BackupMapping = collections.namedtuple(
    'BackupMapping', ['volume_id', 'backup_id', 'instance_id', 'backup_completed'])

QueueMapping = collections.namedtuple(
    'QueueMapping', ['volume_id', 'backup_id',
                     'instance_id', 'backup_status']
)

conn = auth.create_connection()


def check_vm_backup_metadata(metadata):
    if not CONF.conductor.backup_metadata_key in metadata:
        return False
    return metadata[CONF.conductor.backup_metadata_key].lower() in ['true']


def backup_volumes_in_project(conn, project_name):
    # conn.list_servers()
    pass


def get_projects_list():
    projects = conn.list_projects()
    return(projects)


class Queue(object):
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
            self._available_queues = objects.Queue.list(
                self.ctx)
        return self._available_queues

    @property
    def available_queues_map(self):
        """Mapping of backup loaded from DB"""
        if self._available_queues_map is None:
            self._available_queues_map = {
                QueueMapping(
                    backup_id=g.backup_id,
                    volume_id=g.volume_id,
                    instance_id=g.instance_id,
                    backup_status=g.backup_status): g
                for g in self.available_queues
            }
        return self._available_queues_map

    def get_queues(self, filters=None):
        queues = objects.Queue.list(self.ctx, filters=filters)
        return queues

    def create_queue(self):
        self.discovered_map = self.check_instance_volumes()
        queues_map = self.discovered_map["queues"]
        for queue_name, queue_map in queues_map.items():
            self._volume_queue(queue_map)

    def check_instance_volumes(self):
        queues_map = {}
        discovered_map = {
            "queues": queues_map
        }
        projects = get_projects_list()
        for project in projects:
            servers = conn.compute.servers(
                details=True, all_projects=True, project_id=project.id)
            for server in servers:
                server_id = server.host_id
                volumes = server.attached_volumes
                for volume in volumes:
                    queues_map['queues'] = QueueMapping(
                        volume_id=volume['id'],
                        backup_id=short_id.generate_id(),
                        instance_id=server_id,
                        backup_status=1
                    )
        return discovered_map

    def _volume_queue(self, queue_map):
        # print(queue_map)
        volume_id = queue_map.volume_id
        backup_id = queue_map.backup_id
        instance_id = queue_map.instance_id
        backup_status = queue_map.backup_status
        backup_mapping = dict()
        matching_backups = [g for g in self.available_queues
                            if g.backup_id == backup_id]
        if not matching_backups:
            volume_queue = objects.Queue(self.ctx)
            volume_queue.backup_id = backup_id
            volume_queue.volume_id = volume_id
            volume_queue.instance_id = instance_id
            volume_queue.backup_status = backup_status
            volume_queue.create()


class Backup_data(object):

    def __init__(self):
        self.ctx = context.make_context()
        self.discovered_map = None
        self.backup_mapping = dict()
        self._available_backups = None
        self._available_backups_map = None

    @property
    def available_backups(self):
        """Backups loaded from DB"""
        if self._available_backups is None:
            self._available_backups = objects.Volume.list(self.ctx)
        return self._available_backups

    @property
    def available_backups_map(self):
        """Mapping of backup loaded from DB"""
        if self._available_backups_map is None:
            self._available_backups_map = {
                BackupMapping(
                    backup_id=g.backup_id,
                    volume_id=g.volume_id,
                    instance_id=g.instance_id,
                    backup_completed=g.backup_completed): g
                for g in self.available_backups
            }
        return self._available_backups_map

    def volume_backup(self, queue):
        pass

    def _volume_backup(self, backup_map):
        volume_id = backup_map.volume_id
        backup_id = backup_map.backup_id
        instance_id = backup_map.instance_id
        backup_mapping = dict()
        for g in self.available_backups:
            print(g)
            print(g.volume_id)
        matching_backups = [g for g in self.available_backups
                            if g.backup_id == backup_id]
        if not matching_backups:
            volume = objects.Volume(self.ctx)
            volume.backup_id = backup_id
            volume.volume_id = volume_id
            volume.instance_id = instance_id
            volume.create()
