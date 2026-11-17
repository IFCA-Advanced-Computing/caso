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

"""Module containing the base class and configuration for all cASO extractors."""

import abc

from oslo_config import cfg
from oslo_log import log

opts = [
    cfg.StrOpt("site_name", help="Site name as in GOCDB."),
    cfg.StrOpt(
        "service_name", default="$site_name", help="Service name within the site"
    ),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = log.getLogger(__name__)


class BaseProjectExtractor(abc.ABC):
    """Abstract base class for all extractors in cASO."""

    def __init__(self, project):
        """Initialize extractor, loading the VO map."""
        self.project = project

    @abc.abstractmethod
    def extract(self, extract_from, extract_to):
        """Extract records for a project from given date.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of accounting records

        This method should be overriden in a subclass.
        """
