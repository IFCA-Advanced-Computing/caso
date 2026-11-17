# -*- coding: utf-8 -*-

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

"""Tests for the OpenStack nova extractor."""

import datetime
import unittest
from unittest import mock

from caso.extract.openstack import nova


class TestNovaBuildRecord(unittest.TestCase):
    """Test case for Nova _build_record method."""

    @mock.patch("caso.extract.openstack.nova.CONF")
    def test_build_record_with_none_user(self, mock_conf):
        """Test that _build_record handles None user without AttributeError."""
        # Setup mocks
        mock_conf.site_name = "test-site"
        mock_conf.service_name = "test-service"
        mock_conf.benchmark.name_key = "benchmark_name"
        mock_conf.benchmark.value_key = "benchmark_value"

        # Create a mock extractor with None user
        with mock.patch.object(nova.NovaExtractor, "__init__", lambda x, y, z: None):
            extractor = nova.NovaExtractor(None, None)
            extractor.vo = "test-vo"

            # Mock the users dictionary to return None
            extractor.users = {"test-user-id": None}

            # Mock flavors and images
            extractor.flavors = {
                "test-flavor-id": {
                    "ram": 2048,
                    "vcpus": 2,
                    "disk": 20,
                    "OS-FLV-EXT-DATA:ephemeral": 0,
                    "extra": {},
                }
            }
            extractor.images = {}

            # Create a mock server object
            mock_server = mock.MagicMock()
            mock_server.id = "550e8400-e29b-41d4-a716-446655440000"
            mock_server.name = "test-server"
            mock_server.user_id = "test-user-id"
            mock_server.tenant_id = "test-tenant-id"
            mock_server.status = "ACTIVE"
            mock_server.image = {"id": "test-image-id"}
            mock_server.flavor = {"id": "test-flavor-id"}
            mock_server.created = "2023-01-01T00:00:00.000000"

            # Mock methods
            start_dt = datetime.datetime(2023, 1, 1)
            end_dt = datetime.datetime(2023, 1, 2)
            with mock.patch.object(
                extractor, "_get_server_start", return_value=start_dt
            ):
                with mock.patch.object(
                    extractor, "_get_server_end", return_value=end_dt
                ):
                    with mock.patch.object(
                        extractor, "_count_ips_on_server", return_value=0
                    ):
                        # This should not raise AttributeError
                        record = extractor._build_record(mock_server)

                        # Verify the record was created with user_dn=None
                        self.assertIsNone(record.user_dn)


class TestNovaVmStatus(unittest.TestCase):
    """Test case for Nova VM status mapping."""

    def test_vm_status_maps_password_state(self):
        """Test that the OpenStack PASSWORD status maps to started."""
        extractor = object.__new__(nova.NovaExtractor)

        self.assertEqual("started", extractor.vm_status("PASSWORD"))


class TestNovaProcessUsages(unittest.TestCase):
    """Test case for Nova _process_usages_for_period method."""

    @mock.patch("caso.extract.openstack.nova.CONF")
    def test_ended_server_does_not_reuse_wall_duration(self, mock_conf):
        """Servers ended in the period must compute their own durations."""
        mock_conf.site_name = "test-site"
        mock_conf.service_name = "test-service"

        with mock.patch.object(nova.NovaExtractor, "__init__", lambda x, y, z: None):
            extractor = nova.NovaExtractor(None, None)
        extractor.vo = "test-vo"
        extractor.users = {"user": None}
        extractor.flavors = {}
        extractor.images = {}
        extractor.records = {}
        extractor.acc_records = {}

        class FakeServer:
            id = "550e8400-e29b-41d4-a716-446655440000"
            name = "server"
            user_id = "user"
            tenant_id = "tenant"
            status = "DELETED"
            image = None
            flavor = {"id": "missing"}
            created = "2023-05-01T00:00:00Z"
            updated = "2023-05-02T00:00:00Z"
            addresses: dict = {}
            _extra = {
                "OS-SRV-USG:terminated_at": "2023-05-02T00:00:00Z",
                "OS-SRV-USG:launched_at": "2023-05-01T00:00:00Z",
            }

            def __getattr__(self, name):
                return self._extra[name]

        server = FakeServer()

        extractor.nova = mock.MagicMock()
        extractor.nova.servers.get.return_value = server

        usages = [
            {
                "instance_id": server.id,
                "ended_at": "2023-05-02T00:00:00",
                "vcpus": 2,
                "memory_mb": 1024,
                "local_gb": 10,
            }
        ]
        extractor._process_usages_for_period(
            usages,
            datetime.datetime(2023, 4, 1),
            datetime.datetime(2023, 6, 1),
        )

        record = extractor.records[server.id]
        self.assertEqual(86400, record.wall_duration)
        self.assertEqual(2 * 86400, record.cpu_duration)
