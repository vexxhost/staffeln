# Email notification package
# This should be upgraded by integrating with mail server to send batch
from oslo_log import log

import staffeln.conf
from staffeln.common import email
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
        self.project_list = []
        self.success_backup_list = {}
        self.failed_backup_list = {}

    def add_project(self, id, name):
        if id in self.success_backup_list:
            return
        self.project_list.append({"name": name, "id": id})
        self.success_backup_list[id] = []
        self.failed_backup_list[id] = []

    def add_success_backup(self, project_id, volume_id, backup_id):
        if project_id not in self.success_backup_list:
            LOG.error(_("Not registered project is reported for backup result."))
            return
        self.success_backup_list[project_id].append(
            {
                "volume_id": volume_id,
                "backup_id": backup_id,
            }
        )

    def add_failed_backup(self, project_id, volume_id, reason):
        if project_id not in self.failed_backup_list:
            LOG.error(_("Not registered project is reported for backup result."))
            return
        self.failed_backup_list[project_id].append(
            {
                "volume_id": volume_id,
                "reason": reason,
            }
        )

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
        html = ""
        for project in self.project_list:
            quota = backup.Backup().get_backup_quota(project["id"])

            html += (
                "<h3>Project: ${PROJECT}</h3><br>"
                "<h3>Quota Usage</h3><br>"
                "<h4>Limit: ${QUOTA_LIMIT}, In Use: ${QUOTA_IN_USE}, Reserved: ${QUOTA_RESERVED}</h4><br>"
                "<h3>Success List</h3><br>"
                "<h4>${SUCCESS_VOLUME_LIST}</h4><br>"
                "<h3>Failed List</h3><br>"
                "<h4>${FAILED_VOLUME_LIST}</h4><br>"
            )

            success_volumes = "<br>".join(
                [
                    "Volume ID: %s, Backup ID: %s"
                    % (str(e["volume_id"]), str(e["backup_id"]))
                    for e in self.success_backup_list[project["id"]]
                ]
            )
            failed_volumes = "<br>".join(
                [
                    "Volume ID: %s, Reason: %s"
                    % (str(e["volume_id"]), str(e["reason"]))
                    for e in self.failed_backup_list[project["id"]]
                ]
            )

            html = html.replace("${QUOTA_LIMIT}", str(quota["limit"]))
            html = html.replace("${QUOTA_IN_USE}", str(quota["in_use"]))
            html = html.replace("${QUOTA_RESERVED}", str(quota["reserved"]))
            html = html.replace("${SUCCESS_VOLUME_LIST}", success_volumes)
            html = html.replace("${FAILED_VOLUME_LIST}", failed_volumes)
            html = html.replace("${PROJECT}", project["name"])
        if html == "":
            return
        self.content += html
        self.send_result_email()
