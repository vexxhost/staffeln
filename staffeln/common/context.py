from oslo_context import context
from oslo_log import log

LOG = log.getLogger(__name__)


class RequestContext(context.RequestContext):
    """Added security context with request parameters from openstack common library"""

    def __init__(
        self,
        backup_id=None,
        volume_id=None,
        instance_id=None,
        executed_at=None,
        backup_status=None,
        **kwargs
    ):
        self.backup_id = backup_id
        self.volume_id = volume_id
        self.instance_id = instance_id
        self.backup_id = backup_id
        self.executed_at = executed_at


def make_context(*args, **kwargs):
    return RequestContext(*args, **kwargs)
