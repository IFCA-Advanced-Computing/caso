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

"""Unit tests for the Prometheus energy consumption extractor."""

import datetime
import unittest.mock as mock

import pytest
import requests
from oslo_config import cfg

from caso.extract.prometheus import EnergyConsumptionExtractor

CONF = cfg.CONF


@pytest.fixture
def extract_dates():
    """Return the extraction date range."""
    return {
        "extract_from": datetime.datetime(2023, 5, 25, 0, 0, 0),
        "extract_to": datetime.datetime(2023, 5, 25, 23, 59, 59),
    }


def _response(result):
    """Return a mocked HTTP response for a successful query_range."""
    response = mock.Mock()
    response.json.return_value = {"status": "success", "data": {"result": result}}
    return response


def _server(uuid, name, created="2023-05-25T12:00:00Z", terminated=None):
    """Return a mocked OpenStack server."""
    server = mock.Mock()
    server.id = uuid
    server.name = name
    server.status = "DELETED" if terminated else "ACTIVE"
    server.created = created
    server.updated = terminated or created
    server.flavor = {"id": "flavor-1"}
    setattr(server, "OS-SRV-USG:launched_at", created)
    setattr(server, "OS-SRV-USG:terminated_at", terminated)
    return server


@pytest.fixture
def mock_server():
    """Return a mocked OpenStack server."""
    return _server("e3c5aeef-37b8-4332-ad9f-9d068f156dc2", "test-vm-1")


@pytest.fixture
def mock_flavors():
    """Return mocked flavor definitions."""
    return {"flavor-1": {"vcpus": 2, "id": "flavor-1"}}


@pytest.fixture
def configured_extractor(mock_flavors):
    """Return a configured EnergyConsumptionExtractor instance."""
    CONF.set_override("site_name", "TEST-Site")
    CONF.set_override("service_name", "TEST-Service")
    CONF.set_override(
        "prometheus_endpoint", "http://localhost:9090", group="prometheus"
    )
    CONF.set_override("prometheus_metric_name", "prometheus_value", group="prometheus")
    CONF.set_override("vm_uuid_label_name", "uuid", group="prometheus")
    CONF.set_override(
        "labels",
        ["type_instance:scaph_process_power_microwatts"],
        group="prometheus",
    )
    CONF.set_override("prometheus_step_seconds", 30, group="prometheus")
    CONF.set_override("prometheus_verify_ssl", True, group="prometheus")
    CONF.set_override("cpu_normalization_factor", 1.0, group="prometheus")

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
    """Return a successful Prometheus query_range result."""
    return [
        {
            "metric": {"uuid": "test-uuid"},
            "values": [
                [1685051946, "5.0"],
            ],
        }
    ]


@pytest.fixture
def mock_prometheus_result_empty():
    """Return an empty Prometheus result."""
    return []


class TestEnergyConsumptionExtractor:
    """Tests for the EnergyConsumptionExtractor."""

    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_extract_with_results(
        self,
        mock_session,
        configured_extractor,
        mock_server,
        extract_dates,
        mock_prometheus_result_success,
    ):
        """Test extraction when Prometheus returns energy data."""
        mock_server2 = _server("f4d6bedf-48c9-5f2f-b043-ebb4f9e65d73", "test-vm-2")

        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [
            mock_server,
            mock_server2,
        ]

        mock_prom = mock.Mock()
        mock_prom.get.return_value = _response(mock_prometheus_result_success)
        mock_session.return_value = mock_prom

        records = configured_extractor.extract(**extract_dates)

        assert len(records) == 2
        assert records[0].energy_wh == pytest.approx(4.1666667e-08)
        assert records[0].owner == "test-vo"
        assert records[0].status == "active"

    def test_extract_with_no_vms(self, configured_extractor, extract_dates):
        """Test extraction when no virtual machines exist."""
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = []

        records = configured_extractor.extract(**extract_dates)

        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_extract_with_no_energy_data(
        self,
        mock_session,
        configured_extractor,
        mock_server,
        extract_dates,
        mock_prometheus_result_empty,
    ):
        """Test extraction when Prometheus returns no data."""
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [mock_server]

        mock_prom = mock.Mock()
        mock_prom.get.return_value = _response(mock_prometheus_result_empty)
        mock_session.return_value = mock_prom

        records = configured_extractor.extract(**extract_dates)

        assert len(records) == 0

    @mock.patch("caso.extract.prometheus.LOG")
    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_extract_with_prometheus_exception(
        self,
        mock_session,
        mock_log,
        configured_extractor,
        mock_server,
        extract_dates,
    ):
        """Test extraction when Prometheus raises an exception."""
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [mock_server]

        mock_prom = mock.Mock()
        mock_prom.get.side_effect = Exception("Connection error")
        mock_session.return_value = mock_prom

        records = configured_extractor.extract(**extract_dates)

        assert len(records) == 0
        mock_log.error.assert_called()


