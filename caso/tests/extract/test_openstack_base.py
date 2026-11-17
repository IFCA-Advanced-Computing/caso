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

"""Tests for the base OpenStack extractor helpers."""

import types
from unittest import mock

from caso.extract.openstack import base


def _resources(start, stop):
    return [types.SimpleNamespace(id=i, created=-i) for i in range(start, stop)]


def test_list_paginated_follows_markers_and_sorts():
    """All pages must be fetched using the last ID as marker, then sorted."""
    pages = [_resources(0, 2), _resources(2, 4), _resources(4, 5)]
    list_method = mock.Mock(side_effect=pages)

    result = base.BaseOpenStackExtractor._list_paginated(
        list_method, "created", limit=2, search_opts={"foo": "bar"}
    )

    assert [r.id for r in result] == [4, 3, 2, 1, 0]
    assert list_method.call_args_list == [
        mock.call(limit=2, marker=None, search_opts={"foo": "bar"}),
        mock.call(limit=2, marker=1, search_opts={"foo": "bar"}),
        mock.call(limit=2, marker=3, search_opts={"foo": "bar"}),
    ]


@mock.patch("caso.extract.openstack.base.keystone_client.get_session")
def test_keystone_session_is_shared_between_clients(m_get_session):
    """All the service clients must reuse the same Keystone session."""

    class Extractor(base.BaseOpenStackExtractor):
        def __init__(self):
            self.project = "project"

        def extract(self, extract_from, extract_to):
            return []

    extractor = Extractor()

    first = extractor._get_keystone_session()
    second = extractor._get_keystone_session()

    assert first is second
    m_get_session.assert_called_once()
