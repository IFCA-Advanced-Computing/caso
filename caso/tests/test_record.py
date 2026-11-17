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
import time

import pytest

import caso.record
from caso.tests import conftest


def test_cloud_record(cloud_record):
    """Test a cloud record is correctly generated."""
    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * cloud_record.cpu_count

    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu

    assert isinstance(cloud_record.start_time, datetime.datetime)
    assert isinstance(cloud_record.end_time, datetime.datetime)
    assert isinstance(cloud_record.start_time_epoch, int)
    assert isinstance(cloud_record.end_time_epoch, int)


def test_cloud_record_map_opts(cloud_record, valid_cloud_record):
    """Test a cloud record is correctly rendered."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }

    assert json.loads(cloud_record.model_dump_json(**opts)) == valid_cloud_record


def test_cloud_record_map_opts_custom_wall_cpu(cloud_record, valid_cloud_record):
    """Test a cloud record is correctly rendered with custom wall and cpu times."""
    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * cloud_record.cpu_count
    cloud_record.wall_duration = wall
    cloud_record.cpu_duration = cpu

    opts = {
        "by_alias": True,
        "exclude_none": True,
    }

    assert json.loads(cloud_record.model_dump_json(**opts)) == valid_cloud_record


def test_cloud_record_custom_wall(cloud_record):
    """Test a cloud record is correctly rendered with custom wall time."""
    wall = 200
    cpu = wall * cloud_record.cpu_count
    cloud_record.wall_duration = wall
    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu


def test_cloud_record_custom_wall_cpu(cloud_record):
    """Test a cloud record is correctly generated with custom wall and cpu time."""
    wall = 200
    cpu = wall * cloud_record.cpu_count
    cloud_record.wall_duration = wall
    cloud_record.cpu_duration = cpu

    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu


def test_cloud_record_custom_cpu(cloud_record):
    """Test a cloud record is correctly rendered with custom cpu time."""
    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * cloud_record.cpu_count * 10
    cloud_record.cpu_duration = cpu
    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu


def test_cloud_record_zero_cpu(zero_cpu_cloud_record):
    """Test a cloud record with 0 CPU time is correctly rendered."""
    ssm_message = zero_cpu_cloud_record.ssm_message()
    assert "CpuDuration: 1" in ssm_message
    assert "WallDuration: 1" in ssm_message


def test_ip_record(ip_record):
    """Test that an IP record is correctly generated."""
    assert isinstance(ip_record.measure_time, datetime.datetime)


def test_ip_record_map_opts(ip_record, valid_ip_record):
    """Test that an IP record is correctly generated."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }

    assert json.loads(ip_record.model_dump_json(**opts)) == valid_ip_record


def test_accelerator_record(accelerator_record):
    """Test that an IP record is correctly generated."""
    assert isinstance(accelerator_record.available_duration, int)


def test_accelerator_record_map_opts(accelerator_record, valid_accelerator_record):
    """Test that an IP record is correctly generated."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }
    assert (
        json.loads(accelerator_record.model_dump_json(**opts))
        == valid_accelerator_record  # noqa
    )


def test_storage_record(storage_record):
    """Test that an IP record is correctly generated."""
    assert isinstance(storage_record.active_duration, int)


def test_storage_record_map_opts(storage_record, valid_storage_record):
    """Test that an IP record is correctly generated."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }
    assert json.loads(storage_record.model_dump_json(**opts)) == valid_storage_record


def test_energy_record(energy_record):
    """Test that an Energy record is correctly generated."""
    assert energy_record.energy_wh == 5.0
    assert energy_record.work == 10.0
    assert energy_record.efficiency == 0.5
    assert energy_record.wall_clock_time_s == 3600
    assert energy_record.cpu_duration_s == 1800
    assert energy_record.status == "running"


def test_energy_record_map_opts(energy_record, valid_energy_record):
    """Test that an Energy record is correctly rendered."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }
    assert json.loads(energy_record.model_dump_json(**opts)) == valid_energy_record


@pytest.fixture
def non_utc_local_timezone(monkeypatch):
    """Run the test with a local time zone that is not UTC."""
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_naive_datetimes_are_treated_as_utc(non_utc_local_timezone):
    """Naive datetimes coming from the extractors are UTC, not local time."""
    fields = dict(conftest.valid_cloud_records_fields[0])
    fields["start_time"] = datetime.datetime(2023, 5, 20, 21, 59, 6)
    fields["end_time"] = datetime.datetime(2023, 5, 25, 21, 59, 6)
    record = caso.record.CloudRecord(**fields)

    assert record.start_time_epoch == 1684619946
    assert record.end_time_epoch == 1685051946


def test_storage_message_with_naive_datetimes(non_utc_local_timezone):
    """Storage records must render naive datetimes as UTC."""
    fields = dict(conftest.valid_storage_records_fields[0])
    fields["start_time"] = datetime.datetime(2023, 5, 20, 21, 59, 6)
    fields["measure_time"] = datetime.datetime(2023, 5, 25, 21, 59, 6)
    fields["volume_creation"] = datetime.datetime(2023, 5, 20, 21, 59, 6)
    record = caso.record.StorageRecord(**fields)

    assert record.measure_time_epoch == 1685051946
    message = record.ssm_message().decode()
    assert "<sr:StartTime>2023-05-20T21:59:06+00:00</sr:StartTime>" in message
    assert 'sr:createTime="2023-05-25T21:59:06+00:00"' in message
