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

"""Test for Prometheus extractor."""

import datetime
import unittest.mock as mock

import pytest
from oslo_config import cfg

from caso.extract.prometheus import EnergyConsumptionExtractor

CONF = cfg.CONF


@pytest.fixture
def extract_dates():
    """Fixture for extraction date range."""
    return {
        "extract_from": datetime.datetime(2023, 5, 25, 0, 0, 0),
        "extract_to": datetime.datetime(2023, 5, 25, 23, 59, 59),
    }


@pytest.fixture
def mock_server():
    """Fixture for a mock server."""
    server = mock.Mock()
    server.id = "e3c5aeef-37b8-4332-ad9f-9d068f156dc2"
    server.name = "test-vm-1"
    server.status = "ACTIVE"
    server.created = "2023-05-25T12:00:00Z"
    server.flavor = {"id": "flavor-1"}
    return server


@pytest.fixture
def mock_flavors():
    """Fixture for mock flavors."""
    return {"flavor-1": {"vcpus": 2, "id": "flavor-1"}}


@pytest.fixture
def configured_extractor(mock_flavors):
    """Fixture for a configured EnergyConsumptionExtractor."""
    # Configure CONF
    CONF.set_override("site_name", "TEST-Site")
    CONF.set_override("service_name", "TEST-Service")
    CONF.set_override("prometheus_endpoint", "http://localhost:9090", group="prometheus")
    CONF.set_override("prometheus_metric_name", "prometheus_value", group="prometheus")
    CONF.set_override("vm_uuid_label_name", "uuid", group="prometheus")
    CONF.set_override(
        "labels",
        ["type_instance:scaph_process_power_microwatts"],
        group="prometheus",
    )
    CONF.set_override("prometheus_step_seconds", 30, group="prometheus")
    CONF.set_override("prometheus_query_range", "1h", group="prometheus")
    CONF.set_override("prometheus_verify_ssl", True, group="prometheus")

    with mock.patch(
        "caso.extract.openstack.base.BaseOpenStackExtractor.__init__",
        return_value=None,
    ), mock.patch(
        "caso.extract.prometheus.EnergyConsumptionExtractor._get_flavors",
        return_value=mock_flavors,
    ), mock.patch(
        "caso.extract.openstack.base.BaseOpenStackExtractor._get_nova_client"
    ):
        extractor = EnergyConsumptionExtractor("test-project", "test-vo")
        extractor.project = "test-project"
        extractor.vo = "test-vo"
        extractor.project_id = "test-project-id"
        extractor.cloud_type = "openstack"
        yield extractor


@pytest.fixture
def mock_prometheus_result_success():
    """Fixture for a successful Prometheus API result."""
    return [{"metric": {"uuid": "test-uuid"}, "value": [1685051946, "5.0"]}]


@pytest.fixture
def mock_prometheus_result_empty():
    """Fixture for an empty Prometheus API result."""
    return []


class TestEnergyConsumptionExtractor:
    """Test the energy consumption extractor."""

    @mock.patch("caso.extract.prometheus.prometheus_api_client.PrometheusConnect")
    def test_extract_with_results(
        self,
        mock_prom_connect,
        configured_extractor,
        mock_server,
        extract_dates,
        mock_prometheus_result_success,
    ):
        """Test extraction with successful Prometheus query."""
        # Create a second server
        mock_server2 = mock.Mock()
        mock_server2.id = "f4d6bedf-48c9-5f2f-b043-ebb4f9e65d73"
        mock_server2.name = "test-vm-2"
        mock_server2.status = "ACTIVE"
        mock_server2.created = "2023-05-25T12:00:00Z"
        mock_server2.flavor = {"id": "flavor-1"}

        # Mock Nova client with servers
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [
            mock_server,
            mock_server2,
        ]

        # Mock Prometheus client
        mock_prom = mock.Mock()
        mock_prom.custom_query.return_value = mock_prometheus_result_success
        mock_prom_connect.return_value = mock_prom

        # Extract records
        records = configured_extractor.extract(**extract_dates)

        # Verify - should create 2 records (one per VM)
        assert len(records) == 2
        assert records[0].energy_wh == 5.0
        assert records[0].owner == "test-vo"
        assert records[0].status == "active"

    def test_extract_with_no_vms(self, configured_extractor, extract_dates):
        """Test extraction when there are no VMs."""
        # Mock Nova client with no servers
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = []

        # Extract records
        records = configured_extractor.extract(**extract_dates)

        # Verify - no VMs, no records
        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.prometheus_api_client.PrometheusConnect")
    def test_extract_with_no_energy_data(
        self,
        mock_prom_connect,
        configured_extractor,
        mock_server,
        extract_dates,
        mock_prometheus_result_empty,
    ):
        """Test extraction when Prometheus returns no energy data."""
        # Mock Nova client with servers
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [mock_server]

        # Mock Prometheus client with empty result
        mock_prom = mock.Mock()
        mock_prom.custom_query.return_value = mock_prometheus_result_empty
        mock_prom_connect.return_value = mock_prom

        # Extract records
        records = configured_extractor.extract(**extract_dates)

        # Verify - no energy data, no records
        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.LOG")
    @mock.patch("caso.extract.prometheus.prometheus_api_client.PrometheusConnect")
    def test_extract_with_prometheus_exception(
        self,
        mock_prom_connect,
        mock_log,
        configured_extractor,
        mock_server,
        extract_dates,
    ):
        """Test extraction when Prometheus query raises an exception."""
        # Mock Nova client with servers
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [mock_server]

        # Mock Prometheus client to raise exception
        mock_prom = mock.Mock()
        mock_prom.custom_query.side_effect = Exception("Connection error")
        mock_prom_connect.return_value = mock_prom

        # Extract records
        records = configured_extractor.extract(**extract_dates)

        # Verify - exception caught, no records
        assert len(records) == 0
        mock_log.error.assert_called()
