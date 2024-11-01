from __future__ import annotations

from oslo_config import cfg

from staffeln.i18n import _

api_group = cfg.OptGroup(
    "api",
    title="API options",
    help=_("Options under this group are used to define staffeln API."),
)

connection_opts = [
    cfg.StrOpt(
        "host",
        default="0.0.0.0",
        help=_("IP address on which the staffeln API will listen."),
    ),
    cfg.PortOpt(
        "port",
        default=8808,
        help=_(
            "Staffeln API listens on this port number for incoming requests."
        ),
    ),
    cfg.BoolOpt("enabled_ssl", default=False, help=_("ssl enabled")),
    cfg.StrOpt("ssl_key_file", default=False, help=_("ssl key file path")),
    cfg.StrOpt("ssl_cert_file", default=False, help=_("ssl cert file path")),
]

API_OPTS = connection_opts


def register_opts(conf):
    conf.register_group(api_group)
    conf.register_opts(API_OPTS, group=api_group)


def list_opts():
    return {api_group: API_OPTS}
