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

"""Energy Consumption extractor for cASO."""

import operator
import uuid
from datetime import timedelta

import dateutil.parser
import prometheus_api_client
from oslo_config import cfg
from oslo_log import log

from caso import record
from caso.extract.openstack import base

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
        help="List of label filters as key:value pairs to filter the metric.",
    ),
    cfg.IntOpt(
        "prometheus_step_seconds",
        default=30,
        help="Frequency between samples in the time series (in seconds).",
    ),
    cfg.BoolOpt(
        "prometheus_verify_ssl",
        default=True,
        help="Whether to verify SSL when connecting to Prometheus.",
    ),
    cfg.FloatOpt(
        "cpu_normalization_factor",
        default=1.0,
        help="CPU normalization factor to apply to energy measurements.",
    ),
]

CONF.import_opt("site_name", "caso.extract.base")
CONF.register_opts(opts, group="prometheus")

LOG = log.getLogger(__name__)


class EnergyConsumptionExtractor(base.BaseOpenStackExtractor):
    """Extractor for VM energy consumption from Prometheus."""

    def __init__(self, project, vo):
        """Initialize the extractor with OpenStack clients and flavor information."""
        super().__init__(project, vo)
        self.nova = self._get_nova_client()
        self.flavors = self._get_flavors()

    def _get_flavors(self):
        """Get all flavors for the project."""
        flavors = {}
        for flavor in self.nova.flavors.list():
            flavors[flavor.id] = flavor.to_dict()
            flavors[flavor.id]["extra"] = flavor.get_keys()
        return flavors

    def _get_servers(self):
        """Get all servers for the project, paginated."""
        servers = []
        limit = 200
        marker = None

        while True:
            batch = self.nova.servers.list(limit=limit, marker=marker)
            servers.extend(batch)
            if len(batch) < limit:
                break
            marker = batch[-1].id

        # Sort by creation date
        servers = sorted(servers, key=operator.attrgetter("created"))
        return servers

    def _get_prometheus_client(self):
        """Create and return a Prometheus client based on configuration."""
        return prometheus_api_client.PrometheusConnect(
            url=CONF.prometheus.prometheus_endpoint,
            disable_ssl=not CONF.prometheus.prometheus_verify_ssl,
        )

    def _build_label_selector(self, vm_uuid):
        labels = {}
        for label_filter in CONF.prometheus.labels:
            if ":" in label_filter:
                key, value = label_filter.split(":", 1)
                labels[key.strip()] = value.strip()
            else:
                LOG.warning(
                    f"Invalid label filter '{label_filter}', expected 'key:value'."
                )
        labels[CONF.prometheus.vm_uuid_label_name] = vm_uuid
        return ",".join(f'{k}="{v}"' for k, v in labels.items())

    def _split_time_chunks(self, start, end, step_seconds, max_points=11_000):
        """Yield non-overlapping (chunk_start, chunk_end) tuples."""
        while start < end:
            remaining_steps = int((end - start).total_seconds() / step_seconds)
            chunk_steps = min(remaining_steps, max_points)
            chunk_end = start + timedelta(seconds=chunk_steps * step_seconds)
            yield start, min(chunk_end, end)
            start = chunk_end + timedelta(seconds=step_seconds)  # avoid overlapping

    def _energy_consumed_wh(self, vm_uuid, extract_from, extract_to):
        """Compute energy (Wh) from Prometheus in chunks for a VM."""
        prom = self._get_prometheus_client()
        label_selector = self._build_label_selector(vm_uuid)
        factor = CONF.prometheus.prometheus_step_seconds / 3600 / 1_000_000  # µW·s → Wh
        energy_wh = 0.0

        query = f"{CONF.prometheus.prometheus_metric_name}{{{label_selector}}}"

        for chunk_start, chunk_end in self._split_time_chunks(
            extract_from, extract_to, CONF.prometheus.prometheus_step_seconds
        ):
            LOG.debug(
                "Querying Prometheus chunk for VM %s [%s → %s]",
                vm_uuid,
                chunk_start,
                chunk_end,
            )

            try:
                result = prom.custom_query_range(
                    query=query,
                    start_time=chunk_start,
                    end_time=chunk_end,
                    step=CONF.prometheus.prometheus_step_seconds,
                )
            except Exception as e:
                LOG.error(
                    "Error querying Prometheus for chunk [%s → %s]: %s",
                    chunk_start,
                    chunk_end,
                    e,
                )
                continue

            for series in result:
                for _, value in series.get("values", []):
                    energy_wh += float(value) * factor

        LOG.debug(f"VM {vm_uuid} total energy consumed: {energy_wh:.4f} Wh")
        return energy_wh

    def _build_energy_record(self, server, energy_value, extract_from, extract_to):
        """Build an EnergyRecord for a VM."""
        vm_uuid = str(server.id)
        vm_status = server.status.lower()

        created_at = dateutil.parser.parse(server.created)
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)

        # Skip VMs created after extraction end
        if created_at >= extract_to:
            return None

        start_time = max(created_at, extract_from)
        end_time = extract_to

        wall_clock_time_s = int((end_time - start_time).total_seconds())

        cpu_count = 1
        try:
            flavor = self.flavors.get(server.flavor.get("id"))
            if flavor:
                cpu_count = flavor.get("vcpus", 1)
        except Exception:
            pass

        # Assuming CPU duration is wall clock time multiplied by number of vCPUs
        # (this is a simplification)
        cpu_duration_s = wall_clock_time_s * cpu_count

        # Suspended duration (not available from OpenStack API, set to 0 for now)
        suspend_duration_s = 0

        # Exec unit finished if VM is in a terminal state (e.g., deleted),
        # otherwise consider it still running
        exec_unit_finished = 1 if vm_status in ["deleted"] else 0

        # Apply CPU normalization factor to energy value
        cpu_normalization_factor = CONF.prometheus.cpu_normalization_factor
        energy_wh = energy_value * cpu_normalization_factor

        # Work is defined as CPU time (in seconds) per Wh of energy consumed,
        # which gives an indication of how much CPU time
        # was achieved for the energy consumed.
        work = cpu_duration_s / energy_wh if energy_wh > 0 else 0.0

        # Efficiency is defined as CPU time per second of wall clock time,
        # normalized by the number of vCPUs (always 1 in this simplified model)
        efficiency = (
            cpu_duration_s / (wall_clock_time_s * cpu_count)
            if wall_clock_time_s > 0
            else 0.0
        )

        return record.EnergyRecord(
            exec_unit_id=uuid.UUID(vm_uuid),
            start_exec_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_exec_time=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            energy_wh=energy_wh,
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
            compute_service=CONF.service_name,
        )

    def extract(self, extract_from, extract_to):
        """Extract energy consumption records for all VMs in the project.

        :param extract_from: Start of the extraction period (datetime)
        :param extract_to: End of the extraction period (datetime)
        :return: List of EnergyRecord objects with energy consumption data for each VM
        """
        extract_from = extract_from.replace(tzinfo=None)
        extract_to = extract_to.replace(tzinfo=None)

        records = []

        LOG.debug(f"Getting servers for project {self.project}")
        servers = self._get_servers()
        LOG.info(
            f"Found {len(servers)} VMs for project {self.project}, querying Prometheus"
        )

        for server in servers:
            vm_uuid = str(server.id)
            vm_name = server.name
            LOG.debug(f"Querying energy consumption for VM {vm_name} ({vm_uuid})")

            energy_value = self._energy_consumed_wh(vm_uuid, extract_from, extract_to)
            if energy_value <= 0:
                LOG.debug(f"No energy data for VM {vm_name} ({vm_uuid}), skipping")
                continue

            energy_record = self._build_energy_record(
                server, energy_value, extract_from, extract_to
            )
            if energy_record is None:
                continue

            LOG.debug(
                f"Creating energy record: {energy_value:.4f} Wh "
                "for VM {vm_name} ({vm_uuid})"
            )
            records.append(energy_record)

        LOG.info(f"Extracted {len(records)} energy records for project {self.project}")
        return records
