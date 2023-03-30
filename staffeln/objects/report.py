from oslo_versionedobjects import fields as ovoo_fields

from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class ReportTimestamp(
    base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat
):
    VERSION = "1.0"
    # Version 1.0: Initial version

    dbapi = db_api.get_instance()

    fields = {
        "id": sfeild.IntegerField(),
        "sender": sfeild.StringField(nullable=True),
        "created_at": ovoo_fields.DateTimeField(),
    }

    @base.remotable_classmethod
    def list(cls, context, filters=None):  # pylint: disable=E0213
        db_report = cls.dbapi.get_report_timestamp_list(context, filters=filters)
        return [cls._from_db_object(cls(context), obj) for obj in db_report]

    @base.remotable
    def create(self):
        """Create a :class:`report_timestamp` record in the DB"""
        values = self.obj_get_changes()
        db_report_timestamp = self.dbapi.create_report_timestamp(values)
        return self._from_db_object(self, db_report_timestamp)

    @base.remotable
    def save(self):
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_report_timestamp(self.id, updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    @base.remotable
    def delete(self):
        """Soft Delete the :class:`report_timestamp` from the DB"""
        self.dbapi.soft_delete_report_timestamp(self.id)
