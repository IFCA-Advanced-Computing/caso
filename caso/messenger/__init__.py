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

"""Module containing the base class and manager for the cASO messengers."""

import abc
import typing

from oslo_config import cfg
from oslo_log import log
import six

import caso.record
from caso import loading

CONF = cfg.CONF

LOG = log.getLogger(__name__)

# Valid record types that can be configured
VALID_RECORD_TYPES = frozenset(["cloud", "ip", "accelerator", "storage", "energy"])

# Default record types for SSM messenger (records from default extractors)
# Default extractors are: nova, cinder, neutron
# nova -> CloudRecord, AcceleratorRecord
# cinder -> StorageRecord
# neutron -> IPRecord
DEFAULT_SSM_RECORD_TYPES = ["cloud", "ip", "accelerator", "storage"]


def get_messenger_opts(messenger_name: str) -> typing.List[cfg.Opt]:
    """Get the configuration options for a specific messenger.

    :param messenger_name: Name of the messenger.
    :returns: List of configuration options for the messenger.
    """
    # SSM messengers have a different default (only records from default extractors)
    if messenger_name in ("ssm", "ssmv4"):
        default_record_types = DEFAULT_SSM_RECORD_TYPES
    else:
        default_record_types = []

    return [
        cfg.ListOpt(
            "record_types",
            default=default_record_types,
            help="List of record types to publish to this messenger. "
            "Valid values are: cloud, ip, accelerator, storage, energy. "
            "If empty, all record types will be published. "
            f"Default for {messenger_name}: "
            f"{default_record_types if default_record_types else 'all record types'}.",
        ),
    ]


def register_messenger_opts(messenger_names: typing.Optional[typing.List[str]] = None):
    """Register configuration options for the specified messengers.

    :param messenger_names: List of messenger names to register options for.
                           If None, registers options for all available messengers.
    """
    if messenger_names is None:
        messenger_names = list(loading.get_available_messenger_names())

    for messenger_name in messenger_names:
        group_name = f"messenger_{messenger_name}"
        CONF.register_opts(get_messenger_opts(messenger_name), group=group_name)


# Mapping from record type names to record classes
RECORD_TYPE_MAP: typing.Dict[str, type] = {
    "cloud": caso.record.CloudRecord,
    "ip": caso.record.IPRecord,
    "accelerator": caso.record.AcceleratorRecord,
    "storage": caso.record.StorageRecord,
    "energy": caso.record.EnergyRecord,
}


@six.add_metaclass(abc.ABCMeta)
class BaseMessenger(object):
    """Base class for all messengers."""

    @abc.abstractmethod
    def push(self, records):
        """Push the records."""


def _filter_records(
    records: typing.List,
    record_types: typing.Optional[typing.List[str]],
) -> typing.List:
    """Filter records based on allowed record types.

    :param records: List of records to filter.
    :param record_types: List of allowed record type names. If None or empty,
                         all records are returned.
    :returns: Filtered list of records.
    """
    if not record_types:
        return records

    allowed_classes = tuple(
        RECORD_TYPE_MAP[rt] for rt in record_types if rt in RECORD_TYPE_MAP
    )
    if not allowed_classes:
        return records

    return [r for r in records if isinstance(r, allowed_classes)]


class Manager(object):
    """Manager for all cASO messengers."""

    def __init__(self):
        """Init the manager with all the configured messengers."""
        # Register messenger options for all configured messengers
        register_messenger_opts(CONF.messengers)

        try:
            self.mgr = loading.get_enabled_messengers(CONF.messengers)
        except Exception as e:
            # Capture exception so that we can continue working
            LOG.error(e)
            raise e

        # Build mapping of messenger name to allowed record types
        self.messenger_record_types: typing.Dict[
            str, typing.Optional[typing.List[str]]
        ] = {}
        for messenger_name in CONF.messengers:
            group_name = f"messenger_{messenger_name}"
            self.messenger_record_types[messenger_name] = None
            if hasattr(CONF, group_name):
                group = getattr(CONF, group_name)
                if hasattr(group, "record_types"):
                    record_types = group.record_types
                    if record_types:
                        self.messenger_record_types[messenger_name] = list(record_types)

    def push_to_all(self, records):
        """Push records to all the configured messengers."""
        try:
            for ext in self.mgr:
                messenger_name = ext.name
                record_types = self.messenger_record_types.get(messenger_name)
                filtered_records = _filter_records(records, record_types)
                if filtered_records:
                    ext.obj.push(filtered_records)
                else:
                    LOG.debug(
                        "No records to push to messenger %s "
                        "after filtering for record types: %s",
                        messenger_name,
                        record_types,
                    )
        except Exception as e:
            # Capture exception so that we can continue working
            LOG.error("Something happeneded when pushing records.")
            LOG.exception(e)
