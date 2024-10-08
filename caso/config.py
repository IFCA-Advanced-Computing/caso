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

"""Load and parse configuration options."""

import logging
import warnings

from oslo_config import cfg
from oslo_log import log

import caso

logging.captureWarnings(True)
warnings.simplefilter("default", DeprecationWarning)

log.register_options(cfg.CONF)


def parse_args(argv, default_config_files=None):
    """Parse command line argments with oslo_config CONF object."""
    cfg.CONF(
        argv[1:],
        project="caso",
        version=caso.extract_version(),
        default_config_files=default_config_files,
    )
