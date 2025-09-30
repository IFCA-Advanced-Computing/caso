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

from caso.extract import base
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
        default="sum(rate(node_energy_joules_total[5m])) * 300 / 3600000",
        help="Prometheus query to retrieve energy consumption in kWh. "
        "The query should return energy consumption metrics.",
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


class PrometheusExtractor(base.BaseProjectExtractor):
    """A Prometheus extractor for energy consumption metrics in cASO."""

    def __init__(self, project, vo):
        """Initialize a Prometheus extractor for a given project."""
        super(PrometheusExtractor, self).__init__(project)
        self.vo = vo
        self.project_id = project

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

    def _build_energy_record(self, energy_value, measurement_time):
        """Build an energy consumption record.

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
        in the specified time range.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of energy records
        """
        records = []

        # Query Prometheus at the extract_to timestamp
        query = CONF.prometheus.prometheus_query
        LOG.debug(
            f"Querying Prometheus for project {self.project} " f"with query: {query}"
        )

        results = self._query_prometheus(query, extract_to)

        if results is None:
            LOG.warning(
                f"No results returned from Prometheus for project {self.project}"
            )
            return records

        # Process results and create records
        for result in results:
            value = result.get("value", [])

            if len(value) < 2:
                continue

            # value is [timestamp, value_string]
            energy_value = float(value[1])

            LOG.debug(
                f"Creating energy record: {energy_value} kWh "
                f"for project {self.project}"
            )

            energy_record = self._build_energy_record(energy_value, extract_to)
            records.append(energy_record)

        LOG.info(f"Extracted {len(records)} energy records for project {self.project}")

        return records
