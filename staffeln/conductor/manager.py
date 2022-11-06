import threading
import time

import cotyledon
import staffeln.conf
from futurist import periodics
from oslo_log import log
from staffeln.common import constants, context, lock
from staffeln.common import time as xtime
from staffeln.conductor import backup
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
        self.controller = backup.Backup()
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
        current_tasks = self.controller.get_queues()
        self.controller.create_queue(current_tasks)

    def _report_backup_result(self):
        self.controller.publish_backup_result()
        self.controller.purge_backups()

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
        self.controller = backup.Backup()
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)
        self.rotation_engine(CONF.conductor.retention_service_period)

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(RotationManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    def get_backup_list(self):
        threshold_strtime = self.get_threshold_strtime()
        if threshold_strtime is None:
            return False
        self.backup_list = self.controller.get_backups(
            filters={"created_at__lt": threshold_strtime}
        )
        return True

    def remove_backups(self):
        print(self.backup_list)
        for retention_backup in self.backup_list:
            self.controller.hard_remove_volume_backup(retention_backup)

    def rotation_engine(self, retention_service_period):
        LOG.info("%s rotation_engine" % self.name)

        @periodics.periodic(spacing=retention_service_period, run_immediately=True)
        def rotation_tasks():
            self.controller.refresh_openstacksdk()
            # 1. get the list of backups to remove based on the retention time
            if not self.get_backup_list():
                return
            # 2. get project list
            self.controller.update_project_list()
            # 3. remove the backups
            self.remove_backups()

        periodic_callables = [
            (rotation_tasks, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(
            periodic_callables, schedule_strategy="last_finished"
        )
        periodic_thread = threading.Thread(target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    # get the threshold time str
    def get_threshold_strtime(self):
        time_delta_dict = xtime.parse_timedelta_string(CONF.conductor.retention_time)
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
        return res.strftime(xtime.DEFAULT_TIME_FORMAT)
