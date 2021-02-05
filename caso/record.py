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

import datetime
import json
import pprint

import caso
from caso import exception


class CloudRecord(object):
    """The CloudRecord class holds information for each of the records.

    This class is versioned, following the Cloud Accounting Record versions.
    """

    # Version 0.2: initial version
    # Version 0.4: Add 0.4 fields
    version = "0.4"

    _v02_fields = [
        "VMUUID",
        "SiteName",
        "MachineName",
        "LocalUserId",
        "LocalGroupId",
        "GlobalUserName",
        "FQAN",
        "Status",
        "StartTime",
        "EndTime",
        "SuspendDuration",
        "WallDuration",
        "CpuDuration",
        "CpuCount",
        "NetworkType",
        "NetworkInbound",
        "NetworkOutbound",
        "Memory",
        "Disk",
        "StorageRecordId",
        "ImageId",
        "CloudType",
    ]

    _v04_fields = _v02_fields + [
        "CloudComputeService",
        "BenchmarkType",
        "Benchmark",
        "PublicIPCount",
    ]

    _version_field_map = {
        "0.2": _v02_fields,
        "0.4": _v04_fields,
    }

    def __init__(
        self, uuid, site, name, user_id, group_id, fqan,
        cloud_type=caso.user_agent,
        compute_service=None,
        status=None,
        start_time=None,
        end_time=None,
        suspend_duration=None,
        wall_duration=None,
        cpu_duration=None,
        network_type=None,
        network_in=None,
        network_out=None,
        public_ip_count=None,
        cpu_count=None,
        memory=None,
        disk=None,
        image_id=None,
        storage_record_id=None,
        user_dn=None,
        vo=None,
        vo_group=None,
        vo_role=None,
        benchmark_value=None,
        benchmark_type=None
    ):

        self.uuid = uuid
        self.site = site
        self.name = name
        self.user_id = user_id
        self.group_id = group_id
        self.fqan = fqan
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.suspend_duration = suspend_duration
        self.wall_duration = wall_duration
        self.cpu_duration = cpu_duration
        self.network_type = network_type
        self.network_in = network_in
        self.network_out = network_out
        self.cpu_count = cpu_count
        self.memory = memory
        self.disk = disk
        self.image_id = image_id
        self.cloud_type = cloud_type
        self.storage_record_id = storage_record_id
        self.user_dn = user_dn
        self.compute_service = compute_service
        self.benchmark_value = benchmark_value
        self.benchmark_type = benchmark_type
        self.public_ip_count = public_ip_count

    def __repr__(self):
        return pprint.pformat(self.as_dict())

    def as_dict(self, version=None):
        """Return CloudRecord as a dictionary.

        :param str version: optional, if passed it will format the record
                            acording to that account record version

        :returns: A dict containing the record.
        """
        if version is None:
            version = self.version

        if version not in self._version_field_map:
            raise exception.RecordVersionNotFound(version=version)

        return {k: v for k, v in self.map.items()
                if k in self._version_field_map[version]}

    @property
    def wall_duration(self):
        duration = None
        if self._wall_duration is not None:
            duration = self._wall_duration
        elif None not in (self._start_time, self._end_time):
            duration = (self.end_time - self.start_time).total_seconds()
        return duration and int(duration)

    @wall_duration.setter
    def wall_duration(self, value):
        if value and not isinstance(value, (int, float)):
            raise ValueError("Duration must be a number")
        self._wall_duration = value

    @property
    def cpu_duration(self):
        duration = None
        if self._cpu_duration is not None:
            duration = self._cpu_duration
        elif self.wall_duration is not None and self.cpu_count:
            duration = self.wall_duration * self.cpu_count
        return duration and int(duration)

    @cpu_duration.setter
    def cpu_duration(self, value):
        if value and not isinstance(value, (int, float)):
            raise ValueError("Duration must be a number")
        self._cpu_duration = value

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value):
        if value and not isinstance(value, datetime.datetime):
            raise ValueError("Dates must be datetime.datetime objects")
        self._start_time = value

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        if value and not isinstance(value, datetime.datetime):
            raise ValueError("Dates must be datetime.datetime objects")
        self._end_time = value

    @property
    def map(self):
        d = {
            'VMUUID': self.uuid,
            'SiteName': self.site,
            'MachineName': self.name,
            'LocalUserId': self.user_id,
            'LocalGroupId': self.group_id,
            'FQAN': self.fqan,
            'Status': self.status,
            'StartTime': self.start_time and int(
                self.start_time.strftime("%s")
            ),
            'EndTime': self.end_time and int(
                self.end_time.strftime("%s")
            ),
            'SuspendDuration': self.suspend_duration,
            'WallDuration': self.wall_duration,
            'CpuDuration': self.cpu_duration,
            'CpuCount': self.cpu_count,
            'NetworkType': self.network_type,
            'NetworkInbound': self.network_in,
            'NetworkOutbound': self.network_out,
            'Memory': self.memory,
            'Disk': self.disk,
            'StorageRecordId': self.storage_record_id,
            'ImageId': self.image_id,
            'CloudType': self.cloud_type,
            'GlobalUserName': self.user_dn,
            'PublicIPCount': self.public_ip_count,
            'Benchmark': self.benchmark_value,
            'BenchmarkType': self.benchmark_type,
            'CloudComputeService': self.compute_service,
        }
        return d

    def as_json(self, version=None):
        return json.dumps(self.as_dict(version=version))


