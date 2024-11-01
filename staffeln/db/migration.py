"""Database setup command"""

from __future__ import annotations

from stevedore import driver

import staffeln.conf

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


def upgrade(version=None):
    """Migrate the database to `version` or the most recent version."""
    return get_backend().upgrade(version)
