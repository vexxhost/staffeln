"""Utility method for objects"""
from oslo_serialization import jsonutils
from oslo_versionedobjects import fields

BooleanField = fields.BooleanField
StringField = fields.StringField
DateTimeField = fields.DateTimeField
IntegerField = fields.IntegerField


class UUIDField(fields.UUIDField):
    def coerce(self, obj, attr, value):
        if value is None or value == "":
            return self._null(obj, attr)
        else:
            return self._type.coerce(obj, attr, value)


class Numeric(fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if value is None:
            return value
        f_value = float(value)
        return f_value if not f_value.is_integer() else value


class ListOfUUIDsField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.UUID())


class Json(fields.FieldType):
    def coerce(self, obj, attr, value):
        if isinstance(value, str):
            loaded = jsonutils.loads(value)
            return loaded
        return value

    def from_primitive(self, obj, attr, value):
        return self.coerce(obj, attr, value)

    def to_primitive(self, obj, attr, value):
        return jsonutils.dumps(value)


class JsonField(fields.AutoTypedField):
    AUTO_TYPE = Json()
