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

"""Tests for the OpenStack neutron extractor."""

import datetime
from unittest import mock

import pytest

from caso.extract.openstack import neutron


@pytest.fixture
def extractor():
    """Get a Neutron extractor with all external clients mocked."""
    with mock.patch.object(
        neutron.NeutronExtractor, "__init__", lambda self, *a, **kw: None
    ):
        ext = neutron.NeutronExtractor("project", "vo")
    ext.project_id = "project-id"
    ext.vo = "vo"
    ext.users = {None: None}
    ext.neutron = mock.MagicMock()
    return ext


def _fip(address, created="2023-05-25T12:00:00Z"):
    return {"floating_ip_address": address, "created_at": created}


@mock.patch("caso.extract.openstack.neutron.CONF")
def test_extract_filters_by_project(mock_conf, extractor):
    """Floating IPs must be requested for the extractor's project only."""
    mock_conf.site_name = "site"
    mock_conf.service_name = "service"
    extractor.neutron.list_floatingips.return_value = {"floatingips": []}

    extractor.extract(datetime.datetime(2023, 5, 1), datetime.datetime(2023, 6, 1))

    extractor.neutron.list_floatingips.assert_called_once_with(project_id="project-id")


@mock.patch("caso.extract.openstack.neutron.CONF")
def test_extract_keeps_ipv4_and_ipv6_records(mock_conf, extractor):
    """IPv4 and IPv6 counts must produce separate records."""
    mock_conf.site_name = "site"
    mock_conf.service_name = "service"
    extractor.neutron.list_floatingips.return_value = {
        "floatingips": [
            _fip("192.0.2.1"),
            _fip("192.0.2.2"),
            _fip("2001:db8::1"),
            # Created after the extraction period, must be ignored
            _fip("192.0.2.3", created="2023-07-01T00:00:00Z"),
        ]
    }

    records = extractor.extract(
        datetime.datetime(2023, 5, 1), datetime.datetime(2023, 6, 1)
    )

    counts = {r.ip_version: r.public_ip_count for r in records}
    assert counts == {4: 2, 6: 1}
