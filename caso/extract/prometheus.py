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

"""Module containing the Energy Consumption extractor for energy metrics."""

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
        '{uuid=~"{{uuid}}"}[5m])) * 300 / 3600',
        help="Prometheus query to retrieve energy consumption in Wh. "
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


class EnergyConsumptionExtractor(base.BaseOpenStackExtractor):
    """An energy consumption extractor for cASO."""

    def __init__(self, project, vo):
        """Initialize an energy consumption extractor for a given project."""
        super(EnergyConsumptionExtractor, self).__init__(project, vo)
        self.nova = self._get_nova_client()
        self.flavors = self._get_flavors()

    def _get_flavors(self):
        """Get flavors for the project."""
        flavors = {}
        try:
            for flavor in self.nova.flavors.list(is_public=None):
                flavors[flavor.id] = flavor.to_dict()
        except Exception as e:
            LOG.warning(f"Could not get flavors: {e}")
        return flavors

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

    def _build_energy_record(self, server, energy_value, extract_from, extract_to):
        """Build an energy consumption record for a VM.

        :param server: Nova server object
        :param energy_value: Energy consumption value in Wh
        :param extract_from: Start time for extraction period
        :param extract_to: End time for extraction period
        :returns: EnergyRecord object
        """
        vm_uuid = str(server.id)
        vm_status = server.status.lower()

        # Get server creation time
        import dateutil.parser

        created_at = dateutil.parser.parse(server.created)

        # Remove timezone info for comparison (extract_from/to are naive)
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)

        # Calculate start and end times for the period
        start_time = max(created_at, extract_from)
        end_time = extract_to

        # Calculate durations in seconds
        duration = (end_time - start_time).total_seconds()
        wall_clock_time_s = int(duration)

        # For CPU duration, we need to multiply by vCPUs if available
        # Get flavor info to get vCPUs
        cpu_count = 1  # Default
        try:
            flavor = self.flavors.get(server.flavor.get("id"))
            if flavor:
                cpu_count = flavor.get("vcpus", 1)
        except Exception:
            pass

        cpu_duration_s = wall_clock_time_s * cpu_count

        # Calculate suspend duration (0 if running)
        suspend_duration_s = 0
        if vm_status in ["suspended", "paused"]:
            suspend_duration_s = wall_clock_time_s

        # ExecUnitFinished: 0 if running, 1 if stopped/deleted
        exec_unit_finished = 0 if vm_status in ["active", "running"] else 1

        # Calculate work (CPU time in hours)
        work = cpu_duration_s / 3600.0

        # Calculate efficiency (simple model: actual work / max possible work)
        # Efficiency can be calculated as actual energy vs theoretical max
        # For now, use a default value
        efficiency = 0.5  # Placeholder

        # CPU normalization factor (default to 1.0 if not available)
        cpu_normalization_factor = 1.0

        r = record.EnergyRecord(
            exec_unit_id=uuid.UUID(vm_uuid),
            start_exec_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_exec_time=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            energy_wh=energy_value,
            work=work,
            efficiency=efficiency,
            wall_clock_time_s=wall_clock_time_s,
            cpu_duration_s=cpu_duration_s,
            suspend_duration_s=suspend_duration_s,
            cpu_normalization_factor=cpu_normalization_factor,
            exec_unit_finished=exec_unit_finished,
            status=vm_status,
            owner=self.vo,
            site_name=CONF.site_name,
            cloud_type=self.cloud_type,
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
                    f"Creating energy record: {energy_value} Wh "
                    f"for VM {vm_name} ({vm_uuid})"
                )

                energy_record = self._build_energy_record(
                    server, energy_value, extract_from, extract_to
                )
                records.append(energy_record)

        LOG.info(f"Extracted {len(records)} energy records for project {self.project}")

        return records
