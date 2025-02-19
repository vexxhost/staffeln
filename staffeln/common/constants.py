from __future__ import annotations

BACKUP_INIT = 4
BACKUP_FAILED = 3
BACKUP_COMPLETED = 2
BACKUP_WIP = 1
BACKUP_PLANNED = 0

BACKUP_ENABLED_KEY = "true"
BACKUP_RESULT_CHECK_INTERVAL = 60  # second

# default config values
DEFAULT_BACKUP_CYCLE_TIMEOUT = "5min"

PULLER = "puller"
RETENTION = "retention"
