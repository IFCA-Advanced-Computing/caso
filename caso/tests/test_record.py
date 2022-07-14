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

"""
Tests for `caso.record` module.
"""

import uuid

import caso
from caso import exception
from caso import record
from caso.tests import base


class TestCasoManager(base.TestCase):
    def test_invalid_version(self):
        r = record.CloudRecord(uuid=uuid.uuid4().hex,
                               site_name="site-foo",
                               compute_service="name-foo",
                               user_id=uuid.uuid4().hex,
                               group_id=uuid.uuid4().hex,
                               fqan="/Foo/User/Fqan")

        self.assertRaises(exception.RecordVersionNotFound,
                          r.as_dict, version="0.0")

        self.assertRaises(exception.RecordVersionNotFound,
                          r.as_json, version="0.0")

    def test_required_fields(self):
        server_id = uuid.uuid4().hex
        site_name = "site-foo"
        server_name = "name-foo"
        server_user_id = uuid.uuid4().hex
        server_project_id = uuid.uuid4().hex
        fqan = "FooVO"
        status = 'completed'
        image_id = uuid.uuid4().hex
        user_dn = "/Foo/bar/baz"

        expected = {
            'FQAN': fqan,
            'GlobalUserName': user_dn,
            'ImageId': image_id,
            'LocalGroupId': server_project_id,
            'LocalUserId': server_user_id,
            'MachineName': server_name,
            'SiteName': site_name,
            'Status': status,
            'VMUUID': server_id,
            'CloudType': caso.user_agent,
        }

        expected_02 = {
            'CpuCount': None,
            'CpuDuration': None,
            'Disk': None,
            'EndTime': None,
            'Memory': None,
            'NetworkInbound': None,
            'NetworkOutbound': None,
            'NetworkType': None,
            'StartTime': None,
            'StorageRecordId': None,
            'SuspendDuration': None,
            'WallDuration': None,
        }

        expected_04 = {
            'CloudComputeService': None,
            'BenchmarkType': None,
            'Benchmark': None,
            'PublicIPCount': None,
        }

        r = record.CloudRecord(server_id,
                               site_name,
                               server_name,
                               server_user_id,
                               server_project_id,
                               fqan,
                               status=status,
                               image_id=image_id,
                               user_dn=user_dn)

        d_02 = r.as_dict(version="0.2")
        self.assertDictContainsSubset(expected, d_02)
        self.assertDictContainsSubset(expected_02, d_02)

        d_04 = r.as_dict(version="0.4")
        self.assertDictContainsSubset(expected, d_04)
        self.assertDictContainsSubset(expected_04, d_04)
