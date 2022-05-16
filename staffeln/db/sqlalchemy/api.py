"""SQLAlchemy storage backend."""

import datetime
import operator

from oslo_config import cfg
from oslo_log import log
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import timeutils
from oslo_utils import strutils
from oslo_utils import uuidutils
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import exc

from staffeln.db.sqlalchemy import models
from staffeln.common import short_id


LOG = log.getLogger(__name__)

CONF = cfg.CONF

_FACADE = None

is_uuid_like = uuidutils.is_uuid_like
is_int_like = strutils.is_int_like


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


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    session = kwargs.get("session") or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.
    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by backup_id.
    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if is_int_like(value):
        return query.filter_by(id=value)
    else:
        LOG.error("Invalid Identity")


def _paginate_query(
    model, limit=None, marker=None, sort_key=None, sort_dir=None, query=None
):
    if not query:
        query = model_query(model)
    sort_keys = ["id"]
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(
        query, model, limit, sort_keys, marker=marker, sort_dir=sort_dir
    )
    return query.all()


class Connection(object):
    """SQLAlchemy connection."""

    valid_operators = {
        "": operator.eq,
        "eq": operator.eq,
        "neq": operator.ne,
        "gt": operator.gt,
        "gte": operator.ge,
        "lt": operator.lt,
        "lte": operator.le,
    }

    def __init__(self):
        super(Connection, self).__init__()

    @staticmethod
    def _get_relationships(model):
        return inspect(model).relationships

    def _add_backup_filters(self, query, filters):
        """Add filters while listing the columns from the backup_data table"""
        if filters is None:
            filters = {}

        plain_fields = [
            "volume_id",
            "backup_id",
            "project_id",
            "backup_completed",
            "instance_id",
            "created_at",
        ]

        return self._add_filters(
            query=query,
            model=models.Backup_data,
            filters=filters,
            plain_fields=plain_fields,
        )

    def _add_queues_filters(self, query, filters):
        """Add filters while listing the columns from the queue_data table"""
        if filters is None:
            filters = {}

        plain_fields = [
            "backup_id",
            "project_id",
            "volume_id",
            "instance_id",
            "backup_status",
        ]

        return self._add_filters(
            query=query,
            model=models.Queue_data,
            filters=filters,
            plain_fields=plain_fields,
        )

    def _add_filters(self, query, model, filters=None, plain_fields=None):
        """Add filters while listing the columns from database table"""
        timestamp_mixin_fields = ["created_at", "updated_at"]
        filters = filters or {}

        for raw_fieldname, value in filters.items():
            fieldname, operator_ = self.__decompose_filter(raw_fieldname)

            if fieldname in plain_fields:
                query = self.__add_simple_filter(
                    query, model, fieldname, value, operator_
                )

        return query

    def __add_simple_filter(self, query, model, fieldname, value, operator_):
        field = getattr(model, fieldname)

        if (
            fieldname != "deleted"
            and value
            and field.type.python_type is datetime.datetime
        ):
            if not isinstance(value, datetime.datetime):
                value = timeutils.parse_isotime(value)
        return query.filter(self.valid_operators[operator_](field, value))

    def __decompose_filter(self, raw_fieldname):
        """Decompose a filter name into it's two subparts"""

        seperator = "__"
        fieldname, seperator, operator_ = raw_fieldname.partition(seperator)

        if operator_ and operator_ not in self.valid_operators:
            LOG.error("Invalid operator %s" % operator_)

        return fieldname, operator_

    def _get(self, context, model, fieldname, value):
        query = model_query(model)

        query = query.filter(getattr(model, fieldname) == value)

        try:
            # To avoid exception if the no result found in table.
            obj = query.one_or_none()
        except exc.NoResultFound:
            LOG.error("ResourceNotFound")

        return obj

    def _create(self, model, values):
        obj = model()
        cleaned_values = {
            k: v for k, v in values.items() if k not in self._get_relationships(model)
        }
        obj.update(cleaned_values)
        obj.save()
        return obj

    @staticmethod
    def _update(model, id_, values):
        session = get_session()
        with session.begin():
            query = model_query(model, session=session)
            query = add_identity_filter(query, id_)
            try:
                ref = query.with_for_update().one()
            except exc.NoResultFound:
                LOG.error("Update backup failed. No result found.")
            ref.update(values)
        return ref

    @staticmethod
    def _soft_delete(model, id_):
        session = get_session()
        with session.begin():
            query = model_query(model, session=session)
            query = add_identity_filter(query, id_)
            try:
                row = query.one()

            except exc.NoResultFound:
                LOG.error("Resource Not found.")

            deleted_row = session.delete(row)
            return row

    def _get_model_list(
        self,
        model,
        add_filter_func,
        context,
        filters=None,
        limit=None,
        marker=None,
        sort_key=None,
        sort_dir=None,
    ):
        query = model_query(model)

        query = add_filter_func(query, filters)
        return _paginate_query(model, limit, marker, sort_key, sort_dir, query)

    def create_backup(self, values):
        if not values.get("backup_id"):
            values["backup_id"] = short_id.generate_id()

        try:
            backup_data = self._create(models.Backup_data, values)
        except db_exc.DBDuplicateEntry:
            LOG.error("Backup ID already exists.")
        return backup_data

    def get_backup_list(self, *args, **kwargs):
        return self._get_model_list(
            models.Backup_data, self._add_backup_filters, *args, **kwargs
        )

    def update_backup(self, backup_id, values):
        if "backup_id" in values:
            LOG.error("Cannot override ID for existing backup")

        try:
            return self._update(models.Backup_data, backup_id, values)
        except:
            LOG.error("backup resource not found.")

    def create_queue(self, values):
        if not values.get("backup_id"):
            values["backup_id"] = short_id.generate_id()

        try:
            queue_data = self._create(models.Queue_data, values)
        except db_exc.DBDuplicateEntry:
            LOG.error("Backup ID already exists.")
        return queue_data

    def get_queue_list(self, *args, **kwargs):
        return self._get_model_list(
            models.Queue_data, self._add_queues_filters, *args, **kwargs
        )

    def update_queue(self, id, values):

        try:
            return self._update(models.Queue_data, id, values)
        except:
            LOG.error("Queue resource not found.")

    def get_queue_by_id(self, context, id):
        """Get the column from queue_data with matching backup_id"""
        return self._get_queue(context, fieldname="id", value=id)

    def _get_queue(self, context, fieldname, value):
        """Get the columns from queue_data table"""

        try:

            return self._get(
                context, model=models.Queue_data, fieldname=fieldname, value=value
            )
        except:
            LOG.error("Queue not found")

    def soft_delete_queue(self, id):
        try:
            return self._soft_delete(models.Queue_data, id)
        except:
            LOG.error("Queue Not found.")

    def get_backup_by_backup_id(self, context, backup_id):
        """Get the column from the backup_data with matching backup_id"""

        try:
            return self._get_backup(context, fieldname="backup_id", value=backup_id)
        except:
            LOG.error("Backup not found with backup_id %s." % backup_id)

    def _get_backup(self, context, fieldname, value):
        """Get the column from the volume_data table"""

        try:
            return self._get(
                context, model=models.Backup_data, fieldname=fieldname, value=value
            )
        except:
            LOG.error("Backup resource not found.")

    def soft_delete_backup(self, id):
        try:
            return self._soft_delete(models.Backup_data, id)
        except:
            LOG.error("Backup Not found.")
