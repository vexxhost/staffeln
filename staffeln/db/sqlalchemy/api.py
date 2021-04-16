"""SQLAlchemy storage backend."""

import collections
import datetime
import operator

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import timeutils
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import exc


from staffeln.i18n import _
from staffeln.common import config
from staffeln.db import api
from staffeln.db.sqlalchemy import models
from staffeln.common import short_id

CONF = cfg.CONF

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def model_query(model, *args, **kwargs):
    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


class Connection(api.BaseConnection):
    """SQLAlchemy connection."""

    def __init__(self):
        super(Connection, self).__init__()

    def _get_relationships(model):
        return inspect(model).relationships

    def _create(self, model, values):
        obj = model()

        cleaned_values = {k: v for k, v in values.items()
                          if k not in self._get_relationships(model)}
        obj.update(cleaned_values)
        obj.save()
        return obj

    def create_backup(self, values):
        # ensure uuid are present for new backup
        if not values.get('uuid'):
            values['uuid'] = short_id.generate_id()

        try:
            backup_data = self._create(models.Backup_data, values)
        except db_exc.DBDuplicateEntry:
            pass
        return goal
