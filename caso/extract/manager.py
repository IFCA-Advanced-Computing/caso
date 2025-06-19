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

"""Module containing the manager for all extractors configured in cASO."""

import datetime
import json
import os.path
import sys
import warnings

import dateutil.parser
from dateutil import tz
from oslo_config import cfg
from oslo_log import log
import six

from caso import keystone_client
from caso import loading

from keystoneauth1.exceptions.catalog import EmptyCatalog
from keystoneauth1.exceptions.http import Forbidden

cli_opts = [
    cfg.ListOpt(
        "projects",
        default=[],
        help="List of projects to extract accounting records from. You can "
        "use this option, or add 'caso' tag to the project in Keystone. "
        "Please refer to the documentation for more details.",
    ),
    cfg.StrOpt(
        "caso_tag",
        default="caso",
        help="Tag used to mark a project in Keystone to be extracted by cASO",
    ),
    cfg.StrOpt(
        "vo_property",
        default="VO",
        help="Property key used to get the VO name from the project properties. ",
    ),
    cfg.StrOpt(
        "mapping_file",
        default="/etc/caso/voms.json",
        deprecated_group="extractor",
        deprecated_for_removal=True,
        deprecated_reason="This option is marked for removal in the next release. "
        "Please see the release notes, and migrate your current configuration "
        "to use the new project mapping as soon as possible. If you already migrated "
        "your configuration, please remove the JSON file to get rid of this message.",
        help="File containing the VO <-> project mapping as used in Keystone-VOMS.",
    ),
    cfg.StrOpt(
        "extract-to",
        help="Extract record changes until this date. "
        "If it is not set, we use now. If a server has "
        "ended after this date, it will be included, but "
        "the consuption reported will end on this date. "
        "If no time zone is specified, UTC will be used.",
    ),
    cfg.StrOpt(
        "extract-from",
        help="Extract records that have changed after this date. This "
        "means that if a record has started before this date, and "
        "it has changed after this date (i.e. it is still running "
        "or it has ended) it will be reported. \n"
        "If it is not set, extract records from last run. "
        "If it is set to None and last run file is not present, "
        "it will extract records from the beginning of time. "
        "If no time zone is specified, UTC will be used.",
    ),
    cfg.ListOpt(
        "extractor",
        default=["nova", "cinder", "neutron"],
        help="Which extractor to use for getting the data. "
        "If you do not specify anything, nova will be "
        "used. Available choices are {}".format(
            sorted(loading.get_available_extractor_names())
        ),
    ),
]

CONF = cfg.CONF

CONF.register_cli_opts(cli_opts)

LOG = log.getLogger(__name__)


