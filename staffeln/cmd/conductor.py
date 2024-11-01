"""Starter script for the staffeln conductor service."""

from __future__ import annotations

import cotyledon
from cotyledon import oslo_config_glue

from staffeln.common import service
from staffeln.conductor import manager
import staffeln.conf

CONF = staffeln.conf.CONF


def main():
    service.prepare_service()

    sm = cotyledon.ServiceManager()
    sm.add(
        manager.BackupManager,
        workers=CONF.conductor.backup_workers,
        args=(CONF,),
    )
    sm.add(
        manager.RotationManager,
        workers=CONF.conductor.rotation_workers,
        args=(CONF,),
    )
    oslo_config_glue.setup(sm, CONF)
    sm.run()
