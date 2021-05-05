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
        "backup_service_period",
        default=60,
        min=10,
        help=_("The time of bakup period, the unit is one minute."),
    ),
    cfg.StrOpt(
        "backup_metadata_key",
        default="__automated_backup",
        help=_("The key string of metadata the VM, which requres back up, has"),
    ),
    cfg.IntOpt(
        "max_backup_count",
        default=10,
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
        "retention_service_period",
        default=20,
        min=10,
        help=_("The period of the retention service, the unit is one second."),
    ),
    cfg.IntOpt(
        "rotation_workers",
        default=1,
        help=_("The maximum number of rotation processes to "
               "fork and run. Default to number of CPUs on the host."),
    ),
    cfg.StrOpt(
        "retention_time",
        default="2w3d",
        help=_("The time of retention period, the for mat is "
               "<YEARS>y<MONTHS>m<WEEKS>w<DAYS>d."),
    ),
]

CONDUCTOR_OPTS = (backup_opts, rotation_opts)


def register_opts(conf):
    conf.register_group(conductor_group)
    conf.register_opts(backup_opts, group=conductor_group)
    conf.register_opts(rotation_opts, group=conductor_group)


def list_opts():
    return {"DEFAULT": rotation_opts, conductor_group: backup_opts}
