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

"""Fixtures for cASO tests."""

import datetime

import pytest

import caso
import caso.record

now = datetime.datetime(2023, 5, 25, 21, 59, 6, 0)
cloud_type = caso.user_agent

valid_cloud_records_fields = [
    dict(
        uuid="721cf1db-0e0f-4c24-a5ea-cd75e0f303e8",
        site_name="TEST-Site",
        name="VM Name 1",
        user_id="a4519d7d-f60a-4908-9d63-7d9e17422188",
        group_id="03b6a6c4-cf2b-48b9-82f1-69c52b9f30af",
        fqan="VO 1 FQAN",
        start_time=now - datetime.timedelta(days=5),
        end_time=now,
        compute_service="Fake Cloud Service",
        status="started",
        image_id="b39a8ed9-e15d-4b71-ada2-daf88efbac0a",
        user_dn="User DN",
        benchmark_type=None,
        benchmark_value=None,
        memory=16,
        cpu_count=8,
        disk=250,
        public_ip_count=7,
    ),
    dict(
        uuid="a53738e1-13eb-4047-800c-067d14ce3d22",
        site_name="TEST-Site",
        name="VM Name 2",
        user_id="a4519d7d-f60a-4908-9d63-7d9e17422188",
        group_id="03b6a6c4-cf2b-48b9-82f1-69c52b9f30af",
        fqan="VO 2 FQAN",
        start_time=now - datetime.timedelta(days=6),
        end_time=now,
        compute_service="Fake Cloud Service",
        status="completed",
        image_id="b39a8ed9-e15d-4b71-ada2-daf88efbac0a",
        user_dn="User DN",
        benchmark_type=None,
        benchmark_value=None,
        memory=16,
        cpu_count=8,
        disk=250,
        public_ip_count=7,
    ),
]

valid_cloud_records_dict = [
    {
        "CloudComputeService": "Fake Cloud Service",
        "CpuCount": 8,
        "CpuDuration": 3456000,
        "CloudType": cloud_type,
        "Disk": 250,
        "StartTime": 1684612746,
        "EndTime": 1685044746,
        "FQAN": "VO 1 FQAN",
        "GlobalUserName": "User DN",
        "ImageId": "b39a8ed9-e15d-4b71-ada2-daf88efbac0a",
        "LocalGroupId": "03b6a6c4-cf2b-48b9-82f1-69c52b9f30af",
        "LocalUserId": "a4519d7d-f60a-4908-9d63-7d9e17422188",
        "MachineName": "VM Name 1",
        "Memory": 16,
        "PublicIPCount": 7,
        "SiteName": "TEST-Site",
        "Status": "started",
        "VMUUID": "721cf1db-0e0f-4c24-a5ea-cd75e0f303e8",
        "WallDuration": 432000,
    },
    {
        "CloudComputeService": "Fake Cloud Service",
        "CpuCount": 8,
        "CpuDuration": 3456000,
        "CloudType": cloud_type,
        "Disk": 250,
        "StartTime": 1684526346,
        "EndTime": 1685044746,
        "FQAN": "VO 2 FQAN",
        "GlobalUserName": "User DN",
        "ImageId": "b39a8ed9-e15d-4b71-ada2-daf88efbac0a",
        "LocalGroupId": "03b6a6c4-cf2b-48b9-82f1-69c52b9f30af",
        "LocalUserId": "a4519d7d-f60a-4908-9d63-7d9e17422188",
        "MachineName": "VM Name 2",
        "Memory": 16,
        "PublicIPCount": 7,
        "SiteName": "TEST-Site",
        "Status": "completed",
        "VMUUID": "a53738e1-13eb-4047-800c-067d14ce3d22",
        "WallDuration": 432000,
    },
]

# Record fixtures


@pytest.fixture(scope="module")
def cloud_record():
    """Get a fixture for the CloudRecord."""
    record = caso.record.CloudRecord(**valid_cloud_records_fields[0])
    # Remove this when moving to Pydantic 2
    record.wall_duration = 432000
    record.cpu_duration = 3456000
    return record


@pytest.fixture(scope="module")
def another_cloud_record():
    """Get another fixture for the CloudRecord."""
    record = caso.record.CloudRecord(**valid_cloud_records_fields[1])
    record.wall_duration = 432000
    record.cpu_duration = 3456000
    return record


@pytest.fixture(scope="module")
def valid_cloud_record():
    """Get a fixture for a valid record."""
    return valid_cloud_records_dict[0]


@pytest.fixture(scope="module")
def valid_cloud_records():
    """Get a fixture for valid records as a dict."""
    return valid_cloud_records_dict


@pytest.fixture(scope="module")
def another_valid_cloud_record():
    """Get another fixture for a valid record as a dict."""
    return valid_cloud_records_dict[0]


@pytest.fixture(scope="module")
def cloud_record_list(cloud_record, another_cloud_record):
    """Get a fixture for a list of valid records."""
    return [cloud_record, another_cloud_record]


# SSM entries


@pytest.fixture
def expected_entries_cloud():
    """Get a fixture for all cloud entries."""
    ssm_entries = [
        "CloudComputeService: Fake Cloud Service\n"
        f"CloudType: {cloud_type}\n"
        "CpuCount: 8\n"
        "CpuDuration: 3456000\n"
        "Disk: 250\n"
        "EndTime: 1685044746\n"
        "FQAN: VO 1 FQAN\n"
        "GlobalUserName: User DN\n"
        "ImageId: b39a8ed9-e15d-4b71-ada2-daf88efbac0a\n"
        "LocalGroupId: 03b6a6c4-cf2b-48b9-82f1-69c52b9f30af\n"
        "LocalUserId: a4519d7d-f60a-4908-9d63-7d9e17422188\n"
        "MachineName: VM Name 1\n"
        "Memory: 16\n"
        "PublicIPCount: 7\n"
        "SiteName: TEST-Site\n"
        "StartTime: 1684612746\n"
        "Status: started\n"
        "VMUUID: 721cf1db-0e0f-4c24-a5ea-cd75e0f303e8\n"
        "WallDuration: 432000",
        "CloudComputeService: Fake Cloud Service\n"
        f"CloudType: {cloud_type}\n"
        "CpuCount: 8\n"
        "CpuDuration: 3456000\n"
        "Disk: 250\n"
        "EndTime: 1685044746\n"
        "FQAN: VO 2 FQAN\n"
        "GlobalUserName: User DN\n"
        "ImageId: b39a8ed9-e15d-4b71-ada2-daf88efbac0a\n"
        "LocalGroupId: 03b6a6c4-cf2b-48b9-82f1-69c52b9f30af\n"
        "LocalUserId: a4519d7d-f60a-4908-9d63-7d9e17422188\n"
        "MachineName: VM Name 2\n"
        "Memory: 16\n"
        "PublicIPCount: 7\n"
        "SiteName: TEST-Site\n"
        "StartTime: 1684526346\n"
        "Status: completed\n"
        "VMUUID: a53738e1-13eb-4047-800c-067d14ce3d22\n"
        "WallDuration: 432000",
    ]

    return ssm_entries
