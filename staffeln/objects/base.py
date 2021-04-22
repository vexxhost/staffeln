"""Staffeln common internal object model"""

from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import fields as ovoo_fields

from staffeln import objects


remotable_classmethod = ovoo_base.remotable_classmethod
remotable = ovoo_base.remotable


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    # FIXME(danms): This is just until we use o.vo's class properties
    # and object base.
    return '_obj_' + name


class StaffelnObject(ovoo_base.VersionedObject):
    """Base class and object factory.

    This forms the base of all objects that can be remoted or instantiated
    via RPC. Simply defining a class that inherits from this base class
    will make it remotely instantiatable. Objects should implement the
    necessary "get" classmethod routines as well as "save" object methods
    as appropriate.
    """
    OBJ_SERIAL_NAMESPACE = 'staffeln_object'
    OBJ_PROJECT_NAMESPACE = 'staffeln'

    def as_dict(self):
        return {k: getattr(self, k)
                for k in self.fields
                if self.obj_attr_is_set(k)}


class StaffelnObjectSerializer(ovoo_base.VersionedObjectSerializer):
    # Base class to use for object hydration
    OBJ_BASE_CLASS = StaffelnObject


class StaffelnPersistentObject(object):
    feilds = {
        'created_at': ovoo_fields.DateTimeField(nullable=True),
        'updated_at': ovoo_fields.DateTimeField(nullable=True),
        'deleted_at': ovoo_fields.DateTimeField(nullable=True),
    }

    object_fields = {}

    def obj_refresh(self, loaded_object):
        fields = (field for field in self.feilds if field not in self.object_fields)
        for field in fields:
            if (self.obj_attr_is_set(field) and self[field] != loaded_object[field]):
                self[field] = loaded_object[field]

    @staticmethod
    def _from_db_object(obj, db_object, eager=False):
        obj_class = type(obj)
        object_fields = obj_class.object_fields

        for field in obj.fields:
            if field not in object_fields:
                obj[field] = db_object[field]

        obj.obj_reset_changes()
        return obj


class StaffelnObjectRegistry(ovoo_base.VersionedObjectRegistry):
    def registration_hook(self, cls, index):
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            cur_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= cur_version:
                setattr(objects, cls.obj_name(), cls)


class StaffelnObjectDictCompat(ovoo_base.VersionedObjectDictCompat):
    pass
