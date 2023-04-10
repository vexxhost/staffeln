import threading
import time
from datetime import timedelta, timezone

import cotyledon
import staffeln.conf
from futurist import periodics
from oslo_log import log
from oslo_utils import timeutils
from staffeln.common import constants, context, lock
from staffeln.common import time as xtime
from staffeln.conductor import backup as backup_controller
from staffeln import objects
from staffeln.i18n import _
from tooz import coordination

LOG = log.getLogger(__name__)
CONF = staffeln.conf.CONF


class BackupManager(cotyledon.Service):
    name = "Staffeln conductor backup controller"

    def __init__(self, worker_id, conf):
        super(BackupManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        self.ctx = context.make_context()
        self.lock_mgt = lock.LockManager()
        self.controller = backup_controller.Backup()
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)
        self.backup_engine(CONF.conductor.backup_service_period)

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(BackupManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    # Manage active backup generators
    def _process_wip_tasks(self):
        LOG.info(_("Processing WIP backup generators..."))
        # TODO(Alex): Replace this infinite loop with finite time
        self.cycle_start_time = xtime.get_current_time()

        # loop - take care of backup result while timeout
        while 1:
            queues_started = self.controller.get_queues(
                filters={"backup_status": constants.BACKUP_WIP}
            )
            if len(queues_started) == 0:
                LOG.info(_("task queue empty"))
                break
            if not self._backup_cycle_timeout():  # time in
                LOG.info(_("cycle timein"))
                for queue in queues_started:
                    try:
                        with self.lock_mgt.coordinator.get_lock(queue.volume_id):
                            self.controller.check_volume_backup_status(queue)
                    except coordination.LockAcquireFailed:
                        LOG.debug(
                            "Failed to lock task for volume: %s." % queue.volume_id
                        )
            else:  # time out
                LOG.info(_("cycle timeout"))
                for queue in queues_started:
                    self.controller.hard_cancel_backup_task(queue)
                break
            time.sleep(constants.BACKUP_RESULT_CHECK_INTERVAL)

    # if the backup cycle timeout, then return True
    def _backup_cycle_timeout(self):
        time_delta_dict = xtime.parse_timedelta_string(
            CONF.conductor.backup_cycle_timout
        )

        if time_delta_dict is None:
            LOG.info(
                _(
                    "Recycle timeout format is invalid. "
                    "Follow <YEARS>y<MONTHS>m<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."
                )
            )
            time_delta_dict = xtime.parse_timedelta_string(
                constants.DEFAULT_BACKUP_CYCLE_TIMEOUT
            )
        rto = xtime.timeago(
            years=time_delta_dict["years"],
            months=time_delta_dict["months"],
            weeks=time_delta_dict["weeks"],
            days=time_delta_dict["days"],
            hours=time_delta_dict["hours"],
            minutes=time_delta_dict["minutes"],
            seconds=time_delta_dict["seconds"],
        )
        # print(rto.strftime(xtime.DEFAULT_TIME_FORMAT))
        # print(self.cycle_start_time)
        # print(self.cycle_start_time - rto)
        if rto >= self.cycle_start_time:
            return True
        return False

    # Create backup generators
    def _process_todo_tasks(self):
        LOG.info(_("Creating new backup generators..."))
        tasks_to_start = self.controller.get_queues(
            filters={"backup_status": constants.BACKUP_PLANNED}
        )
        if len(tasks_to_start) != 0:
            for task in tasks_to_start:
                try:
                    with self.lock_mgt.coordinator.get_lock(task.volume_id):
                        self.controller.create_volume_backup(task)
                except coordination.LockAcquireFailed:
                    LOG.debug("Failed to lock task for volume: %s." % task.volume_id)

    # Refresh the task queue
    def _update_task_queue(self):
        LOG.info(_("Updating backup task queue..."))
        self.controller.refresh_openstacksdk()
        self.controller.refresh_backup_result()
        filters = {"backup_status": constants.BACKUP_WIP}
        current_wip_tasks = self.controller.get_queues(filters=filters)
        filters["backup_status"] = constants.BACKUP_PLANNED
        current_plan_tasks = self.controller.get_queues(filters=filters)
        self.controller.create_queue(current_plan_tasks + current_wip_tasks)

    def _report_backup_result(self):
        report_period = CONF.conductor.report_period
        threshold_strtime = timeutils.utcnow() - timedelta(seconds=report_period)

        filters = {"created_at__gt": threshold_strtime.astimezone(timezone.utc)}
        report_tss = objects.ReportTimestamp.list(  # pylint: disable=E1120
            context=self.ctx, filters=filters
        )
        # If there are no reports that generated within report_period seconds,
        # generate and publish one.
        if not report_tss:
            LOG.info(_("Reporting finished backup tasks..."))
            self.controller.publish_backup_result(purge_on_success=True)

            # Purge records that live longer than 10 report cycles
            threshold_strtime = timeutils.utcnow() - timedelta(seconds=report_period*10)
            filters = {"created_at__lt": threshold_strtime.astimezone(timezone.utc)}
            old_report_tss = objects.ReportTimestamp.list(  # pylint: disable=E1120
                context=self.ctx, filters=filters
            )
            for report_ts in old_report_tss:
                report_ts.delete()

    def backup_engine(self, backup_service_period):
        LOG.info("Backup manager started %s" % str(time.time()))
        LOG.info("%s periodics" % self.name)

        @periodics.periodic(spacing=backup_service_period, run_immediately=True)
        def backup_tasks():
            with self.lock_mgt:
                try:
                    with self.lock_mgt.coordinator.get_lock(constants.PULLER):
                        LOG.info("Running as puller role")
                        self._update_task_queue()
                        self._process_todo_tasks()
                        self._process_wip_tasks()
                        self._report_backup_result()
                except coordination.LockAcquireFailed:
                    LOG.info("Running as non-puller role")
                    self._process_todo_tasks()
                    self._process_wip_tasks()

        periodic_callables = [
            (backup_tasks, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(
            periodic_callables, schedule_strategy="last_finished"
        )
        periodic_thread = threading.Thread(target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()


class RotationManager(cotyledon.Service):
    name = "Staffeln conductor rotation controller"

    def __init__(self, worker_id, conf):
        super(RotationManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        self.lock_mgt = lock.LockManager()
        self.controller = backup_controller.Backup()
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)
        self.rotation_engine(CONF.conductor.retention_service_period)

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(RotationManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    def get_backup_list(self, filters=None):
        return self.controller.get_backups(filters=filters)

    def remove_backups(self, retention_backups):
        LOG.info(_("Backups to be removed: %s" % retention_backups))
        for retention_backup in retention_backups:
            self.controller.hard_remove_volume_backup(retention_backup)

    def is_retention(self, backup):
        now = timeutils.utcnow().astimezone(timezone.utc)
        backup_age = now - backup.created_at.astimezone(timezone.utc)
        # see if need to be delete.
        if backup.instance_id in self.instance_retention_map:
            retention_time = now - self.get_time_from_str(
                self.instance_retention_map[backup.instance_id]
            )
            if backup_age > retention_time:
                # Backup remain longer than retention, need to purge it.
                return True
        elif now - self.threshold_strtime < backup_age:
            return True
        return False

    def rotation_engine(self, retention_service_period):
        LOG.info("%s rotation_engine" % self.name)

        @periodics.periodic(spacing=retention_service_period, run_immediately=True)
        def rotation_tasks():
            try:
                # TODO(rlin): change to use decorator for this
                # Make sure only one retention at a time
                with self.lock_mgt.coordinator.get_lock("retention"):
                    self.controller.refresh_openstacksdk()
                    # get the threshold time
                    self.threshold_strtime = self.get_time_from_str(
                        CONF.conductor.retention_time
                    ).astimezone(timezone.utc)
                    self.instance_retention_map = (
                        self.controller.collect_instance_retention_map()
                    )

                    # No way to judge retention
                    if (
                        self.threshold_strtime is None
                        and not self.instance_retention_map
                    ):
                        return
                    backup_instance_map = {}

                    # get project list
                    self.controller.update_project_list()

                    for backup in self.get_backup_list():
                        # Create backup instance map for later sorted by created_at.
                        # This can be use as base of judgement on delete a backup.
                        # The reason we need such list is because backup have
                        # dependency with each other after we enable incremental backup.
                        # So we need to have information to judge on.
                        if backup.instance_id in backup_instance_map:
                            backup_instance_map[backup.instance_id].append(backup)
                        else:
                            backup_instance_map[backup.instance_id] = [backup]

                    # Sort backup instance map and use it to check backup create time and order.
                    for instance_id in backup_instance_map:
                        sorted_backup_list = sorted(
                            backup_instance_map[instance_id],
                            key=lambda backup: backup.created_at.timestamp(),
                            reverse=True,
                        )
                        for backup in sorted_backup_list:
                            if self.is_retention(backup):
                                # Try to delete and skip any incremental exist error.
                                self.controller.hard_remove_volume_backup(
                                    backup, skip_inc_err=True
                                )
                                time.sleep(2)
            except coordination.LockAcquireFailed:
                LOG.debug("Failed to lock for retention")

        periodic_callables = [
            (rotation_tasks, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(
            periodic_callables, schedule_strategy="last_finished"
        )
        periodic_thread = threading.Thread(target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    # get time
    def get_time_from_str(self, time_str, to_str=False):
        time_delta_dict = xtime.parse_timedelta_string(time_str)
        if time_delta_dict is None:
            LOG.info(
                _(
                    "Retention time format is invalid. "
                    "Follow <YEARS>y<MONTHS>m<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."
                )
            )
            return None

        res = xtime.timeago(
            years=time_delta_dict["years"],
            months=time_delta_dict["months"],
            weeks=time_delta_dict["weeks"],
            days=time_delta_dict["days"],
            hours=time_delta_dict["hours"],
            minutes=time_delta_dict["minutes"],
            seconds=time_delta_dict["seconds"],
        )
        return res.strftime(xtime.DEFAULT_TIME_FORMAT) if to_str else res
