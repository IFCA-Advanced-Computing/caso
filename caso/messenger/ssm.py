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
    compute_version = "0.4"
    ip_version = "0.2"
    acc_version = "0.1"
    str_version = None  # FIXME: this cannot have a none version

    def __init__(self):
        # FIXME(aloga): try except here
        utils.makedirs(CONF.ssm.output_path)

    def push_compute_message(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        message = f"APEL-cloud-message: v{self.compute_version}\n"
        aux = "%%\n".join(entries)
        message += f"{aux}\n"
        queue.add(message.encode("utf-8"))

    def push_json_message(
        self,
        queue: dirq.QueueSimple.QueueSimple,
        entries: typing.List[str],
        msg_type: str,
        version: str,
    ):
        message = {
            "Type": msg_type,
            "Version": version,
            "UsageRecords": [json.loads(r) for r in entries],
        }
        queue.add(json.dumps(message))

    def push_ip_message(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        self.push_json_message(
            queue, entries, "APEL Public IP message", self.ip_version
        )

    def push_acc_message(
        self, queue: dirq.QueueSimple.QueueSimple, entries: typing.List[str]
    ):
        self.push_json_message(
            queue, entries, "APEL-accelerator-message", self.acc_version
        )

    def push_str_message(self, queue, entries):
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

    def push(self, records):
        if not records:
            return

        entries_cloud = []
        entries_ip = []
        entries_acc = []
        entries_str = []
        opts = {
            "by_alias": True,
            "exclude_unset": True,
            "exclude_none": True,
        }
        for record in records:
            if isinstance(record, caso.record.CloudRecord):
                aux = ""
                for k, v in six.iteritems(record.dict(**opts)):
                    if v is not None:
                        aux += f"{k}: {v}\n"
                entries_cloud.append(aux)
            elif isinstance(record, caso.record.IPRecord):
                entries_ip.append(record.json(**opts))
            elif isinstance(record, caso.record.AcceleratorRecord):
                entries_acc.append(record.json(**opts))
            elif isinstance(record, caso.record.StorageRecord):
                entries_str.append(record)
            else:
                raise caso.exception.CasoError("Unexpected record format!")

        # FIXME(aloga): try except here
        queue = dirq.QueueSimple.QueueSimple(CONF.ssm.output_path)

        # Divide message into smaller chunks as per GGUS #143436
        # https://ggus.eu/index.php?mode=ticket_info&ticket_id=143436
        for i in range(0, len(entries_cloud), CONF.ssm.max_size):
            entries = entries_cloud[i : i + CONF.ssm.max_size]
            self.push_compute_message(queue, entries)

        for i in range(0, len(entries_ip), CONF.ssm.max_size):
            entries = entries_ip[i : i + CONF.ssm.max_size]
            self.push_ip_message(queue, entries)

        for i in range(0, len(entries_acc), CONF.ssm.max_size):
            entries = entries_acc[i : i + CONF.ssm.max_size]
            self.push_acc_message(queue, entries)

        for i in range(0, len(entries_str), CONF.ssm.max_size):
            entries = entries_str[i : i + CONF.ssm.max_size]
            self.push_str_message(queue, entries)


class SSMMessengerV04(SSMMessenger):
    def __init__(self):
        msg = (
            "Using an versioned SSM messenger is deprecated, please use "
            "'ssm' as messenger instead in order to use the latest "
            "version."
        )
        warnings.warn(msg, DeprecationWarning)
        super(SSMMessengerV04, self).__init__()
