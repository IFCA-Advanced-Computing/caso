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

from caso.extract.prometheus import PrometheusExtractor

CONF = cfg.CONF


class TestPrometheusExtractor:
    """Test the Prometheus extractor."""

    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor._get_nova_client")
    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor.__init__")
    @mock.patch("caso.extract.prometheus.requests.get")
    def test_extract_with_results(self, mock_get, mock_base_init, mock_get_nova):
        """Test extraction with successful Prometheus query."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock the base class __init__ to do nothing
        mock_base_init.return_value = None

        # Mock Nova client and servers
        mock_server1 = mock.Mock()
        mock_server1.id = "vm-uuid-1"
        mock_server1.name = "test-vm-1"

        mock_server2 = mock.Mock()
        mock_server2.id = "vm-uuid-2"
        mock_server2.name = "test-vm-2"

        mock_nova = mock.Mock()
        mock_nova.servers.list.return_value = [mock_server1, mock_server2]
        mock_get_nova.return_value = mock_nova

        # Create extractor and manually set required attributes
        extractor = PrometheusExtractor("test-project", "test-vo")
        extractor.project = "test-project"
        extractor.vo = "test-vo"
        extractor.project_id = "test-project-id"

        # Mock Prometheus response
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"instance": "test"},
                        "value": [1685051946, "125.5"],
                    }
                ]
            },
        }
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify - should create 2 records (one per VM)
        assert len(records) == 2
        assert records[0].energy_consumption == 125.5
        assert records[0].energy_unit == "kWh"
        assert records[0].fqan == "test-vo"

    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor._get_nova_client")
    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor.__init__")
    def test_extract_with_no_vms(self, mock_base_init, mock_get_nova):
        """Test extraction when there are no VMs."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock the base class __init__ to do nothing
        mock_base_init.return_value = None

        # Mock Nova client with no servers
        mock_nova = mock.Mock()
        mock_nova.servers.list.return_value = []
        mock_get_nova.return_value = mock_nova

        # Create extractor and manually set required attributes
        extractor = PrometheusExtractor("test-project", "test-vo")
        extractor.project = "test-project"
        extractor.vo = "test-vo"
        extractor.project_id = "test-project-id"

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify - no VMs, no records
        assert len(records) == 0

    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor._get_nova_client")
    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor.__init__")
    @mock.patch("caso.extract.prometheus.requests.get")
    def test_extract_with_failed_query(self, mock_get, mock_base_init, mock_get_nova):
        """Test extraction when Prometheus query fails."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock the base class __init__ to do nothing
        mock_base_init.return_value = None

        # Mock Nova client and servers
        mock_server = mock.Mock()
        mock_server.id = "vm-uuid-1"
        mock_server.name = "test-vm-1"

        mock_nova = mock.Mock()
        mock_nova.servers.list.return_value = [mock_server]
        mock_get_nova.return_value = mock_nova

        # Create extractor and manually set required attributes
        extractor = PrometheusExtractor("test-project", "test-vo")
        extractor.project = "test-project"
        extractor.vo = "test-vo"
        extractor.project_id = "test-project-id"

        # Mock Prometheus error response
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "status": "error",
            "error": "query failed",
        }
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify - query failed, no records
        assert len(records) == 0

    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor._get_nova_client")
    @mock.patch("caso.extract.openstack.base.BaseOpenStackExtractor.__init__")
    @mock.patch("caso.extract.prometheus.requests.get")
    @mock.patch("caso.extract.prometheus.LOG")
    def test_extract_with_request_exception(
        self, mock_log, mock_get, mock_base_init, mock_get_nova
    ):
        """Test extraction when request to Prometheus fails."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock the base class __init__ to do nothing
        mock_base_init.return_value = None

        # Mock Nova client and servers
        mock_server = mock.Mock()
        mock_server.id = "vm-uuid-1"
        mock_server.name = "test-vm-1"

        mock_nova = mock.Mock()
        mock_nova.servers.list.return_value = [mock_server]
        mock_get_nova.return_value = mock_nova

        # Create extractor and manually set required attributes
        extractor = PrometheusExtractor("test-project", "test-vo")
        extractor.project = "test-project"
        extractor.vo = "test-vo"
        extractor.project_id = "test-project-id"

        # Mock request exception
        mock_get.side_effect = Exception("Connection error")

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify - exception caught, no records
        assert len(records) == 0
        mock_log.error.assert_called()
