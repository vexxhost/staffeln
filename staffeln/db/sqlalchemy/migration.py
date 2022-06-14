import os

import staffeln.conf
from oslo_db.sqlalchemy.migration_cli import manager
from staffeln.db.sqlalchemy import api as sqla_api
from staffeln.db.sqlalchemy import models

CONF = staffeln.conf.CONF
_MANAGER = None


def get_manager():
    global _MANAGER
    if not _MANAGER:
        alembic_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alembic.ini")
        )
        migrate_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "alembic")
        )
        migration_config = {
            "alembic_ini_path": alembic_path,
            "alembic_repo_path": migrate_path,
            "db_url": CONF.database.connection,
        }
        _MANAGER = manager.MigrationManager(migration_config)

    return _MANAGER


def create_schema(config=None, engine=None):
    """Create database schema from models description/

    Can be used for initial installation.
    """
    if engine is None:
        engine = sqla_api.get_engine()

    models.Base.metadata.create_all(engine)


def upgrade(version):
    """Used for upgrading database.

    :param version: Desired database version
    :type version: string
    """
    version = version or "head"

    get_manager().upgrade(version)
