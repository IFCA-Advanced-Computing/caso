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


class TestCasoManager(unittest.TestCase):
    """Test case for Nova extractor."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCasoManager, self).setUp()
        self.flags(mapping_file="etc/caso/voms.json.sample")
        self.extractor = nova.NovaExtractor()

    def tearDown(self):
        """Run after each test, reset state and environment."""
        self.reset_flags()

        super(TestCasoManager, self).tearDown()


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
