"""Base classes for storage engines"""

import abc
from oslo_config import cfg
from oslo_db import api as db_api

_BACKEND_MAPPING = {'sqlalchemy': 'staffeln.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(
    cfg.CONF, backend_mapping=_BACKEND_MAPPING, lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


class BaseConnection(object, metaclass=abc.ABCMeta):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def create_backup(self, values):
        """Create new backup.

        :param values: A dict containing several items used to add
                       the backup. For example:

                       ::

                        {
                            'uuid': short_id.generate_uuid(),
                            'volume_name': 'Dummy',
                        }
        :returns: A backup
        """
