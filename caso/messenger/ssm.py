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

"""Module containing the APEL SSM Messenger."""

import json
import typing
import warnings

# We are not parsing XML so this is safe
import xml.etree.ElementTree as ETree  # nosec

import dirq.QueueSimple
from oslo_config import cfg
from oslo_log import log

import caso.exception
import caso.messenger
import caso.record
from caso import utils

LOG = log.getLogger(__name__)

opts = [
    cfg.StrOpt(
        "output_path",
        default="/var/spool/apel/outgoing/openstack",
        help="Directory to put the generated SSM records.",
    ),
    cfg.IntOpt(
        "max_size", default=100, help="Maximum number of records to send per message"
    ),
]

CONF = cfg.CONF

CONF.register_opts(opts, group="ssm")


__all__ = ["SSMMessenger", "SSMMessengerV04"]


class SSMMessenger(caso.messenger.BaseMessenger):
    """SSM Messenger that pushes formatted messages to a dirq instance."""

    version_cloud = "0.4"
    version_ip = "0.2"
    version_accelerator = "0.1"
    version_storage = None  # FIXME: this cannot have a none version

    def __init__(self):
        """Initialize the SSM messenger with configured values."""
        try:
            utils.makedirs(CONF.ssm.output_path)
        except Exception as err:
            LOG.error(f"Failed to create path {CONF.ssm.output_path} because {err}")
            raise err
        self.queue = dirq.QueueSimple.QueueSimple(CONF.ssm.output_path)

    def _push_message_cloud(self, entries: typing.List[str]):
        """Push a compute message, formatted following the CloudRecord."""
        message = f"APEL-cloud-message: v{self.version_cloud}\n"
        aux = "\n%%\n".join(entries)
        message += f"{aux}\n"
        self.queue.add(message.encode("utf-8"))

    def _push_message_json(
        self,
        entries: typing.List[str],
        msg_type: str,
        version: str,
    ):
        """Push a JSON message with a UsageRecords list."""
        message = {
            "Type": msg_type,
            "Version": version,
            "UsageRecords": [json.loads(r) for r in entries],
        }
        self.queue.add(json.dumps(message))

    def _push_message_ip(self, entries: typing.List[str]):
        """Push an IP message."""
        self._push_message_json(entries, "APEL Public IP message", self.version_ip)

    def _push_message_accelerator(self, entries: typing.List[str]):
        """Push an accelerator message."""
        self._push_message_json(
            entries, "APEL-accelerator-message", self.version_accelerator
        )

    def _push_message_storage(self, entries):
        """Push a storage message."""
        ETree.register_namespace(
            "sr", "http://eu-emi.eu/namespaces/2011/02/storagerecord"
        )
        root = ETree.Element("sr:StorageUsageRecords")
        for record in entries:
            # We are not parsing XML so this is safe
            sr = ETree.fromstring(record)  # nosec
            root.append(sr)
        self.queue.add(ETree.tostring(root))

    def _push(self, entries_cloud, entries_ip, entries_accelerator, entries_storage):
        """Push all messages, dividing them into smaller chunks.

        This method gets lists of messages to be pushed in smaller chucks as per GGUS
        ticket 143436: https://ggus.eu/index.php?mode=ticket_info&ticket_id=143436
        """
        size = CONF.ssm.max_size
        for entries, push_message in (
            (entries_cloud, self._push_message_cloud),
            (entries_ip, self._push_message_ip),
            (entries_accelerator, self._push_message_accelerator),
            (entries_storage, self._push_message_storage),
        ):
            for i in range(0, len(entries), size):
                push_message(entries[i : i + size])  # noqa(E203)

    def push(self, records):
        """Push all records to SSM.

        This includes pushing the following records:
            - Cloud records
            - IP records
            - Accelerator records
            - Storage records

        This method will iterate over all the records, transforming them into the
        correct messages, then pushing it.
        """
        if not records:
            return

        # NOTE: the order of the keys must match the arguments of self._push()
        entries: typing.Dict[type, typing.List] = {
            caso.record.CloudRecord: [],
            caso.record.IPRecord: [],
            caso.record.AcceleratorRecord: [],
            caso.record.StorageRecord: [],
        }
        for record in records:
            bucket = entries.get(type(record))
            if bucket is None:
                raise caso.exception.CasoError("Unexpected record format!")
            bucket.append(record.ssm_message())

        self._push(*entries.values())


class SSMMessengerV04(SSMMessenger):
    """Deprecated versioned SSM Messenger."""

    def __init__(self):
        """Initialize the SSM V04 messenger.

        Deprecated not to be used, please stop using SSM versioned messengers.
        """
        msg = (
            "Using an versioned SSM messenger is deprecated, please use "
            "'ssm' as messenger instead in order to use the latest "
            "version."
        )
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        super(SSMMessengerV04, self).__init__()
