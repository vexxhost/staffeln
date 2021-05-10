"""Database setup command"""

import staffeln.conf
from stevedore import driver

CONF = staffeln.conf.CONF

_IMPL = None


def get_backend():
    global _IMPL
    if not _IMPL:
        _IMPL = driver.DriverManager(
            "staffeln.database.migration_backend", CONF.database.backend
        ).driver
    return _IMPL


def create_schema():
    return get_backend().create_schema()
