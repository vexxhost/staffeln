# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Staffeln base exception handling."""

from typing import Optional, Union  # noqa: H301
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class StaffelnException(Exception):
    """Base Staffeln Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers: dict = {}
    safe = False

    def __init__(self, message: Optional[Union[str, tuple]] = None, **kwargs):
        self.kwargs = kwargs
        self.kwargs['message'] = message

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = str(v)

        if self._should_format():
            try:
                message = self.message % kwargs
            except Exception:
                self._log_exception()
                message = self.message
        elif isinstance(message, Exception):
            message = str(message)

        self.msg = message
        super(StaffelnException, self).__init__(message)
        # Oslo.messaging use the argument 'message' to rebuild exception
        # directly at the rpc client side, therefore we should not use it
        # in our keyword arguments, otherwise, the rebuild process will fail
        # with duplicate keyword exception.
        self.kwargs.pop('message', None)

    def _log_exception(self) -> None:
        # kwargs doesn't match a variable in the message
        # log the issue and the kwargs
        LOG.exception('Exception in string format operation:')
        for name, value in self.kwargs.items():
            LOG.error("%(name)s: %(value)s",
                      {'name': name, 'value': value})

    def _should_format(self) -> bool:
        return self.kwargs['message'] is None or '%(message)' in self.message


class LockCreationFailed(StaffelnException):
    message = "Unable to create lock. Coordination backend not started."
