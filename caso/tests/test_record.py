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

import pytest


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record(cloud_record):
    """Test a cloud record is correctly generated."""
    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * cloud_record.cpu_count

    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu

    assert isinstance(cloud_record.start_time, datetime.datetime)
    assert isinstance(cloud_record.end_time, datetime.datetime)


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record_map_opts(cloud_record, valid_cloud_record):
    """Test a cloud record is correctly rendered."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }

    assert json.loads(cloud_record.json(**opts)) == valid_cloud_record


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

    assert json.loads(cloud_record.json(**opts)) == valid_cloud_record


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
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


@pytest.mark.skip(reason="Pydantic 1 does not support computed fields")
def test_cloud_record_custom_cpu(cloud_record):
    """Test a cloud record is correctly rendered with custom cpu time."""
    wall = datetime.timedelta(days=5).total_seconds()
    cpu = wall * cloud_record.cpu_count * 10
    cloud_record.cpu_duration = cpu
    assert cloud_record.wall_duration == wall
    assert cloud_record.cpu_duration == cpu


def test_ip_record(ip_record):
    """Test that an IP record is correctly generated."""
    assert isinstance(ip_record.measure_time, datetime.datetime)


def test_ip_record_map_opts(ip_record, valid_ip_record):
    """Test that an IP record is correctly generated."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }

    assert json.loads(ip_record.json(**opts)) == valid_ip_record


def test_accelerator_record(accelerator_record):
    """Test that an IP record is correctly generated."""
    assert isinstance(accelerator_record.available_duration, int)


def test_accelerator_record_map_opts(accelerator_record, valid_accelerator_record):
    """Test that an IP record is correctly generated."""
    opts = {
        "by_alias": True,
        "exclude_none": True,
    }
    assert json.loads(accelerator_record.json(**opts)) == valid_accelerator_record
