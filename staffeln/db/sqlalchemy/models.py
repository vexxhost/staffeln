"""
SQLAlchemy models for staffeln service
"""

from oslo_db.sqlalchemy import models
from oslo_serialization import jsonutils
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import orm
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import UniqueConstraint
import urllib.parse as urlparse
from staffeln import conf

CONF = conf.CONF


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == "mysql":
        return {"mysql_engine": CONF.database.mysql_engine, "mysql_charset": "utf8"}
    return None


class StaffelnBase(models.TimestampMixin, models.ModelBase):
    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d

    def save(self, session=None):
        import staffeln.db.sqlalchemy.api as db_api

        if session is None:
            session = db_api.get_session()

        super(StaffelnBase, self).save(session)


Base = declarative_base(cls=StaffelnBase)


class Backup_data(Base):
    """Represent the backup_data"""

    __tablename__ = "backup_data"
    __table_args__ = (
        UniqueConstraint("backup_id", name="unique_backup0uuid"),
        table_args(),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_id = Column(String(100))
    volume_id = Column(String(100))
    instance_id = Column(String(100))
    backup_completed = Column(Integer())


class Queue_data(Base):
    """Represent the queue of the database"""

    __tablename__ = "queue_data"
    __table_args__ = table_args()
    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_id = Column(String(100))
    volume_id = Column(String(100))
    backup_status = Column(Integer())
    instance_id = Column(String(100))
