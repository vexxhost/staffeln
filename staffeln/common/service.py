# Copyright 2013 - Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging

import staffeln.conf
from staffeln import objects
from staffeln.common import config

CONF = staffeln.conf.CONF


def prepare_service(argv=None):
    if argv is None:
        argv = []
    logging.register_options(CONF)
    config.parse_args(argv)
    config.set_config_defaults()
    objects.register_all()
    logging.setup(CONF, "staffeln")