class TestServerSelection:
    """Tests for the selection of servers and their accounting period."""

    def test_get_servers_includes_changed_servers(self, configured_extractor):
        """Deleted servers listed with changes-since must also be accounted."""
        current = _server("e3c5aeef-37b8-4332-ad9f-9d068f156dc2", "current")
        deleted = _server(
            "f4d6bedf-48c9-5f2f-b043-ebb4f9e65d73",
            "deleted",
            created="2023-05-20T00:00:00Z",
            terminated="2023-05-25T06:00:00Z",
        )
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.side_effect = [
            [current],
            [current, deleted],
        ]
        extract_from = datetime.datetime(2023, 5, 25)

        servers = configured_extractor._get_servers(extract_from)

        assert [s.name for s in servers] == ["deleted", "current"]
        configured_extractor.nova.servers.list.assert_called_with(
            limit=200, marker=None, search_opts={"changes-since": extract_from}
        )

    def test_server_period(self, configured_extractor, extract_dates):
        """The period must be limited to the server lifetime."""
        running = _server("e3c5aeef-37b8-4332-ad9f-9d068f156dc2", "running")
        ended = _server(
            "f4d6bedf-48c9-5f2f-b043-ebb4f9e65d73",
            "ended",
            created="2023-05-20T00:00:00Z",
            terminated="2023-05-25T06:00:00Z",
        )
        gone = _server(
            "a1d6bedf-48c9-5f2f-b043-ebb4f9e65d73",
            "gone",
            created="2023-05-20T00:00:00Z",
            terminated="2023-05-21T00:00:00Z",
        )

        assert configured_extractor._get_server_period(running, **extract_dates) == (
            datetime.datetime(2023, 5, 25, 12),
            extract_dates["extract_to"],
            False,
        )
        assert configured_extractor._get_server_period(ended, **extract_dates) == (
            extract_dates["extract_from"],
            datetime.datetime(2023, 5, 25, 6),
            True,
        )
        assert configured_extractor._get_server_period(gone, **extract_dates) is None

    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_prometheus_client_is_reused(
        self,
        mock_session,
        configured_extractor,
        extract_dates,
        mock_prometheus_result_success,
    ):
        """A single Prometheus client must be used for all the VMs."""
        configured_extractor.nova = mock.Mock()
        configured_extractor.nova.servers.list.return_value = [
            _server("e3c5aeef-37b8-4332-ad9f-9d068f156dc2", "vm1"),
            _server("f4d6bedf-48c9-5f2f-b043-ebb4f9e65d73", "vm2"),
        ]
        prom = mock_session.return_value
        prom.get.return_value = _response(mock_prometheus_result_success)

        records = configured_extractor.extract(**extract_dates)

        assert len(records) == 2
        mock_session.assert_called_once()


class TestQueryRange:
    """Tests for the Prometheus HTTP API call."""

    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_query_range_request(
        self, mock_session, configured_extractor, mock_prometheus_result_success
    ):
        """The query is sent to the query_range endpoint with UTC timestamps."""
        get = mock_session.return_value.get
        get.return_value = _response(mock_prometheus_result_success)

        result = configured_extractor._query_range(
            'metric{a="b"}',
            datetime.datetime(2023, 5, 25, 0, 0, 0),
            datetime.datetime(2023, 5, 25, 1, 0, 0),
            30,
        )

        assert result == mock_prometheus_result_success
        url = get.call_args.args[0]
        assert url.endswith("/api/v1/query_range")
        assert get.call_args.kwargs["params"] == {
            "query": 'metric{a="b"}',
            "start": 1684972800,
            "end": 1684976400,
            "step": 30,
        }

    @mock.patch("caso.extract.prometheus.requests.Session")
    def test_query_range_http_error(self, mock_session, configured_extractor):
        """HTTP errors are propagated to the caller."""
        response = mock.Mock()
        response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_session.return_value.get.return_value = response

        with pytest.raises(requests.HTTPError):
            configured_extractor._query_range(
                "m", datetime.datetime(2023, 5, 25), datetime.datetime(2023, 5, 26), 30
            )

    def test_session_verifies_ssl_from_config(self, configured_extractor):
        """The SSL verification option is applied to the session."""
        CONF.set_override("prometheus_verify_ssl", False, group="prometheus")
        try:
            session = configured_extractor._get_prometheus_client()
        finally:
            CONF.clear_override("prometheus_verify_ssl", group="prometheus")
        assert session.verify is False
