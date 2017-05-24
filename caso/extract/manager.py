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
import datetime

import dateutil.parser
from dateutil import tz
from oslo_config import cfg
from oslo_log import log
from oslo_utils import importutils
import six

SUPPORTED_EXTRACTORS = {
    'nova': 'caso.extract.nova.OpenStackExtractor',
    'ceilometer': 'caso.extract.ceilometer.CeilometerExtractor',
}

opts = [
    cfg.StrOpt('site_name',
               help='Site name as in GOCDB.'),
    cfg.StrOpt('service_name',
               default='$site_name',
               help='Service name within the site'),
    cfg.ListOpt('projects',
                default=[],
                deprecated_name='tenants',
                help='List of projects to extract accounting records from.'),
    cfg.StrOpt('mapping_file',
               default='/etc/caso/voms.json',
               deprecated_group="extractor",
               help='File containing the VO <-> project mapping as used '
               'in Keystone-VOMS.'),
    cfg.StrOpt('benchmark_name_key',
               default='accounting:benchmark_type',
               help='Metadata key used to retrieve the benchmark type '
                    'from the flavor properties.'),
    cfg.StrOpt('benchmark_value_key',
               default='accounting:benchmark_value',
               help='Metadata key used to retrieve the benchmark value '
                    'from the flavor properties.'),

]

cli_opts = [
    cfg.StrOpt('extract-to',
               deprecated_name='extract_to',
               help='Extract record changes until this date. '
                    'If it is not set, we use now. If a server has '
                    'ended after this date, it will be included, but '
                    'the consuption reported will end on this date. '
                    'If no time zone is specified, UTC will be used.'),
    cfg.StrOpt('extract-from',
               deprecated_name='extract_from',
               help='Extract records that have changed after this date. This '
                    'means that if a record has started before this date, and '
                    'it has changed after this date (i.e. it is still running '
                    'or it has ended) it will be reported. \n'
                    'If it is not set, extract records from last run. '
                    'If it is set to None and last run file is not present, '
                    'it will extract records from the beginning of time. '
                    'If no time zone is specified, UTC will be used.'),
    cfg.StrOpt('extractor',
               choices=SUPPORTED_EXTRACTORS.keys(),
               default='nova',
               help='Which extractor to use for getting the data. '
                    'If you do not specify anything, nova will be '
                    'used.'),
]

CONF = cfg.CONF

CONF.register_opts(opts)
CONF.register_cli_opts(cli_opts)

LOG = log.getLogger(__name__)


class Manager(object):
    def __init__(self):
        extractor_class = importutils.import_class(
            SUPPORTED_EXTRACTORS[CONF.extractor])
        self.extractor = extractor_class()
        self.records = None

    def _extract(self, extract_from, extract_to):
        self.records = {}
        for project in CONF.projects:
            LOG.info("Extracting records for project '%s'" % project)
            try:
                records = self.extractor.extract_for_project(project,
                                                             extract_from,
                                                             extract_to)
            except Exception:
                records = []
                LOG.exception("Cannot extract records for '%s'" % project)
            else:
                LOG.info("Extracted %d records for project '%s' from "
                         "%s to %s" % (len(records), project, extract_from,
                                       extract_to))
            self.records.update(records)

    def get_records(self, lastrun="1970-01-01"):
        """Get records from given date

        :param lastrun: date to get records from (optional).

        If CONF.extract_from is present, it will be used instead of the
        lastrun parameter. If CONF.extract_to is present, it will be used
        instead of the extract_to parameter
        """
        extract_from = CONF.extract_from or lastrun
        extract_to = CONF.extract_to or datetime.datetime.utcnow()

        if isinstance(extract_from, six.string_types):
            extract_from = dateutil.parser.parse(extract_from)
        if isinstance(extract_to, six.string_types):
            extract_to = dateutil.parser.parse(extract_to)

        if extract_from.tzinfo is None:
            extract_from.replace(tzinfo=tz.tzutc())
        if extract_to.tzinfo is None:
            extract_to.replace(tzinfo=tz.tzutc())

        if self.records is None:
            self._extract(extract_from, extract_to)
        return self.records
