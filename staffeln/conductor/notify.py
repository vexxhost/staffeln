# Email notification package
# This should be upgraded by integrating with mail server to send batch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from oslo_log import log
import staffeln.conf
from staffeln.common import time as xtime
from staffeln.i18n import _

CONF = staffeln.conf.CONF
LOG = log.getLogger(__name__)


def _sendEmail(
    src_email,
    src_pwd,
    dest_email,
    subject,
    content,
    smtp_server_domain,
    smtp_server_port,
):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    # This part is commented as it won't be able to parce the items in list.
    # message["From"] = src_email
    # message["To"] = dest_email
    part = MIMEText(content, "html")
    message.attach(part)

    s = smtplib.SMTP(host=smtp_server_domain, port=smtp_server_port)
    # s.ehlo()
    # s.starttls()
    # we can comment this auth func when use the trusted ip without authentication against the smtp server
    # s.login(src_email, src_pwd)
    s.sendmail(src_email, dest_email, message.as_string())
    s.close()


def SendBackupResultEmail(success_backup_list, failed_backup_list):
    subject = "Backup result"

    html = (
        "<h3>${TIME}</h3>"
        "<h3>Success List</h3>"
        "<h4>${SUCCESS_VOLUME_LIST}</h4>"
        "<h3>Failed List</h3>"
        "<h4>${FAILED_VOLUME_LIST}</h4>"
    )

    success_volumes = "<br>".join([str(elem) for elem in success_backup_list])
    failed_volumes = "<br>".join([str(elem) for elem in failed_backup_list])
    html = html.replace("${TIME}", xtime.get_current_strtime())
    html = html.replace("${SUCCESS_VOLUME_LIST}", success_volumes)
    html = html.replace("${FAILED_VOLUME_LIST}", failed_volumes)
    try:
        _sendEmail(
            src_email=CONF.notification.sender_email,
            src_pwd=CONF.notification.sender_pwd,
            dest_email=CONF.notification.receiver,
            subject=subject,
            content=html,
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
