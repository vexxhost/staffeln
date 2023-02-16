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
        self.backup_mgt = backup.Backup()

    def initialize(self):
        self.content = ""
        self.project_list = set()

    def add_project(self, project_id, project_name):
        self.project_list.add((project_id, project_name))

    def send_result_email(self, project_id, subject=None, project_name=None):
        if not CONF.notification.sender_email:
            LOG.info(
                "Directly record report in log as sender email "
                f"are not configed. Report: {self.content}"
            )
            return
        if not subject:
            subject = "Staffeln Backup result"
        if len(CONF.notification.receiver) != 0:
            # Found receiver in config, override report receiver.
            receiver = CONF.notification.receiver
        elif not CONF.notification.project_receiver_domain:
            try:
                receiver = self.backup_mgt.openstacksdk.get_project_member_emails(
                    project_id
                )
                if not receiver:
                    LOG.warn(
                        f"No email can be found from members of project {project_id}. "
                        "Skip report now and will try to report later."
                    )
                    return
            except Exception as ex:
                LOG.warn(
                    f"Failed to fetch emails from project members with exception: {ex}"
                    "As also no receiver email or project receiver domain are "
                    "configured. Will try to report later."
                )
                return
        else:
            receiver_domain = CONF.notification.project_receiver_domain
            receiver = f"{project_name}@{receiver_domain}"
        try:
            smtp_profile = {
                "src_email": CONF.notification.sender_email,
                "src_name": "Staffeln",
                "src_pwd": CONF.notification.sender_pwd,
                "dest_email": receiver,
                "subject": subject,
                "content": self.content,
                "smtp_server_domain": CONF.notification.smtp_server_domain,
                "smtp_server_port": CONF.notification.smtp_server_port,
            }
            email.send(smtp_profile)
            LOG.info(_(f"Backup result email sent to {receiver}"))
        except Exception as e:
            LOG.warn(
                _(
                    f"Backup result email send to {receiver} failed. "
                    f"Please check email configuration. {str(e)}"
                )
            )
            raise

    def publish(self, project_id=None, project_name=None):
        # 1. get quota
        self.content = "<h3>${TIME}</h3><br>"
        self.content = self.content.replace("${TIME}", xtime.get_current_strtime())
        success_tasks = self.backup_mgt.get_queues(
            filters={
                "backup_status": constants.BACKUP_COMPLETED,
                "project_id": project_id,
            }
        )
        failed_tasks = self.backup_mgt.get_queues(
            filters={
                "backup_status": constants.BACKUP_FAILED,
                "project_id": project_id,
            }
        )
        if not success_tasks and not failed_tasks:
            return False

        html = ""
        quota = self.backup_mgt.get_backup_quota(project_id)

        html += (
            "<h3>Project: ${PROJECT} (ID: ${PROJECT_ID})</h3><h3>Quota Usage</h3>"
            "<FONT COLOR=${QUOTA_COLLOR}><h4>Limit: ${QUOTA_LIMIT}, In Use: "
            "${QUOTA_IN_USE}, Reserved: ${QUOTA_RESERVED}, Total "
            "rate: ${QUOTA_USAGE}</h4></FONT>"
            "<h3>Success List</h3>"
            "<FONT COLOR=GREEN><h4>${SUCCESS_VOLUME_LIST}</h4></FONT><br>"
            "<h3>Failed List</h3>"
            "<FONT COLOR=RED><h4>${FAILED_VOLUME_LIST}</h4></FONT><br>"
        )

        if success_tasks:
            success_volumes = "<br>".join(
                [
                    (
                        f"Volume ID: {str(e.volume_id)}, Backup ID: {str(e.backup_id)}, "
                        f"Backup mode: {'Incremental' if e.incremental else 'Full'}, "
                        f"Created at: {str(e.created_at)}, Last updated at: "
                        f"{str(e.updated_at)}"
                    )
                    for e in success_tasks
                ]
            )
        else:
            success_volumes = "<br>"
        if failed_tasks:
            failed_volumes = "<br>".join(
                [
                    (
                        f"Volume ID: {str(e.volume_id)}, Reason: {str(e.reason)}, "
                        f"Created at: {str(e.created_at)}, Last updated at: "
                        f"{str(e.updated_at)}"
                    )
                    for e in failed_tasks
                ]
            )
        else:
            failed_volumes = "<br>"
        quota_usage = (quota["in_use"] + quota["reserved"]) / quota["limit"]
        if quota_usage > 0.8:
            quota_color = "RED"
        elif quota_usage > 0.5:
            quota_color = "YALLOW"
        else:
            quota_color = "GREEN"
        html = html.replace("${QUOTA_USAGE}", str(quota_usage))
        html = html.replace("${QUOTA_COLLOR}", quota_color)
        html = html.replace("${QUOTA_LIMIT}", str(quota["limit"]))
        html = html.replace("${QUOTA_IN_USE}", str(quota["in_use"]))
        html = html.replace("${QUOTA_RESERVED}", str(quota["reserved"]))
        html = html.replace("${SUCCESS_VOLUME_LIST}", success_volumes)
        html = html.replace("${FAILED_VOLUME_LIST}", failed_volumes)
        html = html.replace("${PROJECT}", project_name)
        html = html.replace("${PROJECT_ID}", project_id)
        self.content += html
        subject = f"Staffeln Backup result: {project_id}"
        self.send_result_email(project_id, subject=subject, project_name=project_name)
        return True
