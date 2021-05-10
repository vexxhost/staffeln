import os

from oslo_config import cfg
from staffeln.i18n import _

PATH_OPTS = [
    cfg.StrOpt(
        "pybasedir",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "../")),
        help=_("Directory where the staffeln python module is installed."),
    ),
    cfg.StrOpt(
        "bindir",
        default="$pybasedir/bin",
        help=_("Directory where staffeln binaries are installed."),
    ),
    cfg.StrOpt(
        "state_path",
        default="$pybasedir",
        help=_("Top-level directory for maintaining staffeln's state."),
    ),
]


def basedir_def(*args):
    """Return an uninterpolated path relative to $pybasedir."""
    return os.path.join("$pybasedir", *args)


def bindir_def(*args):
    """Return an uninterpolated path relative to $bindir."""
    return os.path.join("$bindir", *args)


def state_path_def(*args):
    """Return an uninterpolated path relative to $state_path."""
    return os.path.join("$state_path", *args)


def register_opts(conf):
    conf.register_opts(PATH_OPTS)


def list_opts():
    return [("DEFAULT", PATH_OPTS)]
