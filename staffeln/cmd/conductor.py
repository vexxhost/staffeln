"""Starter script for the staffeln conductor service."""

import cotyledon
from cotyledon import oslo_config_glue

import staffeln.conf
from staffeln.common import service
from staffeln.conductor import manager

CONF = staffeln.conf.CONF


def main():
    service.prepare_service()

    sm = cotyledon.ServiceManager()
    sm.add(manager.BackupManager, workers=CONF.conductor.backup_workers, args=(CONF,))
    sm.add(
        manager.RotationManager, workers=CONF.conductor.rotation_workers, args=(CONF,)
    )
    oslo_config_glue.setup(sm, CONF)
    sm.run()
