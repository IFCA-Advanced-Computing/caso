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

    @mock.patch("caso.extract.prometheus.requests.get")
    def test_extract_with_results(self, mock_get):
        """Test extraction with successful Prometheus query."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

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

        # Create extractor
        extractor = PrometheusExtractor("test-project", "test-vo")

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify
        assert len(records) == 1
        assert records[0].energy_consumption == 125.5
        assert records[0].energy_unit == "kWh"
        assert records[0].fqan == "test-vo"

    @mock.patch("caso.extract.prometheus.requests.get")
    def test_extract_with_no_results(self, mock_get):
        """Test extraction when Prometheus returns no results."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock Prometheus response with no results
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []},
        }
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Create extractor
        extractor = PrometheusExtractor("test-project", "test-vo")

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify
        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.requests.get")
    def test_extract_with_failed_query(self, mock_get):
        """Test extraction when Prometheus query fails."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock Prometheus error response
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "status": "error",
            "error": "query failed",
        }
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Create extractor
        extractor = PrometheusExtractor("test-project", "test-vo")

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify
        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.requests.get")
    @mock.patch("caso.extract.prometheus.LOG")
    def test_extract_with_request_exception(self, mock_log, mock_get):
        """Test extraction when request to Prometheus fails."""
        # Configure CONF
        CONF.set_override("site_name", "TEST-Site")
        CONF.set_override("service_name", "TEST-Service")

        # Mock request exception
        mock_get.side_effect = Exception("Connection error")

        # Create extractor
        extractor = PrometheusExtractor("test-project", "test-vo")

        # Extract records
        extract_from = datetime.datetime(2023, 5, 25, 0, 0, 0)
        extract_to = datetime.datetime(2023, 5, 25, 23, 59, 59)
        records = extractor.extract(extract_from, extract_to)

        # Verify
        assert len(records) == 0
        mock_log.error.assert_called()
