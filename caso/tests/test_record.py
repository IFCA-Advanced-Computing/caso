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

"""Test for cASO records."""

import datetime
import json
import uuid

import pytest

import caso.record

valid_record_fields = dict(
    uuid=str(uuid.uuid4()),
    site_name="TEST-Site",
    name="VM Name",
    user_id=str(uuid.uuid4()),
    group_id=str(uuid.uuid4()),
    fqan="VO FQAN",
    start_time=datetime.datetime.now() - datetime.timedelta(days=5),
    end_time=datetime.datetime.now(),
    compute_service="Fake Cloud Service",
    status="ACTIVE",
    image_id=str(uuid.uuid4()),
    user_dn="User DN",
    benchmark_type=None,
    benchmark_value=None,
    memory=16,
    cpu_count=8,
    disk=250,
    public_ip_count=7,
)

valid_record = {
    "CloudComputeService": "Fake Cloud Service",
    "CpuCount": 8,
    "CpuDuration": 3456000,
    "Disk": 250,
    "StartTime": int(valid_record_fields["start_time"].timestamp()),
    "EndTime": int(valid_record_fields["end_time"].timestamp()),
    "FQAN": "VO FQAN",
    "GlobalUserName": "User DN",
    "ImageId": valid_record_fields["image_id"],
    "LocalGroupId": valid_record_fields["group_id"],
    "LocalUserId": valid_record_fields["user_id"],
    "MachineName": "VM Name",
    "Memory": 16,
    "PublicIPCount": 7,
    "SiteName": "TEST-Site",
    "Status": "ACTIVE",
    "VMUUID": valid_record_fields["uuid"],
    "WallDuration": 432000,
}


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record():
    """Test a cloud record is correctly generated."""
    record = caso.record.CloudRecord(**valid_record_fields)

    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * record.cpu_count

    assert record.wall_duration == wall
    assert record.cpu_duration == cpu

    assert isinstance(record.start_time, datetime.datetime)
    assert isinstance(record.end_time, datetime.datetime)


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record_map_opts():
    """Test a cloud record is correctly rendered."""
    record = caso.record.CloudRecord(**valid_record_fields)

    opts = {
        "by_alias": True,
        "exclude_unset": True,
        "exclude_none": True,
    }

    assert json.loads(record.json(**opts)) == valid_record


def test_cloud_record_map_opts_custom_wall_cpu():
    """Test a cloud record is correctly rendered with custom wall and cpu times."""
    record = caso.record.CloudRecord(**valid_record_fields)

    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * record.cpu_count
    record.wall_duration = wall
    record.cpu_duration = cpu

    opts = {
        "by_alias": True,
        "exclude_unset": True,
        "exclude_none": True,
    }

    assert json.loads(record.json(**opts)) == valid_record


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record_custom_wall():
    """Test a cloud record is correctly rendered with custom wall time."""
    record = caso.record.CloudRecord(**valid_record_fields)

    wall = 200
    cpu = wall * record.cpu_count
    record.wall_duration = wall
    assert record.wall_duration == wall
    assert record.cpu_duration == cpu


def test_cloud_record_custom_wall_cpu():
    """Test a cloud record is correctly generated with custom wall and cpu time."""
    record = caso.record.CloudRecord(**valid_record_fields)

    wall = 200
    cpu = wall * record.cpu_count
    record.wall_duration = wall
    record.cpu_duration = cpu

    assert record.wall_duration == wall
    assert record.cpu_duration == cpu


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record_custom_cpu():
    """Test a cloud record is correctly rendered with custom cpu time."""
    record = caso.record.CloudRecord(**valid_record_fields)

    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * record.cpu_count * 10
    record.cpu_duration = cpu
    assert record.wall_duration == wall
    assert record.cpu_duration == cpu