class IPRecord(object):
    """The IPRecord class holds information for each of the records.

    This class is versioned, following the Public IP Usage Record versions

    """

    version = "0.2"

    _V02_fields = [
        "MeasurementTime",
        "SiteName",
        "CloudComputeService",
        "CloudType",
        "LocalUser",
        "LocalGroup",
        "GlobalUserName",
        "FQAN",
        "IPVersion",
        "IPCount",
    ]

    _version_field_map = {
        "0.2": _V02_fields,
    }

    def __init__(
        self, measure_time, site,
        user_id, group_id, user_dn, fqan,
        ip_version, public_ip_count,
        cloud_type=caso.user_agent,
        compute_service=None
    ):

        self.measure_time = measure_time
        self.site = site
        self.cloud_type = cloud_type
        self.user_id = user_id
        self.group_id = group_id
        self.user_dn = user_dn
        self.fqan = fqan
        self.compute_service = compute_service
        self.ip_version = ip_version
        self.public_ip_count = public_ip_count

    def __repr__(self):
        return pprint.pformat(self.as_dict())

    def as_dict(self, version=None):
        """Return IPRecord as a dictionary.

        :param str version: optional, if passed it will format the record
                            acording to that account record version

        :returns: A dict containing the record.
        """
        if version is None:
            version = self.version

        if version not in self._version_field_map:
            raise exception.RecordVersionNotFound(version=version)

        return {k: v for k, v in self.map.items()
                if k in self._version_field_map[version]}

    @property
    def measure_time(self):
        return self._measure_time

    @measure_time.setter
    def measure_time(self, value):
        if value and not isinstance(value, datetime.datetime):
            raise ValueError("Dates must be datetime.datetime objects")
        self._measure_time = value

    @property
    def map(self):
        d = {
            'MeasurementTime': self.measure_time and int(
                self.measure_time.strftime("%s")
            ),
            'SiteName': self.site,
            'CloudType': self.cloud_type,
            'LocalUser': self.user_id,
            'LocalGroup': self.group_id,
            'FQAN': self.fqan,
            'GlobalUserName': self.user_dn,
            'IPVersion': self.ip_version,
            'IPCount': self.public_ip_count,
            'CloudComputeService': self.compute_service,
        }
        return d

    def as_json(self, version=None):
        print(self.map)
        return json.dumps(self.as_dict(version=version))
