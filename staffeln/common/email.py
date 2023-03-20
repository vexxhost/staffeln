""" Email module with SMTP"""

import smtplib
from email.header import Header
from email.mime.text import MIMEText

from oslo_log import log

LOG = log.getLogger(__name__)


def send(smtp_profile):
    """Email send with SMTP"""
    dest_header = (
        smtp_profile["dest_email"]
        if isinstance(smtp_profile["dest_email"], str)
        else str(smtp_profile["dest_email"])
    )
    message = MIMEText(smtp_profile["content"], "html", "utf-8")
    message["From"] = Header(smtp_profile["src_name"], "utf-8")
    message["To"] = Header(dest_header, "utf-8")
    message["Subject"] = Header(smtp_profile["subject"], "utf-8")
    try:
        smtp_obj = smtplib.SMTP(
            smtp_profile["smtp_server_domain"], smtp_profile["smtp_server_port"]
        )
        smtp_obj.connect(
            smtp_profile["smtp_server_domain"], smtp_profile["smtp_server_port"]
        )
        smtp_obj.ehlo()
        smtp_obj.starttls()
        smtp_obj.ehlo()
        # SMTP Login
        smtp_obj.login(smtp_profile["src_email"], smtp_profile["src_pwd"])
        smtp_obj.sendmail(
            smtp_profile["src_email"], smtp_profile["dest_email"], message.as_string()
        )
        # Email Sent
    except smtplib.SMTPException as error:
        LOG.info(f"Email send error with SMTP fail: {str(error)}")
        raise
