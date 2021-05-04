from oslo_config import cfg
from staffeln.i18n import _


conductor_group = cfg.OptGroup(
    "conductor",
    title="Conductor Options",
    help=_("Options under this group are used " "to define Conductor's configuration."),
)

backup_opts = [
    cfg.IntOpt(
        "backup_workers",
        default=1,
        help=_("The maximum number of backup processes to "
        "fork and run. Default to number of CPUs on the host."),
    ),
    cfg.IntOpt(
        "backup_period",
        default=10,
        min=1,
        help=_("The time of bakup period, the unit is one minute."),
    ),
    cfg.StrOpt(
        "backup_metadata_key",
        default="test",
        help=_("The key string of metadata the VM, which requres back up, has"),
    ),
]

rotation_opts = [
    cfg.IntOpt(
        "rotation_workers",
        default=1,
        help=_("The maximum number of rotation processes to "
        "fork and run. Default to number of CPUs on the host."),
    ),
    cfg.IntOpt(
        "rotation_period",
        default=1,
        min=1,
        help=_("The time of rotation period, the unit is one day."),
    ),
]

CONDUCTOR_OPTS = (backup_opts, rotation_opts)


def register_opts(conf):
    conf.register_group(conductor_group)
    conf.register_opts(backup_opts, group=conductor_group)
    conf.register_opts(rotation_opts, group=conductor_group)


def list_opts():
    return {"DEFAULT": rotation_opts, conductor_group: backup_opts}
