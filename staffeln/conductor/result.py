# Email notification package
# This should be upgraded by integrating with mail server to send batch
import staffeln.conf
from oslo_log import log
from staffeln.common import constants, email
from staffeln.common import time as xtime
from staffeln.conductor import backup
from staffeln.i18n import _

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


class BackupResult(object):
    def __init__(self):
        pass

    def initialize(self):
        self.content = ""
        self.project_list = set()

    def add_project(self, project_id, project_name):
        self.project_list.add((project_id, project_name))

    def send_result_email(self):
        subject = "Backup result"
        try:
            if len(CONF.notification.receiver) == 0:
                return
            email.send(
                src_email=CONF.notification.sender_email,
                src_pwd=CONF.notification.sender_pwd,
                dest_email=CONF.notification.receiver,
                subject=subject,
                content=self.content,
                smtp_server_domain=CONF.notification.smtp_server_domain,
                smtp_server_port=CONF.notification.smtp_server_port,
            )
            LOG.info(_("Backup result email sent"))
        except Exception as e:
            LOG.error(
                _(
                    "Backup result email send failed. Please check email configuration. %s"
                    % (str(e))
                )
            )

    def publish(self):
        # 1. get quota
        self.content = "<h3>${TIME}</h3><br>"
        self.content = self.content.replace("${TIME}", xtime.get_current_strtime())
        backup_mgt = backup.Backup()
        project_success = {}
        project_failed = {}
        success_queues = backup_mgt.get_queues(
            filters={"backup_status": constants.BACKUP_COMPLETED}
        )
        for queue in success_queues:
            if queue.project_id in project_success:
                project_success[queue.project_id].append(queue)
            else:
                project_success[queue.project_id] = [queue]
        failed_queues = backup_mgt.get_queues(
            filters={"backup_status": constants.BACKUP_FAILED}
        )
        for queue in failed_queues:
            if queue.project_id in project_failed:
                project_failed[queue.project_id].append(queue)
            else:
                project_failed[queue.project_id] = [queue]

        html = ""
        for project_id, project_name in self.project_list:
            quota = backup_mgt.get_backup_quota(project_id)

            html += (
                "<h3>Project: ${PROJECT}</h3><br>"
                "<h3>Quota Usage</h3><br>"
                "<h4>Limit: ${QUOTA_LIMIT}, In Use: ${QUOTA_IN_USE}, Reserved: ${QUOTA_RESERVED}</h4><br>"
                "<h3>Success List</h3><br>"
                "<h4>${SUCCESS_VOLUME_LIST}</h4><br>"
                "<h3>Failed List</h3><br>"
                "<h4>${FAILED_VOLUME_LIST}</h4><br>"
            )

            if project_id in project_success:
                success_volumes = "<br>".join(
                    [
                        "Volume ID: %s, Backup ID: %s, backup mode: %s"
                        % (
                            str(e.volume_id),
                            str(e.backup_id),
                            "Incremental" if e.incremental else "Full",
                        )
                        for e in project_success[project_id]
                    ]
                )
            else:
                success_volumes = "<br>"
            if project_id in project_failed:
                failed_volumes = "<br>".join(
                    [
                        "Volume ID: %s, Reason: %s" % (str(e.volume_id), str(e.reason))
                        for e in project_failed[project_id]
                    ]
                )
            else:
                failed_volumes = "<br>"

            html = html.replace("${QUOTA_LIMIT}", str(quota["limit"]))
            html = html.replace("${QUOTA_IN_USE}", str(quota["in_use"]))
            html = html.replace("${QUOTA_RESERVED}", str(quota["reserved"]))
            html = html.replace("${SUCCESS_VOLUME_LIST}", success_volumes)
            html = html.replace("${FAILED_VOLUME_LIST}", failed_volumes)
            html = html.replace("${PROJECT}", project_name)
        if html == "":
            return
        self.content += html
        self.send_result_email()