class Manager(object):
    """A manager for the configured extractors.

    The manager is intended to load all configured extractors, get the records from the
    last time the extractor was called (or from a given date).
    """

    def __init__(self):
        """Initialize a extractor manager, loading all configured extractors."""
        extractors = [
            (i, loading.get_available_extractors()[i]) for i in CONF.extractor
        ]
        self.extractors = extractors
        self.last_run_base = os.path.join(CONF.spooldir, "lastrun")

        self._voms_map = {}
        self.keystone = self._get_keystone_client()

    @property
    def projects(self):
        """Get list of configured projects."""
        projects = CONF.projects
        aux = []
        try:
            aux = [i.id for i in self.keystone.projects.list(tags=CONF.caso_tag)]
        except Forbidden as e:
            LOG.warning(f"Unable to get projects from Keystone, ignoring - {e}")
        return set(projects + aux)

    def _get_keystone_client(self, project=None, system_scope="all"):
        """Get a Keystone Client to get the projects that we will use."""
        client = keystone_client.get_client(
            CONF, project=project, system_scope=system_scope
        )
        return client

    def get_lastrun(self, project):
        """Get lastrun file for a given project."""
        lfile = f"{self.last_run_base}.{project}"
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
        """Write a lastrun file for a given project."""
        if CONF.dry_run:
            return
        lfile = f"{self.last_run_base}.{project}"
        with open(lfile, "w") as fd:
            fd.write(str(datetime.datetime.now(tz.tzutc())))

    @property
    def voms_map(self):
        """Get the VO map."""
        if self._voms_map:
            return self._voms_map

        if not os.path.exists(CONF.mapping_file):
            return {}

        try:
            mapping = json.loads(open(CONF.mapping_file).read())
        except ValueError:
            # FIXME(aloga): raise a proper exception here
            raise
        else:
            self._voms_map = {}
            for vo, vomap in six.iteritems(mapping):
                tenant = vomap.get("tenant", None)
                tenants = vomap.get("tenants", [])
                if tenant is not None:
                    warnings.warn(
                        "Using deprecated 'tenant' mapping, please "
                        "use 'projects' instead",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                if tenants:
                    warnings.warn(
                        "Using deprecated 'tenants' mapping, please "
                        "use 'projects' instead",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                tenants.append(tenant)
                projects = vomap.get("projects", tenants)
                if not projects:
                    LOG.warning(f"No project mapping found for VO {vo}")
                for project in projects:
                    self._voms_map[project] = vo
            return self._voms_map

    def get_project_vo(self, project_id):
        """Get the VO where the project should be mapped."""
        try:
            project = self.keystone.projects.get(project_id)
        except (EmptyCatalog, Forbidden):
            # we may need scoping here, retrying
            LOG.warning(
                f"Scoping the keystone client to the current project {project_id}"
            )
            self.keystone = self._get_keystone_client(project_id)
            project = self.keystone.projects.get(project_id)

        project.get()
        vo = project.to_dict().get(CONF.vo_property, None)
        if vo is None:
            LOG.warning(
                f"No mapping could be found for project '{project_id}' in the "
                "Keystone project metadata, please check cASO documentation."
            )
            vo = self.voms_map.get(project_id, None)
            if vo is None:
                LOG.warning(
                    "No mapping could be found for project "
                    f"'{project_id}', please check mapping file!"
                )
            else:
                LOG.warning(
                    "Using deprecated mapping file, please check cASO documentation "
                    "and migrate to Keystone properties as soon as possible."
                )
        else:
            LOG.debug(
                f"Found VO mapping ({vo}) in Keystone project '{project_id}' "
                "metadata."
            )
        return vo

    def get_records(self):
        """Get records from given date.

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
            LOG.warning(
                "The extract-to parameter is in the future, after "
                "current date and time, cASO will limit the record "
                "generation to the current date and time. "
                f"(extract-to: {extract_to}"
            )
            extract_to = now

        all_records = []
        for project in self.projects:
            LOG.info(f"Extracting records for project '{project}'")

            vo = self.get_project_vo(project)

            extract_from = CONF.extract_from or self.get_lastrun(project)
            if isinstance(extract_from, six.string_types):
                extract_from = dateutil.parser.parse(extract_from)
            if extract_from.tzinfo is None:
                extract_from = extract_from.replace(tzinfo=tz.tzutc())

            if extract_from >= now:
                LOG.error(
                    "Cannot extract records from the future, please "
                    "check the extract-from parameter or the last run "
                    f"file for the project {project}!"
                    f"(extract-from: {extract_from})"
                )
                sys.exit(1)

            record_count = 0
            for extractor_name, extractor_cls in self.extractors:
                LOG.debug(
                    f"Extractor {extractor_name}: extracting records "
                    f"for project {project} "
                    f"({extract_from} to {extract_to})"
                )
                try:
                    extractor = extractor_cls(project, vo)
                    records = extractor.extract(extract_from, extract_to)
                    current_count = len(records)
                    record_count += current_count
                    all_records.extend(records)

                    LOG.debug(
                        f"Extractor {extractor_name}: extracted "
                        f"{current_count} records for project "
                        f"'{project}' "
                        f"({extract_from} to {extract_to})"
                    )
                except Exception:
                    LOG.exception(
                        f"Extractor {extractor_name}: cannot "
                        f"extract records for '{project}', got "
                        "the following exception: "
                    )
            LOG.info(
                f"Extracted {record_count} records in total for "
                f"project '{project}' "
                f"({extract_from} to {extract_to})"
            )
            self.write_lastrun(project)
        return all_records
