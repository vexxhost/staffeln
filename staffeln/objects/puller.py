from oslo_versionedobjects import fields as ovoo_fields

from staffeln.db import api as db_api
from staffeln.objects import base
from staffeln.objects import fields as sfeild


@base.StaffelnObjectRegistry.register
class Puller(
    base.StaffelnPersistentObject, base.StaffelnObject, base.StaffelnObjectDictCompat
):
    VERSION = "1.0"

    dbapi = db_api.get_instance()

    fields = {
        "id": sfeild.IntegerField(),
        "node_id": sfeild.UUIDField(),
        "updated_at": ovoo_fields.DateTimeField(),
    }

    @base.remotable_classmethod
    def get(cls, context):  # pylint: disable=E0213
        """Get puller
        :param context: Security context. NOTE: This should only
                        be used internally by the indirection_api.
                        Unfortunately, RPC requires context as the first
                        argument, even though we don't use it.
                        A context should be set when instantiating the
                        object, e.g.: Queue(context)
        :returns: a :class:`Puller` object.
        """
        db_puller = cls.dbapi.get_puller()
        if not db_puller:
            return None
        puller = cls._from_db_object(cls(context), db_puller)
        return puller

    @base.remotable
    def create(self):
        """Create a :class:`Puller` record in the DB"""
        values = self.obj_get_changes()
        db_puller = self.dbapi.create_puller(values)
        self._from_db_object(self, db_puller)

    @base.remotable
    def save(self):
        updates = self.obj_get_changes()
        db_obj = self.dbapi.update_puller(id=1, values=updates)
        obj = self._from_db_object(self, db_obj, eager=False)
        self.obj_refresh(obj)
        self.obj_reset_changes()

    def refresh(self):
        obj = self.get()
        self.obj_refresh(obj)
