import collections
from datetime import timedelta, timezone

import staffeln.conf
from openstack.exceptions import HttpException as OpenstackHttpException
from openstack.exceptions import ResourceNotFound as OpenstackResourceNotFound
from openstack.exceptions import SDKException as OpenstackSDKException
from oslo_log import log
from oslo_utils import timeutils
from staffeln import objects
from staffeln.common import constants, context, openstack
from staffeln.common import time as xtime
from staffeln.conductor import result
from staffeln.i18n import _

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)

BackupMapping = collections.namedtuple(
    "BackupMapping",
    [
        "volume_id",
        "backup_id",
        "project_id",
        "instance_id",
        "backup_completed",
        "incremental",
        "created_at",
    ],
)

QueueMapping = collections.namedtuple(
    "QueueMapping",
    [
        "volume_id",
        "backup_id",
        "project_id",
        "instance_id",
        "backup_status",
        "instance_name",
        "volume_name",
        "incremental",
        "reason",
    ],
)


def retry_auth(func):
    """Decorator to reconnect openstack and avoid token rotation"""

    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except OpenstackHttpException as ex:
            if ex.status_code == 403:
                LOG.warn(_("Token has been expired or rotated!"))
                self.refresh_openstacksdk()
                return func(self, *args, **kwargs)

    return wrapper


