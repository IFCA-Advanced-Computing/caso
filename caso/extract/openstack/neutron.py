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

"""Module containing the  OpenStack Network (Neutron) record extractor."""

import collections
import ipaddress
import uuid

from oslo_config import cfg
from oslo_log import log

from caso.extract.openstack import base
from caso import record
from datetime import datetime

CONF = cfg.CONF

CONF.import_opt("region_name", "caso.extract.openstack")
CONF.import_opt("site_name", "caso.extract.base")

LOG = log.getLogger(__name__)


class NeutronExtractor(base.BaseOpenStackExtractor):
    """An OpenStack Network (Neutron) record extractor for cASO."""

    def __init__(self, project, vo):
        """Get a Neutron record extractor for a given project."""
        super(NeutronExtractor, self).__init__(project, vo)

        self.neutron = self._get_neutron_client()

    def _build_ip_record(self, user_id, ip_count, version):
        user = self.users[user_id]

        measure_time = self._get_measure_time()

        r = record.IPRecord(
            uuid=uuid.uuid4().hex,
            measure_time=measure_time,
            site_name=CONF.site_name,
            user_id=user_id,
            group_id=self.project_id,
            user_dn=user,
            fqan=self.vo,
            ip_version=version,
            public_ip_count=ip_count,
            compute_service=CONF.service_name,
        )

        return r

    def _get_floating_ips(self):
        ips = self.neutron.list_floatingips(project_id=self.project_id)
        return ips

    def extract(self, extract_from, extract_to):
        """Extract records for a project from given date querying neutron.

        This method will get information from neutron.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of records.
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        extract_from = extract_from.replace(tzinfo=None)
        extract_to = extract_to.replace(tzinfo=None)

        floating_ips = self._get_floating_ips()

        # Neutron does not expose the user owning a floating IP, so we can only
        # aggregate the counts per IP version for the whole project.
        ip_counts = collections.Counter()
        for floating_ip in floating_ips["floatingips"]:
            ip_start = datetime.strptime(
                floating_ip["created_at"], "%Y-%m-%dT%H:%M:%SZ"
            )
            if ip_start > extract_to:
                continue
            ip = floating_ip["floating_ip_address"]
            ip_counts[ipaddress.ip_address(ip).version] += 1

        user_id = None
        self.ip_records = {
            ip_version: self._build_ip_record(user_id, count, ip_version)
            for ip_version, count in sorted(ip_counts.items())
        }

        return list(self.ip_records.values())
