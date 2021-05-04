# Email notification package
# This should be upgraded by integrating with mail server to send batch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import staffeln.conf

CONF = staffeln.conf.CONF


def sendEmail(src_email, src_pwd, dest_email, subject, content, smtp_server_domain, smtp_server_port):
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = src_email
        message["To"] = dest_email
        part = MIMEText(content, "html")
        message.attach(part)

        s = smtplib.SMTP(host=smtp_server_domain, port=smtp_server_port)
        s.ehlo()
        s.starttls()
        # we can comment this auth func when use the trusted ip without authentication against the smtp server
        s.login(src_email, src_pwd)
        s.sendmail(src_email, dest_email, message.as_string())
        s.close()
        return True
    except Exception as e:
        print(str(e))
        return False

def SendNotification(content, receiver=None):
    subject = "Backup result"

    html = "<h3>${CONTENT}</h3>"
    html = html.replace("${CONTENT}", content)

    if receiver == None:
        return
    if len(receiver) == 0:
        return

    res = sendEmail(src_email=CONF.notification.sender_email,
                        src_pwd=CONF.notification.sender_pwd,
                        dest_email=CONF.notification.receiver,
                        subject=subject,
                        content=html,
                        smtp_server_domain=CONF.notification.smtp_server_domain,
                        smtp_server_port=CONF.notification.smtp_server_port)
