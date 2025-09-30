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

"""Module containing the Prometheus extractor for energy consumption metrics."""

import uuid

import requests
from oslo_config import cfg
from oslo_log import log

from caso.extract.openstack import base
from caso import record

CONF = cfg.CONF

opts = [
    cfg.StrOpt(
        "prometheus_endpoint",
        default="http://localhost:9090",
        help="Prometheus server endpoint URL.",
    ),
    cfg.StrOpt(
        "prometheus_query",
        default="sum(rate(libvirt_domain_info_energy_consumption_joules_total"
        '{uuid=~"{{uuid}}"}[5m])) * 300 / 3600000',
        help="Prometheus query to retrieve energy consumption in kWh. "
        "The query can use {{uuid}} as a template variable for the VM UUID.",
    ),
    cfg.IntOpt(
        "prometheus_timeout",
        default=30,
        help="Timeout for Prometheus API requests in seconds.",
    ),
]

CONF.import_opt("site_name", "caso.extract.base")
CONF.register_opts(opts, group="prometheus")

LOG = log.getLogger(__name__)


class PrometheusExtractor(base.BaseOpenStackExtractor):
    """A Prometheus extractor for energy consumption metrics in cASO."""

    def __init__(self, project, vo):
        """Initialize a Prometheus extractor for a given project."""
        super(PrometheusExtractor, self).__init__(project, vo)
        self.nova = self._get_nova_client()

    def _query_prometheus(self, query, timestamp=None):
        """Query Prometheus API and return results.

        :param query: PromQL query string
        :param timestamp: Optional timestamp for query (datetime object)
        :returns: Query results
        """
        endpoint = CONF.prometheus.prometheus_endpoint
        url = f"{endpoint}/api/v1/query"

        params = {"query": query}
        if timestamp:
            params["time"] = int(timestamp.timestamp())

        try:
            response = requests.get(
                url, params=params, timeout=CONF.prometheus.prometheus_timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                LOG.error(f"Prometheus query failed: {error_msg}")
                return None

            return data.get("data", {}).get("result", [])
        except requests.exceptions.RequestException as e:
            LOG.error(f"Failed to query Prometheus: {e}")
            return None
        except Exception as e:
            LOG.error(f"Unexpected error querying Prometheus: {e}")
            return None

    def _get_servers(self, extract_from):
        """Get all servers for a given date."""
        servers = []
        limit = 200
        marker = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            aux = self.nova.servers.list(
                search_opts={
                    "changes-since": extract_from,
                    "project_id": self.project_id,
                    "all_tenants": True,
                },
                limit=limit,
                marker=marker,
            )
            servers.extend(aux)

            if len(aux) < limit:
                break
            marker = aux[-1].id

        return servers

    def _build_energy_record(self, vm_uuid, vm_name, energy_value, measurement_time):
        """Build an energy consumption record for a VM.

        :param vm_uuid: VM UUID
        :param vm_name: VM name
        :param energy_value: Energy consumption value in kWh
        :param measurement_time: Time of measurement
        :returns: EnergyRecord object
        """
        r = record.EnergyRecord(
            uuid=uuid.uuid4(),
            measurement_time=measurement_time,
            site_name=CONF.site_name,
            user_id=None,
            group_id=self.project_id,
            user_dn=None,
            fqan=self.vo,
            energy_consumption=energy_value,
            energy_unit="kWh",
            compute_service=CONF.service_name,
        )

        return r

    def extract(self, extract_from, extract_to):
        """Extract energy consumption records from Prometheus.

        This method queries Prometheus for energy consumption metrics
        for each VM in the project.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of energy records
        """
        # Remove timezone as Nova doesn't expect it
        extract_from = extract_from.replace(tzinfo=None)
        extract_to = extract_to.replace(tzinfo=None)

        records = []

        # Get all servers for the project
        LOG.debug(f"Getting servers for project {self.project}")
        servers = self._get_servers(extract_from)

        LOG.info(
            f"Found {len(servers)} VMs for project {self.project}, "
            f"querying Prometheus for energy metrics"
        )

        # Query Prometheus for each server
        query_template = CONF.prometheus.prometheus_query

        for server in servers:
            vm_uuid = str(server.id)
            vm_name = server.name

            # Replace template variables in the query
            query = query_template.replace("{{uuid}}", vm_uuid)

            LOG.debug(
                f"Querying Prometheus for VM {vm_name} ({vm_uuid}) "
                f"with query: {query}"
            )

            results = self._query_prometheus(query, extract_to)

            if results is None:
                LOG.warning(
                    f"No results returned from Prometheus for VM "
                    f"{vm_name} ({vm_uuid})"
                )
                continue

            # Process results and create records
            for result in results:
                value = result.get("value", [])

                if len(value) < 2:
                    continue

                # value is [timestamp, value_string]
                energy_value = float(value[1])

                LOG.debug(
                    f"Creating energy record: {energy_value} kWh "
                    f"for VM {vm_name} ({vm_uuid})"
                )

                energy_record = self._build_energy_record(
                    vm_uuid, vm_name, energy_value, extract_to
                )
                records.append(energy_record)

        LOG.info(f"Extracted {len(records)} energy records for project {self.project}")

        return records
