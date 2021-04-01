from oslo_config import cfg

conductor_group = cfg.OptGroup(
    'conductor',
    title='Conductor Options',
    help="""
Options under this group are used to define Conductor's configuration.
""", 
)

backup_opts = [ 
    cfg.IntOpt(
        'backup_period',
        default=1,
        min=1,
        help="""
The time of bakup period, the unit is one minute.
"""),
]

rotation_opts = [ 
    cfg.IntOpt(
        'rotation_default_period',
        default=1,
        min=1,
        help="""
The time of rotation period, the unit is one day.
"""),
]


def register_opts(conf):
    conf.register_group(conductor_group)


def list_opts():
    return {"DEFAULT": backup_opts,
            conductor_group: rotation_opts}
