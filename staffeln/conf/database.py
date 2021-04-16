from oslo_config import cfg
from oslo_db import options as oslo_db_options

_DEFAULT_SQL_CONNECTION = 'mysql+pymysql://root:password@localhost:3306/staffeln'

database = cfg.OptGroup(
    'database',
    title='Database options',
    help='Options under this group are used for defining database.'
)

SQL_OPTS = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.'
               ),
]


def register_opts(conf):
    oslo_db_options.set_defaults(conf, connection=_DEFAULT_SQL_CONNECTION)
    conf.register_group(database)
    conf.register_opts(SQL_OPTS, group=database)


def list_opts():
    return [(database, SQL_OPTS)]
