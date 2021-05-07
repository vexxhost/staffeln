import cotyledon
from futurist import periodics
from oslo_log import log
import staffeln.conf
import threading
import time

from staffeln.common import constants
from staffeln.common import context
from staffeln.common import time as xtime
from staffeln.conductor import backup
from staffeln.conductor import notify
from staffeln.i18n import _

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
        periodic_worker = periodics.PeriodicWorker(periodic_callables, schedule_strategy="last_finished")
        periodic_thread = threading.Thread(target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(BackupManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    # Check if the backup count is over the limit
    # TODO(Alex): how to count the backup number
    #  only available backups are calculated?
    def _check_quota(self):
        LOG.info(_("Checking the backup limitation..."))
        max_count = CONF.conductor.max_backup_count
        current_count = len(backup.Backup().get_backups())
        if max_count <= current_count:
            # TODO(Alex): Send notification
            LOG.info(_("The backup limit is over."))
            return True
        LOG.info(_("The max limit is %s, and current backup count is %s" % (max_count, current_count)))
        return False

    # Manage active backup generators
    def _process_wip_tasks(self):
        LOG.info(_("Processing WIP backup generators..."))
        # TODO(Alex): Replace this infinite loop with finite time
        self.cycle_start_time = xtime.get_current_time()

        # loop - take care of backup result while timeout
        while(1):
            queues_started = backup.Backup().get_queues(
                filters={"backup_status": constants.BACKUP_WIP}
            )
            if len(queues_started) == 0:
                LOG.info(_("task queue empty"))
                break
            if not self._backup_cycle_timeout():# time in
                LOG.info(_("cycle timein"))
                for queue in queues_started: backup.Backup().check_volume_backup_status(queue)
            else: # time out
                LOG.info(_("cycle timeout"))
                for queue in queues_started: backup.Backup().hard_cancel_backup_task(queue)
                break
            time.sleep(constants.BACKUP_RESULT_CHECK_INTERVAL)

    # if the backup cycle timeout, then return True
    def _backup_cycle_timeout(self):
        time_delta_dict = xtime.parse_timedelta_string(CONF.conductor.backup_cycle_timout)

        if time_delta_dict == None:
            LOG.info(_("Recycle timeout format is invalid. "
                       "Follow <YEARS>y<MONTHS>m<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."))
            time_delta_dict = xtime.parse_timedelta_string(constants.DEFAULT_BACKUP_CYCLE_TIMEOUT)
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
        queues_to_start = backup.Backup().get_queues(
            filters={"backup_status": constants.BACKUP_PLANNED}
        )
        if len(queues_to_start) != 0:
            for queue in queues_to_start:
                backup.Backup().create_volume_backup(queue)

    # Refresh the task queue
    def _update_task_queue(self):
        LOG.info(_("Updating backup task queue..."))
        current_tasks = backup.Backup().get_queues()
        backup.Backup().create_queue(current_tasks)

    def _report_backup_result(self):
        # TODO(Alex): Need to update these list
        self.success_backup_list = []
        self.failed_backup_list = []
        notify.SendBackupResultEmail(self.success_backup_list, self.failed_backup_list)

    @periodics.periodic(spacing=CONF.conductor.backup_service_period, run_immediately=True)
    def backup_engine(self):
        LOG.info("backing... %s" % str(time.time()))
        LOG.info("%s periodics" % self.name)

        if self._check_quota(): return
        # NOTE(Alex): If _process_wip_tasks() waits tiil no WIP tasks
        # exist, no need to repeat this function before and after queue update.
        self._update_task_queue()
        self._process_todo_tasks()
        self._process_wip_tasks()
        # self._report_backup_result()


class RotationManager(cotyledon.Service):
    name = "Staffeln conductor rotation controller"

    def __init__(self, worker_id, conf):
        super(RotationManager, self).__init__(worker_id)
        self._shutdown = threading.Event()
        self.conf = conf
        LOG.info("%s init" % self.name)

    def run(self):
        LOG.info("%s run" % self.name)

        periodic_callables = [
            (self.rotation_engine, (), {}),
        ]
        periodic_worker = periodics.PeriodicWorker(periodic_callables, schedule_strategy="last_finished")
        periodic_thread = threading.Thread(target=periodic_worker.start)
        periodic_thread.daemon = True
        periodic_thread.start()

    def terminate(self):
        LOG.info("%s terminate" % self.name)
        super(RotationManager, self).terminate()

    def reload(self):
        LOG.info("%s reload" % self.name)

    def get_backup_list(self):
        threshold_strtime = self.get_threshold_strtime()
        if threshold_strtime == None: return False
        self.backup_list = backup.Backup().get_backups(filters={"created_at__lt": threshold_strtime})
        return True

    def remove_backups(self):
        print(self.backup_list)
        for retention_backup in self.backup_list:
            backup.Backup().hard_remove_volume_backup(retention_backup)

    @periodics.periodic(spacing=CONF.conductor.retention_service_period, run_immediately=True)
    def rotation_engine(self):
        LOG.info("%s rotation_engine" % self.name)
        # 1. get the list of backups to remove based on the retention time
        if not self.get_backup_list(): return

        # 2. remove the backups
        self.remove_backups()

    # get the threshold time str
    def get_threshold_strtime(self):
        time_delta_dict = xtime.parse_timedelta_string(CONF.conductor.retention_time)
        if time_delta_dict == None:
            LOG.info(_("Retention time format is invalid. "
                       "Follow <YEARS>y<MONTHS>m<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."))
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
