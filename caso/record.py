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

import abc
import datetime
import typing
import uuid as m_uuid

import pydantic

import caso
from oslo_log import log

LOG = log.getLogger(__name__)


class BaseRecord(pydantic.BaseModel, abc.ABC):
    """This is the base cASO record object."""

    version: str

    site_name: str
    cloud_type = caso.user_agent
    compute_service: str


class CloudRecord(BaseRecord):
    """The CloudRecord class holds information for each of the records.

    This class is versioned, following the Cloud Accounting Record versions.
    """

    version: str = "0.4"

    uuid: m_uuid.UUID
    name: str

    user_id: m_uuid.UUID
    user_dn: typing.Optional[str]
    group_id: m_uuid.UUID
    fqan: str

    status: str

    start_time: datetime.datetime
    end_time: typing.Optional[datetime.datetime]

    suspend_duration: typing.Optional[int]

    _wall_duration: typing.Optional[int]
    _cpu_duration: typing.Optional[int]

    image_id: m_uuid.UUID

    public_ip_count = 0
    cpu_count: int
    memory: int
    disk: int

    benchmark_value: typing.Optional[float]
    benchmark_type: typing.Optional[str]

    @property
    def wall_duration(self) -> typing.Optional[int]:
        duration = None
        if self._wall_duration is not None:
            duration = self._wall_duration
        elif self.end_time:
            duration = int((self.end_time - self.start_time).total_seconds())
        return duration

    def set_wall_duration(self, value: int):
        self._wall_duration = value

    @property
    def cpu_duration(self) -> typing.Optional[int]:
        duration = None
        if self._cpu_duration is not None:
            duration = self._cpu_duration
        elif self.wall_duration is not None and self.cpu_count:
            duration = self.wall_duration * self.cpu_count
        return duration and int(duration)

    def set_cpu_duration(self, value: int):
        self._cpu_duration = value

    class Config:
        @staticmethod
        def map_fields(value: str) -> str:
            d = {
                "uuid": "VMUUID",
                "site_name": "SiteName",
                "name": "MachineName",
                "user_id": "LocalUserId",
                "group_id": "LocalGroupId",
                "fqan": "FQAN",
                "status": "Status",
                "start_time": "StartTime",
                "end_time": "EndTime",
                "suspend_duration": "SuspendDuration",
                "wall_duration": "WallDuration",
                "cpu_duration": "CpuDuration",
                "cpu_count": "CpuCount",
                "network_type": "NetworkType",
                "network_in": "NetworkInbound",
                "network_out": "NetworkOutbound",
                "memory": "Memory",
                "disk": "Disk",
                "storage_record_id": "StorageRecordId",
                "image_id": "ImageId",
                "cloud_type": "CloudType",
                "user_dn": "GlobalUserName",
                "public_ip_count": "PublicIPCount",
                "benchmark_value": "Benchmark",
                "benchmark_type": "BenchmarkType",
                "compute_service": "CloudComputeService",
            }
            return d.get(value, value)

        alias_generator = map_fields
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        extra = "forbid"


class IPRecord(BaseRecord):
    """The IPRecord class holds information for each of the records.

    This class is versioned, following the Public IP Usage Record versions.
    """

    version = "0.2"

    user_id: typing.Optional[m_uuid.UUID]
    user_dn: typing.Optional[str]
    group_id: m_uuid.UUID
    fqan: str

    measure_time: datetime.datetime

    ip_version: int
    public_ip_count: int

    class Config:
        @staticmethod
        def map_fields(field: str) -> str:
            d = {
                "measure_time": "MeasurementTime",
                "site_name": "SiteName",
                "cloud_type": "CloudType",
                "user_id": "LocalUser",
                "group_id": "LocalGroup",
                "fqan": "FQAN",
                "user_dn": "GlobalUserName",
                "ip_version": "IPVersion",
                "public_ip_count": "IPCount",
                "compute_service": "CloudComputeService",
            }
            return d.get(field, field)

        alias_generator = map_fields
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        extra = "forbid"


class AcceleratorRecord(object):
    """The AcceleratorRecord class holds information for each of the records.

    This class is versioned, following the Accelerator Usage Record versions

    """

    version = "0.1"

    uuid: m_uuid.UUID

    user_dn: typing.Optional[str]
    fqan: str

    count: int
    available_duration: int
    _active_duration: typing.Optional[int]

    measurement_month: int
    measurement_year: int

    associated_record_type: str = "cloud"

    accelerator_type: str
    cores: int
    model: str

    benchmark_value: typing.Optional[float]
    benchmark_type: typing.Optional[str]

    @property
    def active_duration(self) -> int:
        if self._active_duration is not None:
            return self._active_duration
        return self.available_duration

    def set_active_duration(self, value: int):
        self._active_duration = value

    class Config:
        @staticmethod
        def map_fields(field: str) -> str:
            d = {
                "measurement_month": "MeasurementMonth",
                "measurement_year": "MeasurementYear",
                "associated_record_type": "AssociatedRecordType",
                "uuid": "AccUUID",
                "user_dn": "GlobalUserName",
                "fqan": "FQAN",
                "site": "SiteName",
                "count": "Count",
                "cores": "Cores",
                "active_duration": "ActiveDuration",
                "available_duration": "AvailableDuration",
                "benchmark_type": "BenchmarkType",
                "benchmark": "Benchmark",
                "accelerator_type": "Type",
                "model": "Model",
            }
            return d.get(field, field)

        alias_generator = map_fields
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        extra = "forbid"


class StorageRecord(BaseRecord):
    """The StorageRecord class holds information for each of the records.

    This class is versioned, following the Storage Accounting Definition on
    EMI StAR
    """

    version: str = "0.1"

    uuid: uuid.UUID
    name: str

    user_id: str
    user_dn: typing.Optional[str]
    group_id: str
    fqan: str

    active_duration: int
    attached_duration: typing.Optional[float]
    attached_to: typing.Optional[str]
    measure_time: datetime.datetime
    start_time: datetime.datetime

    storage_type: typing.Optional[str] = "Block Storage (cinder)"

    status: str
    capacity: int

    # (aidaph) Fix the return to something different to 0
    @pydantic.validator("attached_duration", always=True)
    def validate_attached_duration(cls, value):
        if value is not None:
            return value
        return 0

    class Config:
        @staticmethod
        def map_fields(field: str) -> str:
            d = {
                "measure_time": "CreateTime",
                "uuid": "VolumeUUID",
                "name": "RecordName",
                "user_id": "LocalUser",
                "user_dn": "GlobalUserName",
                "group_id": "LocalGroup",
                "fqan": "FQAN",
                "site_name": "SiteName",
                "capacity": "Capacity",
                "active_duration": "ActiveDuration",
                "start_time": "StartTime",
                "storage_type": "Type",
                "status": "Status",
                "attached_to": "AttachedTo",
                "attached_duration": "AttachedDuration",
                "compute_service": "CloudComputeService",
            }
            return d.get(field, field)

        alias_generator = map_fields
        allow_population_by_field_name = True
        underscore_attrs_are_private = True
        extra = "forbid"
