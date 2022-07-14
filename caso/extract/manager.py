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
import os.path
import sys

import dateutil.parser
from dateutil import tz
from oslo_config import cfg
from oslo_log import log
import six

from caso import loading

cli_opts = [
    cfg.ListOpt('projects',
                default=[],
                deprecated_name='tenants',
                help='List of projects to extract accounting records from.'),
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
    cfg.ListOpt('extractor',
                default=['nova'],
                help='Which extractor to use for getting the data. '
                     'If you do not specify anything, nova will be '
                     'used. Available choices are {}'.format(
                         loading.get_available_extractor_names())),
]

CONF = cfg.CONF

CONF.register_cli_opts(cli_opts)
CONF.import_opt("projects", "caso.extract.base")

LOG = log.getLogger(__name__)


class Manager(object):
    def __init__(self):
        extractors = [
            (i, loading.get_available_extractors()[i])
            for i in CONF.extractor
        ]
        self.extractors = extractors
        self.last_run_base = os.path.join(CONF.spooldir, "lastrun")

    def get_lastrun(self, project):
        lfile = f"{self.last_run_base}.{project}"
        if not os.path.exists(lfile):
            LOG.warning("WARNING: Old global lastrun file detected and no "
                        "project specific file found, using it for this run")
            lfile = self.last_run_base

        date = "1970-01-01"

        if os.path.exists(lfile):
            with open(lfile, "r") as fd:
                date = fd.read()
        else:
            LOG.info(f"No lastrun file found, using '{date}'")
        try:
            date = dateutil.parser.parse(date)
        except Exception:
            LOG.error(f"ERROR: Cannot read date from lastrun file '{lfile}'")
            raise
        else:
            LOG.debug(f"Got '{date}' from lastrun file '{lfile}'")
        return date

    def write_lastrun(self, project):
        if CONF.dry_run:
            return
        lfile = f"{self.last_run_base}.{project}"
        with open(lfile, "w") as fd:
            fd.write(str(datetime.datetime.now(tz.tzutc())))

    def get_records(self):
        """Get records from given date

        If CONF.extract_from is present, it will be used instead of the
        lastrun parameter. If CONF.extract_to is present, it will be used
        instead of the extract_to parameter
        """
        now = datetime.datetime.now(tz.tzutc())
        extract_to = CONF.extract_to or now

        if isinstance(extract_to, six.string_types):
            extract_to = dateutil.parser.parse(extract_to)
        if extract_to.tzinfo is None:
            extract_to = extract_to.replace(tzinfo=tz.tzutc())

        if extract_to > now:
            LOG.warning("The extract-to parameter is in the future, after "
                        "current date and time, cASO will limit the record "
                        "generation to the current date and time. "
                        f"(extract-to: {extract_to}")
            extract_to = now

        all_records = []
        for project in CONF.projects:
            LOG.info(f"Extracting records for project '{project}'")

            extract_from = CONF.extract_from or self.get_lastrun(project)
            if isinstance(extract_from, six.string_types):
                extract_from = dateutil.parser.parse(extract_from)
            if extract_from.tzinfo is None:
                extract_from = extract_from.replace(tzinfo=tz.tzutc())

            if extract_from >= now:
                LOG.error("Cannot extract records from the future, please "
                          "check the extract-from parameter or the last run "
                          f"file for the project {project}!"
                          f"(extract-from: {extract_from})")
                sys.exit(1)

            record_count = 0
            for extractor_name, extractor_cls in self.extractors:
                LOG.debug(f"Extractor {extractor_name}: extracting records "
                          f"for project {project} "
                          f"({extract_from} to {extract_to})")
                try:
                    extractor = extractor_cls(project)
                    records = extractor.extract(extract_from, extract_to)
                    current_count = len(records)
                    record_count += current_count
                    all_records.extend(records)

                    LOG.debug(f"Extractor {extractor_name}: extracted "
                              f"{current_count} records for project "
                              f"'{project}' "
                              f"({extract_from} to {extract_to})")
                except Exception:
                    LOG.exception(f"Extractor {extractor_name}: cannot extract "
                                  f"records for '{project}', got "
                                  "the following exception: ")
            LOG.info(f"Extracted {record_count} records in total for "
                     f"project '{project}' "
                     f"({extract_from} to {extract_to})")
            self.write_lastrun(project)
        return all_records
