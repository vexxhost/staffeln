from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class Volume(
    base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat
):
    VERSION = "1.0"

    dbapi = db_api.get_instance()

    fields = {
        "id": sfeild.IntegerField(),
        "backup_id": sfeild.StringField(),
        "instance_id": sfeild.StringField(),
        "volume_id": sfeild.UUIDField(),
        "backup_completed": sfeild.IntegerField(),
    }

    @base.remotable_classmethod
    def list(cls, context, filters=None):
        """Return a list of :class:`Backup` objects.

        :param filters: dict mapping the filter to a value.
        """
        db_backups = cls.dbapi.get_backup_list(context, filters=filters)

        return [cls._from_db_object(cls(context), obj) for obj in db_backups]

    @base.remotable
    def create(self):
        """Create a :class:`Backup_data` record in the DB"""
        values = self.obj_get_changes()
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
        current = self.get_by_uuid(backup_id=self.backup_id)
        self.obj_refresh(current)

    @base.remotable
    def delete_backup(self):
        """Soft Delete the :class:`Queue_data` from the DB"""
        db_obj = self.dbapi.soft_delete_backup(self.id)
