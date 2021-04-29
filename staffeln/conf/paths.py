from oslo_config import cfg

import os

PATH_OPTS = [
    cfg.StrOpt(
        "state_path",
        default="$pybasedir",
        help="Top-level directory for maintaining staffeln's state.",
    ),
]


def state_path_def(*args):
    """Return an uninterpolated path relative to $state_path."""
    return os.path.join("$state_path", *args)


def register_opts(conf):
    conf.register_opts(PATH_OPTS)


def list_opts():
    return [("DEFAULT", PATH_OPTS)]
