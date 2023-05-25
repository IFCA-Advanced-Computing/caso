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

import datetime
import json
import typing
import warnings

# We are not parsing XML so this is safe
import xml.etree.ElementTree as ETree  # nosec

import dirq.QueueSimple
from oslo_config import cfg
from oslo_log import log
import six

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

    def _push_message_cloud(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        """Push a compute message, formatted following the CloudRecord."""
        message = f"APEL-cloud-message: v{self.version_cloud}\n"
        aux = "\n%%\n".join(entries)
        message += f"{aux}\n"
        queue.add(message.encode("utf-8"))

    def _push_message_json(
        self,
        queue: dirq.QueueSimple.QueueSimple,
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
        queue.add(json.dumps(message))

    def _push_message_ip(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        """Push an IP message."""
        self._push_message_json(
            queue, entries, "APEL Public IP message", self.version_ip
        )

    def _push_message_accelerator(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        """Push an accelerator message."""
        self._push_message_json(
            queue, entries, "APEL-accelerator-message", self.version_accelerator
        )

    def _push_message_storage(self, queue, entries):
        """Push a storage message."""
        ns = {"xmlns:sr": "http://eu-emi.eu/namespaces/2011/02/storagerecord"}
        root = ETree.Element("sr:StorageUsageRecords", attrib=ns)
        for record in entries:
            sr = ETree.SubElement(root, "sr:StorageUsageRecord")
            ETree.SubElement(
                sr,
                "sr:RecordIdentity",
                attrib={
                    "sr:createTime": record.measure_time.isoformat(),
                    "sr:recordId": str(record.uuid),
                },
            )
            ETree.SubElement(sr, "sr:StorageSystem").text = record.compute_service
            ETree.SubElement(sr, "sr:Site").text = record.site_name
            subject = ETree.SubElement(sr, "sr:SubjectIdentity")
            ETree.SubElement(subject, "sr:LocalUser").text = record.user_id
            ETree.SubElement(subject, "sr:LocalGroup").text = record.group_id
            if record.user_dn:
                ETree.SubElement(subject, "sr:UserIdentity").text = record.user_dn
            if record.fqan:
                ETree.SubElement(subject, "sr:Group").text = record.fqan
            ETree.SubElement(sr, "sr:StartTime").text = record.start_time.isoformat()
            ETree.SubElement(sr, "sr:EndTime").text = record.measure_time.isoformat()
            capacity = str(int(record.capacity * 1073741824))  # 1 GiB = 2^30
            ETree.SubElement(sr, "sr:ResourceCapacityUsed").text = capacity
        queue.add(ETree.tostring(root))

    def _push(self, entries_cloud, entries_ip, entries_accelerator, entries_storage):
        """Push all messages, dividing them into smaller chunks.

        This method gets lists of messages to be pushed in smaller chucks as per GGUS
        ticket 143436: https://ggus.eu/index.php?mode=ticket_info&ticket_id=143436
        """
        queue = dirq.QueueSimple.QueueSimple(CONF.ssm.output_path)

        for i in range(0, len(entries_cloud), CONF.ssm.max_size):
            entries = entries_cloud[i : i + CONF.ssm.max_size]  # noqa(E203)
            self._push_message_cloud(queue, entries)

        for i in range(0, len(entries_ip), CONF.ssm.max_size):
            entries = entries_ip[i : i + CONF.ssm.max_size]  # noqa(E203)
            self._push_message_ip(queue, entries)

        for i in range(0, len(entries_accelerator), CONF.ssm.max_size):
            entries = entries_accelerator[i : i + CONF.ssm.max_size]  # noqa(E203)
            self._push_message_accelerator(queue, entries)

        for i in range(0, len(entries_storage), CONF.ssm.max_size):
            entries = entries_storage[i : i + CONF.ssm.max_size]  # noqa(E203)
            self._push_message_storage(queue, entries)

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

        entries_cloud = []
        entries_ip = []
        entries_accelerator = []
        entries_storage = []
        opts = {
            "by_alias": True,
            "exclude_unset": True,
            "exclude_none": True,
        }
        for record in records:
            if isinstance(record, caso.record.CloudRecord):
                aux = []
                for k, v in six.iteritems(record.dict(**opts)):
                    if v is not None:
                        # FIXME(aloga): to be handled at record level.
                        if isinstance(v, datetime.datetime):
                            aux.append(f"{k}: {int(v.timestamp())}")
                        else:
                            aux.append(f"{k}: {v}")
                entries_cloud.append("\n".join(aux))
            elif isinstance(record, caso.record.IPRecord):
                entries_ip.append(record.json(**opts))
            elif isinstance(record, caso.record.AcceleratorRecord):
                entries_accelerator.append(record.json(**opts))
            elif isinstance(record, caso.record.StorageRecord):
                entries_storage.append(record)
            else:
                raise caso.exception.CasoError("Unexpected record format!")

        self._push(entries_cloud, entries_ip, entries_accelerator, entries_storage)


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
        warnings.warn(msg, DeprecationWarning)
        super(SSMMessengerV04, self).__init__()
