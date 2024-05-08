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

"""Module containing all the cloud accounting records."""

import abc
import datetime
import enum
import json
import typing
import uuid as m_uuid

# We are not parsing XML so this is safe
import xml.etree.ElementTree as ETree  # nosec

import pydantic

import caso
from oslo_log import log

LOG = log.getLogger(__name__)


class _BaseRecord(pydantic.BaseModel, abc.ABC):
    """This is the base cASO record object."""

    version: str = pydantic.Field(..., exclude=True)

    site_name: str
    cloud_type: str = caso.user_agent
    compute_service: str

    @abc.abstractmethod
    def ssm_message(self):
        """Render record as the expected SSM message."""
        raise NotImplementedError("Method not implemented")


class _ValidCloudStatus(str, enum.Enum):
    """This is a private class to enum valid cloud statuses."""

    started = "started"
    completed = "completed"
    error = "error"
    paused = "paused"
    suspended = "suspended"
    stopped = "stopped"
    unknown = "unknown"


def map_cloud_fields(value: str) -> str:
    """Map object fields to Cloud Accounting Record fields."""
    d = {
        "uuid": "VMUUID",
        "site_name": "SiteName",
        "name": "MachineName",
        "user_id": "LocalUserId",
        "group_id": "LocalGroupId",
        "fqan": "FQAN",
        "status": "Status",
        "start_time_epoch": "StartTime",
        "end_time_epoch": "EndTime",
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
        "cloud_type": "CloudType",
    }
    return d.get(value, value)


class CloudRecord(_BaseRecord):
    """The CloudRecord class holds information for each of the records.

    This class is versioned, following the Cloud Accounting Record versions.
    """

    version: str = pydantic.Field("0.4", exclude=True)

    uuid: m_uuid.UUID
    name: str

    user_id: str
    user_dn: typing.Optional[str] = None
    group_id: str
    fqan: str

    status: _ValidCloudStatus

    image_id: typing.Optional[str] = None

    public_ip_count: int = 0
    cpu_count: int
    memory: int
    disk: int

    # Make these fields private, and deal with them as properties. This is done as  all
    # the accounting infrastructure needs start and end times as integers, but it is
    # easier for us to maintain them as datetime objects internally.
    _start_time: datetime.datetime
    _end_time: typing.Optional[datetime.datetime] = None

    suspend_duration: typing.Optional[int] = None

    _wall_duration: typing.Optional[int] = None
    _cpu_duration: typing.Optional[int] = None

    benchmark_value: typing.Optional[float] = None
    benchmark_type: typing.Optional[str] = None

    def __init__(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        *args,
        **kwargs,
    ):
        """Initialize the record."""
        super(CloudRecord, self).__init__(*args, **kwargs)

        # Set start time and end times, see comment above.
        self._start_time = start_time
        self._end_time = end_time

    @property
    def start_time(self) -> datetime.datetime:
        """Get start time."""
        return self._start_time

    @start_time.setter
    def start_time(self, start_time: datetime.datetime) -> None:
        """Set start time."""
        self._start_time = start_time

    # NOTE(aloga): we need to specify an alias here, as per the following bug:
    # https://github.com/pydantic/pydantic/issues/5825
    # This is needed for all computed fields.
    @pydantic.computed_field(alias="StartTime")  # type: ignore[misc]
    @property
    def start_time_epoch(self) -> int:
        """Get start time as epoch."""
        return int(self._start_time.timestamp())

    @property
    def end_time(self) -> typing.Optional[datetime.datetime]:
        """Get end time."""
        if self._end_time is not None:
            return self._end_time
        else:
            return None

    @end_time.setter
    def end_time(self, end_time: datetime.datetime) -> None:
        """Set end time."""
        self._end_time = end_time

    @pydantic.computed_field()  # type: ignore[misc]
    @property
    def end_time_epoch(self) -> typing.Optional[int]:
        """Get end time as epoch."""
        if self.end_time:
            return int(self.end_time.timestamp())
        else:
            return 0

    @pydantic.computed_field()  # type: ignore[misc]
    @property
    def wall_duration(self) -> typing.Optional[int]:
        """Get wall duration."""
        duration = None
        if self._wall_duration is not None:
            duration = self._wall_duration
        elif self.end_time:
            duration = self.end_time - self.start_time
            duration = int(duration.total_seconds())
        return duration

    @wall_duration.setter
    def wall_duration(self, wall: int) -> None:
        """Set wall duration."""
        self._wall_duration = wall

    @pydantic.computed_field()  # type: ignore[misc]
    @property
    def cpu_duration(self) -> typing.Optional[int]:
        """Get CPU duration."""
        duration = None
        if self._cpu_duration is not None:
            duration = self._cpu_duration
        elif self.wall_duration is not None and self.cpu_count:
            duration = self.wall_duration * self.cpu_count
        return duration

    @cpu_duration.setter
    def cpu_duration(self, value: int) -> None:
        """Set the CPU duration."""
        self._cpu_duration = value

    def ssm_message(self):
        """Render record as the expected SSM message."""
        opts = {
            "by_alias": True,
            "exclude_none": True,
        }
        # NOTE(aloga): do not iter over the dictionary returned by record.dict() as this
        # is just a dictionary representation of the object, where no serialization is
        # done. In order to get objects correctly serialized we need to convert to JSON,
        # then reload the model
        serialized_record = json.loads(self.model_dump_json(**opts))
        aux = [f"{k}: {v}" for k, v in serialized_record.items()]
        aux.sort()
        return "\n".join(aux)

    model_config = dict(
        alias_generator=map_cloud_fields,
        populate_by_name=True,
        extra="forbid",
    )