class Backup(object):
    """Implmentations of the queue with the sql."""

    def __init__(self):
        self.ctx = context.make_context()
        self.refresh_openstacksdk()
        self.result = result.BackupResult(self)
        self.project_list = {}

    def refresh_openstacksdk(self):
        self.openstacksdk = openstack.OpenstackSDK()

    def publish_backup_result(self, purge_on_success=False):
        for project_id, project_name in self.result.project_list:
            try:
                publish_result = self.result.publish(project_id, project_name)
                if publish_result and purge_on_success:
                    # Purge backup queue tasks
                    self.purge_backups(project_id)
            except Exception as ex:  # pylint: disable=W0703
                LOG.warn(
                    "Failed to publish backup result or "
                    f"purge backup tasks for project {project_id} "
                    f"{str(ex)}"
                )

    def refresh_backup_result(self):
        self.result.initialize()

    def get_backups(self, filters=None, **kwargs):
        return objects.Volume.list(  # pylint: disable=E1120
            context=self.ctx, filters=filters, **kwargs
        )

    def get_backup_quota(self, project_id):
        return self.openstacksdk.get_backup_quota(project_id)

    def get_backup_gigabytes_quota(self, project_id):
        return self.openstacksdk.get_backup_gigabytes_quota(project_id)

    def get_queues(self, filters=None):
        """Get the list of volume queue columns from the queue_data table"""
        queues = objects.Queue.list(  # pylint: disable=E1120
            context=self.ctx, filters=filters
        )
        return queues

    def get_queue_task_by_id(self, task_id):
        """Get single volume queue task from the queue_data table"""
        queue = objects.Queue.get_by_id(  # pylint: disable=E1120
            context=self.ctx, id=task_id
        )
        return queue

    def create_queue(self, old_tasks):
        """
        Create the queue of all the volumes for backup

        :param old_tasks: Task list not completed in the previous cycle
        :type: List<Class objects.Queue>
        """

        LOG.info("Adding new backup tasks to queue.")
        # 1. get the old task list, not finished in the last cycle
        #  and keep till now
        old_task_volume_list = []
        for old_task in old_tasks:
            old_task_volume_list.append(old_task.volume_id)

        # 2. add new tasks in the queue which are not existing in the old task list
        task_list = self.check_instance_volumes()
        for task in task_list:
            if task.volume_id not in old_task_volume_list:
                self._volume_queue(task)

    # Backup the volumes attached to which has a specific metadata
    def filter_by_server_metadata(self, metadata):
        if CONF.conductor.backup_metadata_key is not None:
            if CONF.conductor.backup_metadata_key not in metadata:
                return False

            return (
                metadata[CONF.conductor.backup_metadata_key].lower()
                == constants.BACKUP_ENABLED_KEY
            )
        else:
            return True

    # Backup the volumes in in-use and available status
    def filter_by_volume_status(self, volume_id, project_id):
        try:
            volume = self.openstacksdk.get_volume(volume_id, project_id)
            if volume is None:
                return False
            res = volume["status"] in ("available", "in-use")
            if not res:
                reason = _(
                    "Volume %s is not triger new backup task because it is in %s status"
                    % (volume_id, volume["status"])
                )
                LOG.info(reason)
                return reason
            return res

        except OpenstackResourceNotFound:
            return False

    def purge_backups(self, project_id=None):
        LOG.info(f"Start pruge backup tasks for project {project_id}")
        # TODO make all this in a single DB command
        success_tasks = self.get_queues(
            filters={
                "backup_status": constants.BACKUP_COMPLETED,
                "project_id": project_id,
            }
        )
        failed_tasks = self.get_queues(
            filters={
                "backup_status": constants.BACKUP_FAILED,
                "project_id": project_id,
            }
        )
        LOG.debug(f"Start purge completed tasks for project {project_id}")
        for queue in success_tasks:
            queue.delete_queue()

        LOG.debug(f"Start purge failed tasks for project {project_id}")
        for queue in failed_tasks:
            queue.delete_queue()

    def create_failed_backup_obj(self, task):
        # Create backup object for failed backups, to make sure we
        # will review the delete later when retention triggered.
        # Set the created_at time to retention_time ago,
        # so it might get check on next retention cycle.
        # For customerized retention instances, the backup might check later
        # but the process to check the remove will eventually starts.
        # Note: 315360000 = 10 years. The create time of an backup object will
        # not affect report.
        threshold_strtime = timeutils.utcnow() - timedelta(seconds=315360000)
        self._volume_backup(
            BackupMapping(
                volume_id=task.volume_id,
                project_id=task.project_id,
                backup_id=task.backup_id,
                instance_id=task.instance_id,
                backup_completed=0,
                incremental=task.incremental,
                created_at=threshold_strtime,
            )
        )

    #  delete all backups forcily regardless of the status
    def hard_cancel_backup_task(self, task):
        try:
            project_id = task.project_id
            reason = _("Cancel backup %s because of timeout." % task.backup_id)
            LOG.info(reason)

            if project_id not in self.project_list:
                self.process_non_existing_backup(task)
            self.openstacksdk.set_project(self.project_list[project_id])
            backup = self.openstacksdk.get_backup(task.backup_id)
            if backup is None:
                return task.delete_queue()
            self.openstacksdk.delete_backup(task.backup_id)
            self.create_failed_backup_obj(task)

            task.reason = reason
            task.backup_status = constants.BACKUP_FAILED
            task.save()

        except OpenstackSDKException as e:
            reason = _(
                "Backup %s deletion failed. Need delete manually: %s"
                % (task.backup_id, str(e)[:64])
            )
            log_msg = _(
                "Backup %s deletion failed. Need delete manually: %s"
                % (task.backup_id, str(e))
            )
            LOG.warn(log_msg)
            task.reason = reason
            task.backup_status = constants.BACKUP_FAILED
            task.save()

    #  delete only available backups: reserved
    def soft_remove_backup_task(self, backup_object):
        try:
            backup = self.openstacksdk.get_backup(backup_object.backup_id)
            if backup is None:
                LOG.info(
                    f"Backup {backup_object.backup_id} is removed from "
                    "Openstack or cinder-backup is not existing in the cloud."
                )
                return backup_object.delete_backup()
            if backup["status"] in ("available"):
                self.openstacksdk.delete_backup(backup_object.backup_id)
                # Don't remove backup until it's officially removed from Cinder
                # backup_object.delete_backup()
            elif backup["status"] in ("error", "error_restoring"):
                # Try to remove it from cinder
                self.openstacksdk.delete_backup(backup_object.backup_id)
                # Don't remove backup until it's officially removed from Cinder
                # backup_object.delete_backup()
            else:  # "deleting", "restoring"
                LOG.info(
                    f"Rotation for the backup {backup_object.backup_id} "
                    "is skipped in this cycle "
                    f"because it is in {backup['status']} status"
                )

        except OpenstackSDKException as e:
            LOG.warn(f"Backup {backup_object.backup_id} deletion failed. {str(e)}")
            # We don't delete backup object if any exception occured
            # backup_object.delete_backup()
            return False

    #  delete all backups forcily regardless of the status
    def hard_remove_volume_backup(self, backup_object, skip_inc_err=False):
        try:
            project_id = backup_object.project_id
            if project_id not in self.project_list:
                LOG.warn(
                    f"Project {project_id} for backup "
                    f"{backup_object.backup_id} is not existing in "
                    "Openstack. Please check your access right to this project. "
                    "Skip this backup from remove now and will retry later."
                )
                # Don't remove backup object, keep it and retry on next periodic task
                # backup_object.delete_backup()
                return

            self.openstacksdk.set_project(self.project_list[project_id])
            backup = self.openstacksdk.get_backup(
                uuid=backup_object.backup_id, project_id=project_id
            )
            if backup is None:
                LOG.info(
                    f"Backup {backup_object.backup_id} is removed from Openstack "
                    "or cinder-backup is not existing in the cloud. "
                    "Start removing backup object from Staffeln."
                )
                return backup_object.delete_backup()

            self.openstacksdk.delete_backup(uuid=backup_object.backup_id)
            # Don't remove backup until it's officially removed from Cinder
            # backup_object.delete_backup()
        except Exception as e:
            if skip_inc_err and "Incremental backups exist for this backup" in str(e):
                LOG.debug(str(e))
            else:
                LOG.info(
                    f"Backup {backup_object.backup_id} deletion failed. "
                    "Skip this backup from remove now and will retry later."
                )
                LOG.debug(f"deletion failed {str(e)}")

                # Don't remove backup object, keep it and retry on next periodic task
                # backup_object.delete_backup()

    def update_project_list(self):
        projects = self.openstacksdk.get_projects()
        for project in projects:
            self.project_list[project.id] = project

    def _is_backup_required(self, volume_id):
        """
        Decide if the backup required based on the backup history

        If there is any backup created during certain time,
        will not trigger new backup request.
        This will judge on CONF.conductor.backup_min_interval

        :param volume_id: Target volume id
        :type: uuid string

        :return: if new backup required
        :return type: bool
        """
        # select * from backup order by Id;
        try:
            if CONF.conductor.backup_min_interval == 0:
                # Ignore backup interval
                return True
            interval = CONF.conductor.backup_min_interval
            threshold_strtime = timeutils.utcnow() - timedelta(seconds=interval)
            backups = self.get_backups(
                filters={
                    "volume_id__eq": volume_id,
                    "created_at__gt": threshold_strtime.astimezone(timezone.utc),
                }
            )
            if backups:
                return False
        except Exception as e:
            LOG.debug(
                _(
                    "Failed to get backup history to decide backup is "
                    "required or not. Reason: %s" % str(e)
                )
            )
        return True

    def _is_incremental(self, volume_id):
        """
        Decide the backup method based on the backup history

        It queries to select the last N backups from backup table and
        decide backup type as full if there is no full backup.
        N equals to CONF.conductor.full_backup_depth.

        :param volume_id: Target volume id
        :type: uuid string

        :return: if backup method is incremental or not
        :return type: bool
        """
        # select * from backup order by Id DESC LIMIT 2;
        try:
            if CONF.conductor.full_backup_depth == 0:
                return False
            backups = self.get_backups(
                filters={"volume_id__eq": volume_id},
                limit=CONF.conductor.full_backup_depth,
                sort_key="id",
                sort_dir="desc",
            )
            for bk in backups:
                if bk.incremental:
                    continue
                else:
                    return True
        except Exception as e:
            LOG.debug(
                _(
                    "Failed to get backup history to decide backup method. Reason: %s"
                    % str(e)
                )
            )
        return False

    def check_instance_volumes(self):
        """
        Retrieves volume list to backup

        Get the list of all the volumes from the project using openstacksdk.
        Function first list all the servers in the project and get the volumes
        that are attached to the instance.

        Generate backup candidate list for later create tasks in queue
        """
        queues_map = []
        self.refresh_openstacksdk()
        projects = self.openstacksdk.get_projects()
        for project in projects:
            empty_project = True
            self.project_list[project.id] = project
            try:
                servers = self.openstacksdk.get_servers(project_id=project.id)
            except OpenstackHttpException as ex:
                LOG.warn(
                    _(
                        "Failed to list servers in project %s. %s"
                        % (project.id, str(ex))
                    )
                )
                continue
            for server in servers:
                if not self.filter_by_server_metadata(server.metadata):
                    continue
                if empty_project:
                    empty_project = False
                    self.result.add_project(project.id, project.name)
                for volume in server.attached_volumes:
                    filter_result = self.filter_by_volume_status(
                        volume["id"], project.id
                    )

                    if not filter_result:
                        continue
                    backup_required = self._is_backup_required(volume["id"])
                    if not backup_required:
                        continue

                    if "name" not in volume or not volume["name"]:
                        volume_name = volume["id"]
                    else:
                        volume_name = volume["name"][:100]
                    if filter_result is True:
                        backup_status = constants.BACKUP_PLANNED
                        reason = None
                    else:
                        backup_status = constants.BACKUP_FAILED
                        reason = filter_result
                    incremental = self._is_incremental(volume["id"])
                    backup_method = "Incremental" if incremental else "Full"
                    LOG.info(
                        "Prapering %s backup task for volume %s",
                        backup_method,
                        volume["id"],
                    )
                    queues_map.append(
                        QueueMapping(
                            project_id=project.id,
                            volume_id=volume["id"],
                            backup_id="NULL",
                            instance_id=server.id,
                            backup_status=backup_status,
                            # Only keep the last 100 chars of instance_name and
                            # volume_name for forming backup_name
                            instance_name=server.name[:100],
                            volume_name=volume_name,
                            incremental=incremental,
                            reason=reason,
                        )
                    )
        return queues_map

    def collect_instance_retention_map(self):
        """Retrieves instance backup retention map"""

        retention_map = {}
        # No customized retention.
        if not CONF.conductor.retention_metadata_key:
            return retention_map
        self.refresh_openstacksdk()

        try:
            servers = self.openstacksdk.get_servers(all_projects=True)
        except OpenstackHttpException:
            LOG.warn(_("Failed to list servers for all projects."))

        for server in servers:
            if CONF.conductor.retention_metadata_key in server.metadata:
                server_retention_time = server.metadata[
                    CONF.conductor.retention_metadata_key
                ].lower()
                if xtime.regex.fullmatch(server_retention_time):
                    LOG.debug(
                        f"Found retention time ({server_retention_time}) defined for "
                        f"server {server.id}, Adding it retention reference map."
                    )
                    retention_map[server.id] = server_retention_time
                else:
                    LOG.info(
                        f"Server retention time for instance {server.id} is incorrect. "
                        "Please follow '<YEARS>y<MONTHS>m<WEEKS>w<DAYS>d<HOURS>"
                        "h<MINUTES>min<SECONDS>s' format."
                    )
        return retention_map

    def _volume_queue(self, task):
        """
        Commits one backup task to queue table

        :param task: One backup task
        :type: QueueMapping
        """
        volume_queue = objects.Queue(self.ctx)
        volume_queue.backup_id = task.backup_id
        volume_queue.volume_id = task.volume_id
        volume_queue.instance_id = task.instance_id
        volume_queue.project_id = task.project_id
        volume_queue.backup_status = task.backup_status
        volume_queue.instance_name = task.instance_name
        volume_queue.volume_name = task.volume_name
        # NOTE(Oleks): Backup mode is inherited from backup service.
        # Need to keep and navigate backup mode history, to decide a different mode per volume
        volume_queue.incremental = task.incremental

        backup_method = "Incremental" if task.incremental else "Full"
        LOG.info(
            _(
                ("Schedule %s backup task for volume %s.")
                % (backup_method, task.volume_id)
            )
        )
        return volume_queue.create()

    def create_volume_backup(self, task):
        """Initiate the backup of the volume
        :param task: Provide the map of the volume that needs
                  backup.
        This function will call the backupup api and change the
        backup_status and backup_id in the task queue table.
        """
        project_id = task.project_id
        timestamp = int(timeutils.utcnow().timestamp())
        # Backup name allows max 255 chars of string
        backup_name = ("%(instance_name)s_%(volume_name)s_%(timestamp)s") % {
            "instance_name": task.instance_name,
            "volume_name": task.volume_name,
            "timestamp": timestamp,
        }

        # Make sure we don't exceed max size of backup_name
        backup_name = backup_name[:255]
        if task.backup_id == "NULL":
            try:
                # NOTE(Alex): no need to wait because we have a cycle time out
                if project_id not in self.project_list:
                    LOG.warn(
                        _("Project ID %s is not existing in project list" % project_id)
                    )
                    self.process_non_existing_backup(task)
                    return
                self.openstacksdk.set_project(self.project_list[project_id])
                backup_method = "Incremental" if task.incremental else "Full"
                LOG.info(
                    _(
                        ("%s Backup (name: %s) for volume %s creating in project %s")
                        % (backup_method, backup_name, task.volume_id, project_id)
                    )
                )
                volume_backup = self.openstacksdk.create_backup(
                    volume_id=task.volume_id,
                    project_id=project_id,
                    name=backup_name,
                    incremental=task.incremental,
                )
                task.backup_id = volume_backup.id
                task.backup_status = constants.BACKUP_WIP
                task.save()
            except OpenstackSDKException as error:
                inc_err_msg = "No backups available to do an incremental backup"
                if inc_err_msg in str(error):
                    LOG.info(
                        "Retry to create full backup for volume %s instead of incremental."
                        % task.volume_id
                    )
                    task.incremental = False
                    task.save()
                else:
                    reason = _(
                        "Backup (name: %s) creation for the volume %s failled. %s"
                        % (backup_name, task.volume_id, str(error)[:64])
                    )
                    LOG.warn(
                        "Backup (name: %s) creation for the volume %s failled. %s"
                        % (backup_name, task.volume_id, str(error))
                    )
                    task.reason = reason
                    task.backup_status = constants.BACKUP_FAILED
                    task.save()
            # Added extra exception as OpenstackSDKException does not handle the keystone unauthourized issue.
            except Exception as error:
                reason = _(
                    "Backup (name: %s) creation for the volume %s failled. %s"
                    % (backup_name, task.volume_id, str(error)[:64])
                )
                LOG.warn(
                    "Backup (name: %s) creation for the volume %s failled. %s"
                    % (backup_name, task.volume_id, str(error))
                )
                task.reason = reason
                task.backup_status = constants.BACKUP_FAILED
                task.save()
        else:
            # Backup planned task cannot have backup_id in the same cycle.
            # Remove this task from the task list
            task.delete_queue()

    # backup gen was not created
    def process_pre_failed_backup(self, task):
        # 1.notify via email
        reason = _(
            "The backup creation for the volume %s was prefailed." % task.volume_id
        )
        LOG.warn(reason)
        task.reason = reason
        task.backup_status = constants.BACKUP_FAILED
        task.save()

    def process_failed_backup(self, task):
        # 1. notify via email
        reason = _("The status of backup for the volume %s is error." % task.volume_id)
        LOG.warn(reason)
        # 2. delete backup generator
        try:
            self.openstacksdk.delete_backup(uuid=task.backup_id)
            self.create_failed_backup_obj(task)
        except OpenstackHttpException as ex:
            LOG.warn(
                _(
                    "Failed to delete volume backup %s. %s. Need to delete manually."
                    % (task.backup_id, str(ex))
                )
            )
        task.reason = reason
        task.backup_status = constants.BACKUP_FAILED
        task.save()

    def process_non_existing_backup(self, task):
        task.delete_queue()

    def process_available_backup(self, task):
        LOG.info("Backup of the volume %s is successful." % task.volume_id)
        # 1. save success backup in the backup table
        self._volume_backup(
            BackupMapping(
                volume_id=task.volume_id,
                project_id=task.project_id,
                backup_id=task.backup_id,
                instance_id=task.instance_id,
                backup_completed=1,
                incremental=task.incremental,
                created_at=timeutils.utcnow(),
            )
        )
        task.backup_status = constants.BACKUP_COMPLETED
        task.save()

    def process_using_backup(self, task):
        # treat same as the available backup for now
        self.process_available_backup(task)

    def check_volume_backup_status(self, queue):
        """Checks the backup status of the volume
        :params: queue: Provide the map of the volume that needs backup
                 status checked.
        Call the backups api to see if the backup is successful.
        """
        project_id = queue.project_id

        # The case in which the error produced before backup gen created.
        if queue.backup_id == "NULL":
            self.process_pre_failed_backup(queue)
            return
        if project_id not in self.project_list:
            self.process_non_existing_backup(queue)
            return
        self.openstacksdk.set_project(self.project_list[project_id])
        backup_gen = self.openstacksdk.get_backup(queue.backup_id)

        if backup_gen is None:
            # TODO(Alex): need to check when it is none
            LOG.info(
                _("[Beta] Backup status of %s is returning none." % (queue.backup_id))
            )
            self.process_non_existing_backup(queue)
            return
        if backup_gen.status == "error":
            self.process_failed_backup(queue)
        elif backup_gen.status == "available":
            self.process_available_backup(queue)
        elif backup_gen.status == "creating":
            LOG.info("Waiting for backup of %s to be completed" % queue.volume_id)
        else:  # "deleting", "restoring", "error_restoring" status
            self.process_using_backup(queue)

    def _volume_backup(self, task):
        # matching_backups = [
        #     g for g in self.available_backups if g.backup_id == task.backup_id
        # ]
        # if not matching_backups:
        volume_backup = objects.Volume(self.ctx)
        volume_backup.backup_id = task.backup_id
        volume_backup.volume_id = task.volume_id
        volume_backup.instance_id = task.instance_id
        volume_backup.project_id = task.project_id
        volume_backup.backup_completed = task.backup_completed
        volume_backup.incremental = task.incremental
        volume_backup.create()
