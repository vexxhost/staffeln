# from staffeln.common import rpc
from __future__ import annotations

import staffeln.conf
from staffeln import version

CONF = staffeln.conf.CONF


def parse_args(argv, default_config_files=None):
    # rpc.set_defaults(control_exchange='staffeln')
    CONF(
        argv[1:],
        project="staffeln",
        version=version.version_info.release_string(),
        default_config_files=default_config_files,
    )
    # rpc.init(CONF)


def set_config_defaults():
    pass
