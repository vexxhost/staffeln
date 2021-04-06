"""Starter script for Staffeln API service"""
import os
import sys

from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from staffeln.api import app as api_app
from staffeln.common import service
import staffeln.conf
from staffeln.i18n import _
from staffeln import version

CONF = staffeln.conf.CONF

LOG = logging.getLogger(__name__)


def _get_ssl_configs(use_ssl):
    if use_ssl:
        cert_file = CONF.api.ssl_cert_file
        key_file = CONF.api.ssl_key_file

        if cert_file and not os.path.exists(cert_file):
            raise RuntimeError(
                _("Unable to find cert_file : %s") % cert_file)

        if key_file and not os.path.exists(key_file):
            raise RuntimeError(
                _("Unable to find key_file : %s") % key_file)

        return cert_file, key_file
    else:
        return None


def main():
    service.prepare_service(sys.argv)
    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    # SSL configuration
    use_ssl = CONF.api.enabled_ssl

    # Create the WSGI server and start it
    host, port = CONF.api.host, CONF.api.port

    LOG.info('Starting server in PID %s', os.getpid())
    LOG.debug("Configuration:")
    CONF.log_opt_values(LOG, logging.DEBUG)

    LOG.info('Serving on %(proto)s://%(host)s:%(port)s',
             dict(proto="https" if use_ssl else "http", host=host, port=port))

    api_app.run(host=host, port=port, ssl_context=_get_ssl_configs(use_ssl))
