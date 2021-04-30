from staffeln.common import short_id
from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class Queue(
    base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat
):
    VERSION = "1.0"

    dbapi = db_api.get_instance()

    fields = {
        "id": sfeild.IntegerField(),
        "backup_id": sfeild.StringField(),
        "volume_id": sfeild.UUIDField(),
        "instance_id": sfeild.StringField(),
        "backup_status": sfeild.IntegerField(),
    }

    @base.remotable_classmethod
    def list(cls, context, filters=None):
        db_queue = cls.dbapi.get_queue_list(context, filters=filters)
        return [cls._from_db_object(cls(context), obj) for obj in db_queue]

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        """Find a backup based on backup_id
        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Queue(context)
        :param backup_id: the backup id of volume in queue.
        :returns: a :class:`Queue` object.
        """
        db_queue = cls.dbapi.get_queue_by_id(context, id)
        queue = cls._from_db_object(cls(context), db_queue)
        return queue

    @base.remotable
    def create(self):
        """Create a :class:`Backup_data` record in the DB"""
        values = self.obj_get_changes()
        db_queue = self.dbapi.create_queue(values)
        self._from_db_object(self, db_queue)

    @base.remotable
    def save(self):
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_queue(self.id, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self):
        current = self.get_by_backup_id(backup_id=self.backup_id)
        self.obj_refresh(current)

    @base.remotable
    def delete_queue(self):
        """Soft Delete the :class:`Queue_data` from the DB"""
        db_obj = self.dbapi.soft_delete_queue(self.id)
