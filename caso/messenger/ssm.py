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
import json
import warnings

import dirq.QueueSimple
from oslo_config import cfg
from oslo_log import log
import six

import caso.messenger
import caso.record
from caso import utils

LOG = log.getLogger(__name__)

opts = [
    cfg.StrOpt('output_path',
               default='/var/spool/apel/outgoing/openstack',
               help="Directory to put the generated SSM records."),
    cfg.IntOpt('max_size',
               default=100,
               help="Maximum number of records to send per message"),
]

CONF = cfg.CONF

CONF.register_opts(opts, group="ssm")


__all__ = ["SsmMessenger", "SSMMessengerV02", "SSMMessengerV04"]


@six.add_metaclass(abc.ABCMeta)
class _SSMBaseMessenger(caso.messenger.BaseMessenger):
    compute_version = None
    ip_version = None

    def __init__(self):
        # FIXME(aloga): try except here
        utils.makedirs(CONF.ssm.output_path)

    def push_compute_message(self, queue, entries):
        message = f"APEL-cloud-message: v{self.compute_version}\n"
        aux = "%%\n".join(entries)
        message += f"{aux}\n"
        queue.add(message)

    def push_ip_message(self, queue, entries):
        message = {
            "Type": "APEL Public IP message",
            "Version": self.ip_version,
            "UsageRecords": entries,
        }
        queue.add(json.dumps(message))

    def push(self, records):
        if not records:
            return

        entries_cloud = []
        entries_ip = []
        for _, record in six.iteritems(records):
            if isinstance(record, caso.record.CloudRecord):
                aux = ""
                for k, v in six.iteritems(record.as_dict(
                                          version=self.compute_version)):
                    if v is not None:
                        aux += "%s: %s\n" % (k, v)
                entries_cloud.append(aux)
            else:
                entries_ip.append(record.as_dict(version=self.ip_version))

        # FIXME(aloga): try except here
        queue = dirq.QueueSimple.QueueSimple(CONF.ssm.output_path)

        # Divide message into smaller chunks as per GGUS #143436
        # https://ggus.eu/index.php?mode=ticket_info&ticket_id=143436
        for i in range(0, len(entries_cloud), CONF.ssm.max_size):
            entries = entries_cloud[i:i + CONF.ssm.max_size]
            self.push_compute_message(queue, entries)

        for i in range(0, len(entries_ip), CONF.ssm.max_size):
            entries = entries_ip[i:i + CONF.ssm.max_size]
            self.push_ip_message(queue, entries)


class SSMMessengerV02(_SSMBaseMessenger):
    compute_version = "0.2"


class SSMMessengerV04(_SSMBaseMessenger):
    compute_version = "0.4"
    ip_version = "0.2"


class SsmMessenger(SSMMessengerV02):
    def __init__(self):
        msg = ("Using deprecated caso.messenger.ssm.SsmMessager, "
               "please use caso.messenger.ssm.SSMMessengerV02 if you "
               "wish to continue usinf the 0.2 version of the record, "
               "or refer to the cASO documentation.")
        warnings.warn(msg, DeprecationWarning)
        super(SsmMessenger, self).__init__()