def map_ip_fields(field: str) -> str:
    """Map object fields to accounting Public IP Usage record fields."""
    d = {
        "measure_time_epoch": "MeasurementTime",
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


class IPRecord(_BaseRecord):
    """The IPRecord class holds information for each of the records.

    This class is versioned, following the Public IP Usage Record versions.
    """

    version: str = pydantic.Field("0.2", exclude=True)

    uuid: m_uuid.UUID

    user_id: typing.Optional[str]
    user_dn: typing.Optional[str]
    group_id: str
    fqan: str

    # Make these fields private, and deal with them as properties. This is done as  all
    # the accounting infrastructure needs start and end times as integers, but it is
    # easier for us to maintain them as datetime objects internally.
    _measure_time: datetime.datetime

    ip_version: int
    public_ip_count: int

    def __init__(self, measure_time: datetime.datetime, *args, **kwargs):
        """Initialize the record."""
        super(IPRecord, self).__init__(*args, **kwargs)

        self._measure_time = measure_time

    @property
    def measure_time(self) -> datetime.datetime:
        """Get measurement time."""
        return self._measure_time

    @pydantic.computed_field()
    @property
    def measure_time_epoch(self) -> int:
        """Get measurement time as epoch."""
        return int(self._measure_time.timestamp())

    @measure_time.setter
    def measure_time(self, measure_time: datetime.datetime) -> None:
        """Set measurement time."""
        self._measure_time = measure_time

    def ssm_message(self):
        """Render record as the expected SSM message."""
        opts = {
            "by_alias": True,
            "exclude_none": True,
        }
        return self.model_dump_json(**opts)

    model_config = dict(
        alias_generator=map_ip_fields,
        populate_by_name=True,
        extra="forbid",
    )


def map_accelerator_fields(field: str) -> str:
    """Map object fields to accounting Accelerator Usage Record fields."""
    d = {
        "measurement_month": "MeasurementMonth",
        "measurement_year": "MeasurementYear",
        "associated_record_type": "AssociatedRecordType",
        "uuid": "AccUUID",
        "user_dn": "GlobalUserName",
        "fqan": "FQAN",
        "site_name": "SiteName",
        "count": "Count",
        "cores": "Cores",
        "active_duration": "ActiveDuration",
        "available_duration": "AvailableDuration",
        "benchmark_type": "BenchmarkType",
        "benchmark": "Benchmark",
        "accelerator_type": "Type",
        "model": "Model",
        "compute_service": "CloudComputeService",
        "cloud_type": "CloudType",
    }
    return d.get(field, field)


class AcceleratorRecord(_BaseRecord):
    """The AcceleratorRecord class holds information for each of the records.

    This class is versioned, following the Accelerator Usage Record versions

    """

    version: str = pydantic.Field("0.1", exclude=True)

    uuid: m_uuid.UUID

    user_dn: typing.Optional[str]
    fqan: str

    count: int
    available_duration: int
    _active_duration: typing.Optional[int] = None

    measurement_month: int
    measurement_year: int

    associated_record_type: str = "cloud"

    accelerator_type: str
    cores: typing.Optional[int] = None
    model: str

    benchmark_value: typing.Optional[float] = None
    benchmark_type: typing.Optional[str] = None

    @pydantic.computed_field  # type: ignore[misc]
    @property
    def active_duration(self) -> int:
        """Get the active duration for the record (property)."""
        if self._active_duration is not None:
            return self._active_duration
        return self.available_duration

    @active_duration.setter
    def active_duration(self, value: int) -> None:
        """Set the active duration for the record."""
        self._active_duration = value

    def ssm_message(self):
        """Render record as the expected SSM message."""
        opts = {
            "by_alias": True,
            "exclude_none": True,
        }
        return self.model_dump_json(**opts)

    model_config = dict(
        alias_generator=map_accelerator_fields,
        populate_by_name=True,
        extra="forbid",
    )


def map_storage_fields(field: str) -> str:
    """Map object fields to accounting EMI StAR record values."""
    d = {
        "uuid": "VolumeUUID",
        "name": "RecordName",
        "user_id": "LocalUser",
        "user_dn": "GlobalUserName",
        "group_id": "LocalGroup",
        "fqan": "FQAN",
        "site_name": "SiteName",
        "capacity": "Capacity",
        "active_duration": "ActiveDuration",
        "measure_time_epoch": "CreateTime",
        "start_time_epoch": "StartTime",
        "storage_type": "Type",
        "status": "Status",
        "attached_to": "AttachedTo",
        "attached_duration": "AttachedDuration",
        "compute_service": "CloudComputeService",
        "cloud_type": "CloudType",
    }
    return d.get(field, field)


class StorageRecord(_BaseRecord):
    """The StorageRecord class holds information for each of the records.

    This class is versioned, following the Storage Accounting Definition on
    EMI StAR
    """

    version: str = pydantic.Field("0.1", exclude=True)

    uuid: m_uuid.UUID
    name: str

    user_id: str
    user_dn: typing.Optional[str] = None
    group_id: str
    fqan: str

    active_duration: int
    attached_duration: typing.Optional[float] = None
    attached_to: typing.Optional[str] = None

    # Make these fields private, and deal with them as properties. This is done as  all
    # the accounting infrastructure needs start and end times as integers, but it is
    # easier for us to maintain them as datetime objects internally.
    _measure_time: datetime.datetime
    _start_time: datetime.datetime

    storage_type: typing.Optional[str] = "Block Storage (cinder)"

    status: str
    capacity: int

    def __init__(
        self,
        start_time: datetime.datetime,
        measure_time: datetime.datetime,
        *args,
        **kwargs,
    ):
        """Initialize the record."""
        super(StorageRecord, self).__init__(*args, **kwargs)

        self._start_time = start_time
        self._measure_time = measure_time

    @property
    def start_time(self) -> datetime.datetime:
        """Get start time."""
        return self._start_time

    @pydantic.computed_field()  # type: ignore[misc]
    @property
    def start_time_epoch(self) -> int:
        """Get start time as epoch."""
        return int(self._start_time.timestamp())

    @start_time.setter
    def start_time(self, start_time: datetime.datetime) -> None:
        """Set start time."""
        self._start_time = start_time

    @property
    def measure_time(self) -> datetime.datetime:
        """Get measurement time."""
        return self._measure_time

    @pydantic.computed_field()  # type: ignore[misc]
    @property
    def measure_time_epoch(self) -> int:
        """Get measurement time as epoch."""
        return int(self._measure_time.timestamp())

    @measure_time.setter
    def measure_time(self, measure_time: datetime.datetime) -> None:
        """Set measurement time."""
        self._measure_time = measure_time

    def ssm_message(self):
        """Render record as the expected SSM message."""
        ns = {"xmlns:sr": "http://eu-emi.eu/namespaces/2011/02/storagerecord"}
        sr = ETree.Element("sr:StorageUsageRecord", attrib=ns)
        ETree.SubElement(
            sr,
            "sr:RecordIdentity",
            attrib={
                "sr:createTime": self.measure_time.isoformat(),
                "sr:recordId": str(self.uuid),
            },
        )
        ETree.SubElement(sr, "sr:StorageSystem").text = self.compute_service
        ETree.SubElement(sr, "sr:Site").text = self.site_name
        subject = ETree.SubElement(sr, "sr:SubjectIdentity")
        ETree.SubElement(subject, "sr:LocalUser").text = self.user_id
        ETree.SubElement(subject, "sr:LocalGroup").text = self.group_id
        if self.user_dn:
            ETree.SubElement(subject, "sr:UserIdentity").text = self.user_dn
        if self.fqan:
            ETree.SubElement(subject, "sr:Group").text = self.fqan
        ETree.SubElement(sr, "sr:StartTime").text = self.start_time.isoformat()
        ETree.SubElement(sr, "sr:EndTime").text = self.measure_time.isoformat()
        capacity = str(int(self.capacity * 1073741824))  # 1 GiB = 2^30
        ETree.SubElement(sr, "sr:ResourceCapacityUsed").text = capacity
        return ETree.tostring(sr)

    model_config = dict(
        alias_generator=map_storage_fields,
        populate_by_name=True,
        extra="forbid",
    )
