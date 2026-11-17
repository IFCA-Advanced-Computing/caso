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

import functools
import uuid
from datetime import timedelta, timezone

import requests
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

    def _get_servers(self, extract_from):
        """Get all the servers that may have run during the extraction period.

        This includes the servers that currently exist, and the servers that
        changed (e.g. were deleted) after the start of the period.
        """
        servers = {}
        for search_opts in (None, {"changes-since": extract_from}):
            kwargs = {"search_opts": search_opts} if search_opts else {}
            for server in self._list_paginated(
                self.nova.servers.list, "created", **kwargs
            ):
                servers[server.id] = server
        return sorted(servers.values(), key=lambda s: s.created)

    @functools.cached_property
    def _prometheus(self):
        """Prometheus client, shared for all the queries of the extractor."""
        return self._get_prometheus_client()

    def _get_prometheus_client(self):
        """Create and return an HTTP session based on configuration."""
        session = requests.Session()
        session.verify = CONF.prometheus.prometheus_verify_ssl
        return session

    def _query_range(self, query, start, end, step):
        """Run a range query against the Prometheus HTTP API.

        :param start: naive datetime in UTC.
        :param end: naive datetime in UTC.
        :returns: the list of series (the "result" of the query).
        """
        response = self._prometheus.get(
            f"{CONF.prometheus.prometheus_endpoint.rstrip('/')}/api/v1/query_range",
            params={
                "query": query,
                "start": round(start.replace(tzinfo=timezone.utc).timestamp()),
                "end": round(end.replace(tzinfo=timezone.utc).timestamp()),
                "step": step,
            },
        )
        response.raise_for_status()
        return response.json()["data"]["result"]

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
                result = self._query_range(
                    query,
                    chunk_start,
                    chunk_end,
                    CONF.prometheus.prometheus_step_seconds,
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

    def _get_server_period(self, server, extract_from, extract_to):
        """Get the period of the extraction in which a server was running.

        :returns: a (start, end, finished) tuple, or None if the server did not
                  run during the extraction period.
        """
        created_at = self._get_server_start(server)
        ended_at = self._get_server_end(server)

        if created_at >= extract_to or (ended_at and ended_at <= extract_from):
            return None

        start = max(created_at, extract_from)
        finished = ended_at is not None and ended_at <= extract_to
        end = ended_at if finished else extract_to
        return start, end, finished

    def _build_energy_record(self, server, energy_value, start, end, finished):
        """Build an EnergyRecord for a VM."""
        vm_uuid = str(server.id)
        vm_status = server.status.lower()

        wall_clock_time_s = int((end - start).total_seconds())

        cpu_count = 1
        flavor = self.flavors.get(server.flavor.get("id"))
        if flavor:
            cpu_count = flavor.get("vcpus", 1)

        # Assuming CPU duration is wall clock time multiplied by number of vCPUs
        # (this is a simplification)
        cpu_duration_s = wall_clock_time_s * cpu_count

        # Suspended duration (not available from OpenStack API, set to 0 for now)
        suspend_duration_s = 0

        # Apply CPU normalization factor to energy value
        cpu_normalization_factor = CONF.prometheus.cpu_normalization_factor
        energy_wh = energy_value * cpu_normalization_factor

        # Work is defined as CPU time (in seconds) per Wh of energy consumed,
        # which gives an indication of how much CPU time
        # was achieved for the energy consumed.
        work = cpu_duration_s / energy_wh if energy_wh > 0 else 0.0

        # Efficiency is defined as CPU time per second of wall clock time,
        # normalized by the number of vCPUs (always 1 in this simplified model)
        efficiency = 1.0 if wall_clock_time_s > 0 else 0.0

        return record.EnergyRecord(
            exec_unit_id=uuid.UUID(vm_uuid),
            start_exec_time=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_exec_time=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            energy_wh=energy_wh,
            work=work,
            efficiency=efficiency,
            wall_clock_time_s=wall_clock_time_s,
            cpu_duration_s=cpu_duration_s,
            suspend_duration_s=suspend_duration_s,
            cpu_normalization_factor=cpu_normalization_factor,
            exec_unit_finished=int(finished),
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
        servers = self._get_servers(extract_from)
        LOG.info(
            f"Found {len(servers)} VMs for project {self.project}, querying Prometheus"
        )

        for server in servers:
            vm_uuid = str(server.id)
            vm_name = server.name

            period = self._get_server_period(server, extract_from, extract_to)
            if period is None:
                LOG.debug(f"VM {vm_name} ({vm_uuid}) did not run in period, skipping")
                continue
            start, end, finished = period

            LOG.debug(f"Querying energy consumption for VM {vm_name} ({vm_uuid})")
            energy_value = self._energy_consumed_wh(vm_uuid, start, end)
            if energy_value <= 0:
                LOG.debug(f"No energy data for VM {vm_name} ({vm_uuid}), skipping")
                continue

            LOG.debug(
                f"Creating energy record: {energy_value:.4f} Wh "
                f"for VM {vm_name} ({vm_uuid})"
            )
            records.append(
                self._build_energy_record(server, energy_value, start, end, finished)
            )

        LOG.info(f"Extracted {len(records)} energy records for project {self.project}")
        return records
