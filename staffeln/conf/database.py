from oslo_config import cfg
from oslo_db import options as oslo_db_options
from staffeln.conf import paths
from staffeln.i18n import _

_DEFAULT_SQL_CONNECTION = "sqlite:///{0}".format(
    paths.state_path_def("staffeln.sqlite")
)

database = cfg.OptGroup(
    "database",
    title="Database options",
    help=_("Options under this group are used for defining database."),
)

SQL_OPTS = [
    cfg.StrOpt("mysql_engine", default="InnoDB",
               help=_("MySQL engine to use.")),
]


def register_opts(conf):
    oslo_db_options.set_defaults(conf, connection=_DEFAULT_SQL_CONNECTION)
    conf.register_group(database)
    conf.register_opts(SQL_OPTS, group=database)


def list_opts():
    return [(database, SQL_OPTS)]
