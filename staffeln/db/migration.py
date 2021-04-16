"""Database setup and migration commands."""


from oslo_config import cfg
from stevedore import driver
import staffeln.conf

CONF = staffeln.conf.CONF

_IMPL = None


def get_backend():
    global _IMPL
    if not _IMPL:
        # cfg.CONF.import_opt('backend', 'oslo_db.options', group='database')
        _IMPL = driver.DriverManager(
            "staffeln.database.migration_backend", CONF.database.backend).driver
    return _IMPL


def create_schema():
    return get_backend().create_schema()
