from oslo_config import cfg
from staffeln.conf import api, conductor, database, notify, paths

CONF = cfg.CONF

api.register_opts(CONF)
conductor.register_opts(CONF)
database.register_opts(CONF)
notify.register_opts(CONF)
paths.register_opts(CONF)
