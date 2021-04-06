from oslo_config import cfg

from staffeln.conf import api
from staffeln.conf import conductor


CONF = cfg.CONF

api.register_opts(CONF)
conductor.register_opts(CONF)
