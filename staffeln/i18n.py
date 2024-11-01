"""oslo.i18n integration module.
See http://docs.openstack.org/developer/oslo.i18n/usage.html .
"""

from __future__ import annotations

import oslo_i18n

DOMAIN = "staffeln"

_translators = oslo_i18n.TranslatorFactory(domain=DOMAIN)

# The primary translation function using the well-known name "_"
_ = _translators.primary


def translate(value, user_locale):
    return oslo_i18n.translate(value, user_locale)


def get_available_languages():
    return oslo_i18n.get_available_languages(DOMAIN)
