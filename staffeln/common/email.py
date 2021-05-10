# Email notification package
# This should be upgraded by integrating with mail server to send batch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

__DRY_RUN__ = True


def send(
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
    if __DRY_RUN__:
        print(part)
        return
    s = smtplib.SMTP(host=smtp_server_domain, port=smtp_server_port)
    # s.ehlo()
    # s.starttls()
    # we can comment this auth func when use the trusted ip without authentication against the smtp server
    # s.login(src_email, src_pwd)
    s.sendmail(src_email, dest_email, message.as_string())
    s.close()
