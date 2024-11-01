# Email notification package
# This should be upgraded by integrating with mail server to send batch
from __future__ import annotations

from oslo_log import log
from oslo_utils import timeutils

from staffeln.common import constants
from staffeln.common import email
from staffeln.common import time as xtime
import staffeln.conf
from staffeln import objects

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


class BackupResult(object):
    def __init__(self, backup_mgt):
        self.backup_mgt = backup_mgt

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
            return True
        if not subject:
            subject = "Staffeln Backup result"
        if len(CONF.notification.receiver) != 0:
            # Found receiver in config, override report receiver.
            receiver = CONF.notification.receiver
        elif not CONF.notification.project_receiver_domain:
            try:
                receiver = (
                    self.backup_mgt.openstacksdk.get_project_member_emails(
                        project_id
                    )
                )
                if not receiver:
                    LOG.warn(
                        "No email can be found from members of project "
                        f"{project_id}. "
                        "Skip report now and will try to report later.")
                    return False
            except Exception as ex:
                LOG.warn(
                    "Failed to fetch emails from project members with "
                    f"exception: {str(ex)} "
                    "As also no receiver email or project receiver domain are "
                    "configured. Will try to report later.")
                return False
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
            LOG.info(f"Backup result email sent to {receiver}")
            return True
        except Exception as e:
            LOG.warn(
                f"Backup result email send to {receiver} failed. "
                f"Please check email configuration. {str(e)}"
            )
            raise

    def create_report_record(self):
        sender = (
            CONF.notification.sender_email
            if CONF.notification.sender_email
            else "RecordInLog"
        )
        report_ts = objects.ReportTimestamp(self.backup_mgt.ctx)
        report_ts.sender = sender
        report_ts.created_at = timeutils.utcnow()
        return report_ts.create()

    def publish(self, project_id=None, project_name=None):
        # 1. get quota
        self.content = f"<h3>{xtime.get_current_strtime()}</h3><br>"
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

        # Geneerate HTML Content
        html = ""
        quota = self.backup_mgt.get_backup_gigabytes_quota(project_id)
        quota_usage = (quota["in_use"] + quota["reserved"]) / quota["limit"]
        if quota_usage > 0.8:
            quota_color = "RED"
        elif quota_usage > 0.5:
            quota_color = "YALLOW"
        else:
            quota_color = "GREEN"
        if success_tasks:
            success_volumes = "<br>".join(
                [
                    (f"Volume ID: {str(e.volume_id)}, "
                     f"Backup ID: {str(e.backup_id)}, "
                     "Backup mode: "
                     f"{'Incremental' if e.incremental else 'Full'}, "
                     f"Created at: {str(e.created_at)}, Last updated at: "
                     f"{str(e.updated_at)}") for e in success_tasks])
        else:
            success_volumes = "<br>"
        if failed_tasks:
            failed_volumes = "<br>".join(
                [
                    (f"Volume ID: {str(e.volume_id)}, "
                     f"Reason: {str(e.reason)}, "
                     f"Created at: {str(e.created_at)}, Last updated at: "
                     f"{str(e.updated_at)}") for e in failed_tasks])
        else:
            failed_volumes = "<br>"
        html += (
            f"<h3>Project: {project_name} (ID: {project_id})</h3>"
            "<h3>Quota Usage (Backup Gigabytes)</h3>"
            f"<FONT COLOR={quota_color}><h4>Limit: {str(quota['limit'])} "
            "GB, In Use: "
            f"{str(quota['in_use'])} GB, Reserved: {str(quota['reserved'])} "
            "GB, Total "
            f"rate: {str(quota_usage)}</h4></FONT>"
            "<h3>Success List</h3>"
            f"<FONT COLOR=GREEN><h4>{success_volumes}</h4></FONT><br>"
            "<h3>Failed List</h3>"
            f"<FONT COLOR=RED><h4>{failed_volumes}</h4></FONT><br>")
        self.content += html
        subject = f"Staffeln Backup result: {project_id}"
        reported = self.send_result_email(
            project_id, subject=subject, project_name=project_name
        )
        if reported:
            # Record success report
            self.create_report_record()
            return True
        return False
