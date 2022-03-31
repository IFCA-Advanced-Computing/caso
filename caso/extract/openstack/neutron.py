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

import collections
import ipaddress

import neutronclient.v2_0.client
from oslo_config import cfg
from oslo_log import log

from caso.extract import openstack
from caso import record
from datetime import datetime

CONF = cfg.CONF

CONF.import_opt("region_name", "caso.extract.openstack")
CONF.import_opt("site_name", "caso.extract.base")
CONF.import_group("benchmark", "caso.extract.base")
CONF.import_group("accelerator", "caso.extract.base")

LOG = log.getLogger(__name__)


class NeutronExtractor(openstack.BaseOpenStackExtractor):
    def __init__(self, project):
        super(NeutronExtractor, self).__init__(project)

        self.neutron = self._get_neutron_client()

    def _get_neutron_client(self):
        session = self._get_keystone_session()
        return neutronclient.v2_0.client.Client(session=session)

    def build_ip_record(self, user_id, ip_count, version):
        user = self.users[user_id]

        measure_time = self._get_measure_time()

        r = record.IPRecord(
            measure_time,
            CONF.site_name,
            user_id,
            self.project_id,
            user,
            self.vo,
            version,
            ip_count,
            compute_service=CONF.service_name
        )

        return r

    def _get_floating_ips(self):
        ips = self.neutron.list_floatingips(self.project_id)
        return ips

    def _process_ip_counts(self, ip_counts_v4, ip_counts_v6,
                           extract_from, extract_to):

        floating_ips = self._get_floating_ips()

        user = None
        for floating_ip in floating_ips["floatingips"]:
            ip = floating_ip["floating_ip_address"]
            ip_version = ipaddress.ip_address(ip).version
            ip_start = datetime.strptime(floating_ip["created_at"],
                                         '%Y-%m-%dT%H:%M:%SZ')
            if ip_start > extract_to:
                continue
            else:
                if ip_version == 4:
                    self.ip_counts_v4[user] += 1
                elif ip_version == 6:
                    self.ip_counts_v6[user] += 1

        for (ip_version, ip_counts) in [(4, self.ip_counts_v4),
                                        (6, self.ip_counts_v6)]:
            for user_id, count in ip_counts.items():
                if count == 0:
                    continue

                self.ip_records[user_id] = self.build_ip_record(user_id,
                                                                count,
                                                                ip_version)

    def extract(self, extract_from, extract_to):
        """Extract records for a project from given date querying nova.

        This method will get information from nova.

        :param project: Project to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A dictionary of {"server_id": caso.record.Record"} # FIXME
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        extract_from = extract_from.replace(tzinfo=None)

        # Auxiliary variables to count ips
        self.ip_counts_v4 = collections.defaultdict(lambda: 0)
        self.ip_counts_v6 = collections.defaultdict(lambda: 0)

        self.ip_records = {}

        # Now we have finished processing server and usages (i.e. we have all
        # the server records), but we do not have any IP record
        # So, lets build IP records for each of the users.
        self._process_ip_counts(self.ip_counts_v4, self.ip_counts_v6,
                                extract_from, extract_to)

        return {"ip": self.ip_records}
