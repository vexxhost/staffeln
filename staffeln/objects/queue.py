from staffeln.common import short_id
from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class Queue(base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat):
    VERSION = '1.0'

    dbapi = db_api.get_instance()

    feilds = {
        'id': sfeild.IntegerField(),
        'backup_id': sfeild.StringField(),
        'volume_id': sfeild.UUIDField(),
        'instance_id': sfeild.StringField(),
        'backup_status': sfeild.IntegerField(),
        'executed_at': sfeild.DateTimeField()
    }

    @base.remotable_classmethod
    def list(cls, context, filters=None):
        db_queue = cls.dbapi.get_queue_list(context, filters=filters)
        return [cls._from_db_object(cls(context), obj) for obj in db_queue]

    @base.remotable
    def create(self):
        values = self.obj_get_changes()
        db_queue = self.dbapi.create_queue(values)
        self._from_db_object(self, db_queue)

    @base.remotable
    def save(self):
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_queue(self.backup_id, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    @base.remotable
    def refresh(self):
        current = self.get_by_uuid(uuid=self.uuid)
        self.obj_refresh(current)
