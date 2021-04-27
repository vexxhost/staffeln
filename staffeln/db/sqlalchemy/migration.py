import os

import alembic
from alembic import config as alembic_config
import alembic.migration as alembic_migration
from oslo_db import exception as db_exec

from staffeln.i18n import _
from staffeln.db.sqlalchemy import api as sqla_api
from staffeln.db.sqlalchemy import models


def _alembic_config():
    path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    config = alembic_config.Config(path)
    return config


def create_schema(config=None, engine=None):
    """Create database schema from models description/

    Can be used for initial installation.
    """
    if engine is None:
        engine = sqla_api.get_engine()

    models.Base.metadata.create_all(engine)
