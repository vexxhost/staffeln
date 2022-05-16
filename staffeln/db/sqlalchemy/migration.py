from staffeln.db.sqlalchemy import api as sqla_api
from staffeln.db.sqlalchemy import models


def create_schema(config=None, engine=None):
    """Create database schema from models description/

    Can be used for initial installation.
    """
    if engine is None:
        engine = sqla_api.get_engine()

    models.Base.metadata.create_all(engine)
