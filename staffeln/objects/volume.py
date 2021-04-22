from staffeln.common import short_id
from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class Volume(base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat):
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    fields = {
        'id': sfeild.IntegerField(),
        'backup_id': sfeild.StringField(),
        'instance_id': sfeild.StringField(),
        'volume_id': sfeild.UUIDField()
    }

    @base.remotable
    def list(cls, filters=None):
        """Return a list of :class:`Backup` objects.

        :param filters: dict mapping the filter to a value.
        """
        db_backups = cls.dbapi.get_backup_list(filters=filters)

        return [cls._from_db_object(cls, obj) for obj in db_backups]

    @base.remotable
    def create(self):
        """Create a :class:`Backup_data` record in the DB"""
        values = self.obj_get_changes()
        print(values)
        db_backup = self.dbapi.create_backup(values)
        self._from_db_object(self, db_backup)

    @base.remotable
    def save(self):
        """Save updates to the :class:`Backup_data`.

        Updates will be made column by column based on the results
        of self.what_changed().
        """
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_backup(self.uuid, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self):
        """Loads updates for this :class:`Backup_data`.
        Loads a backup with the same backup_id from the database and
        checks for updated attributes. Updates are applied from
        the loaded backup column by column, if there are any updates.
        """
        current = self.get_by_uuid(uuid=self.uuid)
        self.obj_refresh(current)
