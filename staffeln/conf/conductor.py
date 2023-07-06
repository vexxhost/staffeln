from oslo_config import cfg
from staffeln.common import constants
from staffeln.i18n import _

conductor_group = cfg.OptGroup(
    "conductor",
    title="Conductor Options",
    help=_("Options under this group are used " "to define Conductor's configuration."),
)
lock_opts = [
    cfg.IntOpt(
        "lock_timeout",
        default=7200,
        help=_("The timeout seconds before released a tooz lock."),
    ),
]

backup_opts = [
    cfg.IntOpt(
        "backup_workers",
        default=1,
        help=_(
            "The maximum number of backup processes to "
            "fork and run. Default to number of CPUs on the host."
        ),
    ),
    cfg.IntOpt(
        "backup_service_period",
        default=1800,
        min=60,
        help=_("The time of bakup period, the unit is one second."),
    ),
    cfg.IntOpt(
        "backup_min_interval",
        default=1800,
        min=0,
        help=_(
            "The time of minimum guaranteed interval between Staffeln "
            "created backups, the unit is one seconds. Set to 0 if don't "
            "need to enable this feature."
        ),
    ),
    cfg.IntOpt(
        "report_period",
        default=86400,
        min=600,
        help=_("The time of report period, the unit is one seconds."),
    ),
    cfg.StrOpt(
        "backup_cycle_timout",
        regex=(
            r"((?P<years>\d+?)y)?((?P<months>\d+?)mon)?((?P<weeks>\d+?)w)?"
            r"((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)min)?((?P<seconds>\d+?)s)?"
        ),
        default=constants.DEFAULT_BACKUP_CYCLE_TIMEOUT,
        help=_(
            "The duration while the backup cycle waits backups."
            "<YEARS>y<MONTHS>mon<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."
        ),
    ),
    cfg.StrOpt(
        "backup_metadata_key",
        help=_("The key string of metadata the VM, which requres back up, has"),
    ),
    cfg.StrOpt(
        "retention_metadata_key",
        help=_(
            "The key string of metadata the VM, which use as backup retention period."
        ),
    ),
    cfg.IntOpt(
        "full_backup_depth",
        default=2,
        min=0,
        help=_("Number of incremental backups between full backups."),
    ),
]

rotation_opts = [
    cfg.IntOpt(
        "rotation_workers",
        default=1,
        help=_(
            "The maximum number of rotation processes to "
            "fork and run. Default to number of CPUs on the host."
        ),
    ),
    cfg.IntOpt(
        "retention_service_period",
        default=1200,
        min=60,
        help=_("The period of the retention service, the unit is one second."),
    ),
    cfg.IntOpt(
        "rotation_workers",
        default=1,
        help=_(
            "The maximum number of rotation processes to "
            "fork and run. Default to number of CPUs on the host."
        ),
    ),
    cfg.StrOpt(
        "retention_time",
        regex=(
            r"((?P<years>\d+?)y)?((?P<months>\d+?)mon)?((?P<weeks>\d+?)w)?"
            r"((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)min)?((?P<seconds>\d+?)s)?"
        ),
        default="2w3d",
        help=_(
            "The time of retention period, the for mat is "
            "<YEARS>y<MONTHS>mon<WEEKS>w<DAYS>d<HOURS>h<MINUTES>min<SECONDS>s."
        ),
    ),
]

CONDUCTOR_OPTS = (backup_opts, rotation_opts)


def register_opts(conf):
    conf.register_group(conductor_group)
    conf.register_opts(backup_opts, group=conductor_group)
    conf.register_opts(rotation_opts, group=conductor_group)
    conf.register_opts(lock_opts, group=conductor_group)


def list_opts():
    return {"DEFAULT": rotation_opts, conductor_group: backup_opts}
