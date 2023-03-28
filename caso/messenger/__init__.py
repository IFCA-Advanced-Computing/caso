# -*- coding: utf-8 -*-

# Copyright 2014 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Module containing the base class and manager for the cASO messengers."""

import abc

from oslo_config import cfg
from oslo_log import log
import six

from caso import loading

CONF = cfg.CONF

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseMessenger(object):
    """Base class for all messengers."""

    @abc.abstractmethod
    def push(self, records):
        """Push the records."""


class Manager(object):
    """Manager for all cASO messengers."""

    def __init__(self):
        """Init the manager with all the configured messengers."""
        try:
            self.mgr = loading.get_enabled_messengers(CONF.messengers)
        except Exception as e:
            # Capture exception so that we can continue working
            LOG.error(e)
            raise e

    def push_to_all(self, records):
        """Push records to all the configured messengers."""
        try:
            self.mgr.map_method("push", records)
        except Exception as e:
            # Capture exception so that we can continue working
            LOG.error(e)
