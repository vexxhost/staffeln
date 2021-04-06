"""Staffeln common internal object model"""

from oslo_versionedobjects import base as ovoo_base
# from oslo_versionedobjects import fields as ovoo_fields


remotable_classmethod = ovoo_base.remotable_classmethod
remotable = ovoo_base.remotable


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
