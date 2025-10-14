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

import prometheus_api_client
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
        "prometheus_metric_name",
        default="prometheus_value",
        help="Name of the Prometheus metric to query for energy consumption.",
    ),
    cfg.StrOpt(
        "vm_uuid_label_name",
        default="uuid",
        help="Name of the label that matches the VM UUID in Prometheus metrics.",
    ),
    cfg.ListOpt(
        "labels",
        default=["type_instance:scaph_process_power_microwatts"],
        help="List of label filters as key:value pairs to filter the Prometheus "
        "metric (e.g., 'type_instance:scaph_process_power_microwatts'). "
        "The VM UUID label will be added automatically based on vm_uuid_label_name.",
    ),
    cfg.IntOpt(
        "prometheus_step_seconds",
        default=30,
        help="Frequency between samples in the time series (in seconds).",
    ),
    cfg.StrOpt(
        "prometheus_query_range",
        default="1h",
        help="Query time range (e.g., '1h', '6h', '24h').",
    ),
    cfg.BoolOpt(
        "prometheus_verify_ssl",
        default=True,
        help="Whether to verify SSL when connecting to Prometheus.",
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

    def _energy_consumed_wh(self, vm_uuid):
        """Calculate the energy consumed (Wh) for a VM from Prometheus.

        This function queries Prometheus for instantaneous power samples
        (in microwatts) and calculates the energy consumed in Watt-hours.

        :param vm_uuid: UUID of the VM to query energy for
        :returns: Energy consumed in Watt-hours (Wh)
        """
        prom_url = CONF.prometheus.prometheus_endpoint
        metric_name = CONF.prometheus.prometheus_metric_name
        step_seconds = CONF.prometheus.prometheus_step_seconds
        query_range = CONF.prometheus.prometheus_query_range
        verify_ssl = CONF.prometheus.prometheus_verify_ssl
        vm_uuid_label_name = CONF.prometheus.vm_uuid_label_name
        label_filters = CONF.prometheus.labels

        prom = prometheus_api_client.PrometheusConnect(
            url=prom_url, disable_ssl=not verify_ssl
        )

        # factor = step_seconds / 3600 converts µW·s to µWh
        factor = step_seconds / 3600

        # Build labels dictionary from the list of "key:value" strings
        labels = {}
        for label_filter in label_filters:
            if ":" in label_filter:
                key, value = label_filter.split(":", 1)
                labels[key.strip()] = value.strip()
            else:
                LOG.warning(
                    f"Invalid label filter format '{label_filter}', "
                    "expected 'key:value'. Skipping."
                )

        # Add the VM UUID label
        labels[vm_uuid_label_name] = vm_uuid

        # Build label string: {key="value", ...}
        label_selector = ",".join(f'{k}="{v}"' for k, v in labels.items())

        # Construct the PromQL query
        query = (
            f"sum_over_time({metric_name}{{{label_selector}}}[{query_range}]) "
            f"* {factor} / 1000000"
        )

        LOG.debug(f"Querying Prometheus for VM {vm_uuid} with query: {query}")

        try:
            # Run query
            result = prom.custom_query(query=query)

            if not result:
                LOG.debug(f"No energy data returned for VM {vm_uuid}")
                return 0.0

            energy_wh = float(result[0]["value"][1])
            LOG.debug(f"VM {vm_uuid} consumed {energy_wh:.4f} Wh")
            return energy_wh

        except (KeyError, IndexError, ValueError) as e:
            LOG.warning(f"Error parsing Prometheus result for VM {vm_uuid}: {e}")
            return 0.0
        except Exception as e:
            LOG.error(f"Error querying Prometheus for VM {vm_uuid}: {e}")
            return 0.0

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
        for server in servers:
            vm_uuid = str(server.id)
            vm_name = server.name

            LOG.debug(f"Querying energy consumption for VM {vm_name} ({vm_uuid})")

            # Get energy consumption using the new method
            energy_value = self._energy_consumed_wh(vm_uuid)

            if energy_value <= 0:
                LOG.debug(
                    f"No energy consumption data for VM {vm_name} ({vm_uuid}), "
                    "skipping record creation"
                )
                continue

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
