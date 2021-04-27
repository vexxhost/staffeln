from oslo_config import cfg

from staffeln.conf import api
from staffeln.conf import conductor
from staffeln.conf import database
# from staffeln.conf import paths

CONF = cfg.CONF

api.register_opts(CONF)
conductor.register_opts(CONF)
database.register_opts(CONF)
# paths.register_opts(CONF)
