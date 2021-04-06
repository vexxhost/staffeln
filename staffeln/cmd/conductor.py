"""Starter script for the staffeln conductor service."""

import cotyledon
from cotyledon import oslo_config_glue

from staffeln.common import service
from staffeln import conductor
import staffeln.conf


CONF = staffeln.conf.CONF


def main():
    service.prepare_service()

    sm = cotyledon.ServiceManager()
    sm.add(conductor.BackupService,
           workers=CONF.conductor.workers, args=(CONF,))
    oslo_config_glue.setup(sm, CONF)
    sm.run()
