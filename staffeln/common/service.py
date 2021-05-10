from oslo_log import log as logging

from staffeln.common import config
from staffeln import objects
import staffeln.conf

CONF = staffeln.conf.CONF


def prepare_service(argv=None):
    if argv is None:
        argv = []
    logging.register_options(CONF)
    config.parse_args(argv)
    config.set_config_defaults()
    objects.register_all()
    logging.setup(CONF, 'staffeln')
