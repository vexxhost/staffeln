from datetime import datetime, timezone

from oslo_utils import uuidutils

import staffeln.conf
from staffeln.objects import puller

CONF = staffeln.conf.CONF


class Puller(object):
    def __init__(self, context, node_id=None):
        self.ctx = context

        self.node_id = (
            uuidutils.generate_uuid() if node_id is None else node_id
        )
        self.puller = None

    def fetch_puller_role(self):
        target_puller = puller.Puller.get(context=self.ctx)

        # No puller, run for puller role
        if not target_puller:
            self.puller = puller.Puller(self.ctx)
            self.puller.node_id = self.node_id
            self.puller.updated_at = datetime.now(timezone.utc)
            self.puller.create()
            return True
        # If puller expired, run for new puller role
        elif self.is_old_puller(target_puller):
            self.puller = puller.Puller(self.ctx)
            self.puller.node_id = self.node_id
            self.puller.updated_at = datetime.now(timezone.utc)
            self.puller.save()
            return True
        else:
            return False

        self.puller = puller.Puller.get(context=self.ctx)
        # Return True if this new puller's node_id is this node.
        return self.puller.node_id == self.node_id

    def is_old_puller(self, target_puller):
        valid_period = CONF.conductor.backup_service_period * 2
        # Check if puller have not been update for more than two
        # backup_service_period.
        return True if (
            datetime.now(timezone.utc) - target_puller.updated_at
        ).total_seconds() > valid_period else False

    def renew_update_time(self):
        if self.puller is None:
            return
        self.puller = puller.Puller.get(context=self.ctx)

        if self.puller.node_id == self.node_id:
            self.puller.updated_at = datetime.now(timezone.utc)
            self.puller.save()
