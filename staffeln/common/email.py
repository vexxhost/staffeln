""" Email module with SMTP"""

from __future__ import annotations

import smtplib
from email import utils
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from oslo_log import log

LOG = log.getLogger(__name__)


def send(smtp_profile):
    """Email send with SMTP"""
    if isinstance(smtp_profile["dest_email"], str):
        dest_header = smtp_profile["dest_email"]
    elif isinstance(smtp_profile["dest_email"], list):
        dest_header = ", ".join(smtp_profile["dest_email"])
    else:
        dest_header = str(smtp_profile["dest_email"])
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(smtp_profile["subject"], "utf-8")
    msg["From"] = "{} <{}>".format(
        Header(smtp_profile["src_name"], "utf-8"), smtp_profile["src_email"]
    )
    msg["To"] = dest_header
    msg["Message-id"] = utils.make_msgid()
    msg["Date"] = utils.formatdate()
    content = MIMEText(smtp_profile["content"], "html", "utf-8")
    msg.attach(content)

    try:
        smtp_obj = smtplib.SMTP(
            smtp_profile["smtp_server_domain"],
            smtp_profile["smtp_server_port"],
        )
        smtp_obj.connect(
            smtp_profile["smtp_server_domain"],
            smtp_profile["smtp_server_port"],
        )
        smtp_obj.ehlo()
        smtp_obj.starttls()
        smtp_obj.ehlo()
        # SMTP Login
        smtp_obj.login(smtp_profile["src_email"], smtp_profile["src_pwd"])
        smtp_obj.sendmail(
            smtp_profile["src_email"],
            smtp_profile["dest_email"],
            msg.as_string(),
        )
        # Email Sent
    except smtplib.SMTPException as error:
        LOG.info(f"Email send error with SMTP fail: {str(error)}")
        raise
