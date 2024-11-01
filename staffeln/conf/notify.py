from __future__ import annotations

from oslo_config import cfg

from staffeln.i18n import _

notify_group = cfg.OptGroup(
    "notification",
    title="Notification options",
    help=_(
        "Options under this group are used to define notification settings."
    ),
)

email_opts = [
    cfg.ListOpt(
        "receiver",
        default=[],
        help=_(
            "The receivers of the backup result by email."
            "A list of addresses to receive backup result emails to.  A bare"
            " string will be treated as a list with 1 address."
        ),
    ),
    cfg.StrOpt(
        "project_receiver_domain",
        help=_(
            "The project receiver domain that will be combine with project "
            "name as project report receive target email address. "
            "Format: $(project_name)@project_receiver_domain"
        ),
    ),
    cfg.StrOpt(
        "sender_email",
        help=_(
            "Log in on an SMTP server that requires authentication."
            "The user name to authenticate with."
        ),
    ),
    # We can remove the sender password as we are using postfix to send
    # mail and we won't be authenticating.
    cfg.StrOpt(
        "sender_pwd",
        help=_(
            "Log in on an SMTP server that requires authentication."
            "The password for the authentication."
        ),
    ),
    cfg.StrOpt(
        "smtp_server_domain",
        default="localhost",
        help=_("the name of the remote host to which to connect"),
    ),
    cfg.StrOpt(
        "smtp_server_port",
        default="25",
        help=_("the port to which to connect"),
    ),
]


def register_opts(conf):
    conf.register_group(notify_group)
    conf.register_opts(email_opts, group=notify_group)


def list_opts():
    return {notify_group: email_opts}
