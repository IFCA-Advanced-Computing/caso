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

"""Tests for the OpenStack cinder extractor."""

import datetime
import types
from unittest import mock

import pytest

from caso.extract.openstack import cinder

EXTRACT_FROM = datetime.datetime(2023, 5, 1)
EXTRACT_TO = datetime.datetime(2023, 6, 1)


@pytest.fixture
def extractor():
    """Get a Cinder extractor with all external clients mocked."""
    with mock.patch.object(
        cinder.CinderExtractor, "__init__", lambda self, *a, **kw: None
    ):
        ext = cinder.CinderExtractor("project", "vo")
    ext.project_id = "project-id"
    ext.vo = "vo"
    ext.users = {"user": "User DN"}
    ext.cinder = mock.MagicMock()
    with mock.patch("caso.extract.openstack.cinder.CONF") as m_conf:
        m_conf.site_name = "site"
        m_conf.service_name = "service"
        yield ext


def _volume(created_at, status="available", attachments=()):
    return types.SimpleNamespace(
        id="99cf5d02-a573-46a1-b90d-0f7327126876",
        name="volume",
        user_id="user",
        status=status,
        size=10,
        created_at=created_at,
        attachments=list(attachments),
    )


def test_active_duration_is_clipped_to_period(extractor):
    """Volumes created before the period only account for the period."""
    vol = _volume("2023-04-01T00:00:00.123456")

    r = extractor._build_record(vol, EXTRACT_FROM, EXTRACT_TO)

    assert r.start_time == EXTRACT_FROM
    assert r.volume_creation == datetime.datetime(2023, 4, 1, 0, 0, 0, 123456)
    assert r.active_duration == 31 * 86400


def test_volume_created_after_period_is_skipped(extractor):
    """Volumes created after the period must not produce negative records."""
    extractor.cinder.volumes.list.return_value = [_volume("2023-07-01T00:00:00")]

    assert extractor.extract(EXTRACT_FROM, EXTRACT_TO) == []


def test_all_attachments_are_reported(extractor):
    """Multi-attach volumes must report all the servers they are attached to."""
    vol = _volume(
        "2023-04-01T00:00:00",
        status="in-use",
        attachments=[
            {"server_id": "s1", "attached_at": "2023-05-31T00:00:00"},
            {"server_id": "s2", "attached_at": "2023-05-30T00:00:00"},
        ],
    )

    r = extractor._build_record(vol, EXTRACT_FROM, EXTRACT_TO)

    assert r.attached_to == "s1,s2"
    assert r.attached_duration == 2 * 86400


def test_in_use_volume_without_attachments(extractor):
    """An in-use volume without attachment details must not fail."""
    vol = _volume("2023-04-01T00:00:00", status="in-use")

    r = extractor._build_record(vol, EXTRACT_FROM, EXTRACT_TO)

    assert r.attached_to is None
    assert r.attached_duration is None
