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
    def get_backup_list(self, filters=None):
        """Get specific columns for matching backup.

        Return a list of the specidied columns for all the backups
        that match the specified filters.

        :param filters: Filters to apply. Defaults to None.
        :return: A list of tuples of the specified columns.
        """

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

    @abc.abstractmethod
    def update_backup(self, backup_uuid, values):
        """Update properties of the backup.
        : param backup_uuid: uuid of the backup
        :param values: A dict containing several items used to add
                       the backup. For example:

                       ::

                        {
                            'backup_id': short_id.generate_uuid(),
                            'backup_status': 'completed',
                        }
        :returns: A backup
        """

    @abc.abstractmethod
    def create_queue(self, values):
        """Create entry in queue_data.
        :param values: A dict containing several items used to add 
                        the volume information for backup

                        ::
                        {
                            'backup_id': "backup_id"
                            'volume_id': "volume_id"
                            'backup_status': 0
                        }
        :returns A queue
        """

    @abc.abstractmethod
    def update_queue(self, backup_id, values):
        """Update properties of the backup.
        : param backup_id: uuid of the backup
        :param values: A dict containing several items used to add
                       the backup. For example:

                       ::

                        {
                            'backup_id': short_id.generate_uuid(),
                            'backup_status': 1
                        }
        :returns: A backup
        """

    @abc.abstractmethod
    def get_queue_list(self, filters=None):
        """Get specific columns for matching backup.

        Return a list of the specidied columns for all the queues
        that match the specified filters.

        :param filters: Filters to apply. Defaults to None.
        :return: A list of tuples of the specified columns.
        """
