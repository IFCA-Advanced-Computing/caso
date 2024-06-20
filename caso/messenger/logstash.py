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

"""Module containing a Logstask cASO messenger."""

import socket

from oslo_config import cfg
from oslo_log import log
import six

from caso import exception
import caso.messenger
#add json lib
import json
#add datetime lib
import datetime

opts = [
    cfg.StrOpt("host", default="localhost", help="Logstash host to send records to."),
    cfg.IntOpt("port", default=5000, help="Logstash server port."),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="logstash")

LOG = log.getLogger(__name__)


class LogstashMessenger(caso.messenger.BaseMessenger):
    """Format and send records to a logstash host."""

    def __init__(self, host=CONF.logstash.host, port=CONF.logstash.port):
        """Get a logstash messenger for a given host and port."""
        super(LogstashMessenger, self).__init__()
        self.host = CONF.logstash.host
        self.port = CONF.logstash.port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def push(self, records):

        # NOTE(acostantini): code for the serialization and push of the
        # records in logstash. JSON format to be used and encoding UTF-8
        """Serialization of records to be sent to logstash"""
        if not records:
            return

        #Actual timestamp to be added on each record       
        cdt = datetime.datetime.now()
        ct = int(datetime.datetime.now().timestamp())

        #Open the connection with LS
        self.sock.connect((self.host, self.port))

        """Push records to logstash using tcp."""
        try:
          for record in records:
        #serialization of record
              rec=record.serialization_message()
        #cASO timestamp added to each record
              rec['caso-timestamp']=ct
        #Send the record to LS
              self.sock.send((json.dumps(rec)+'\n').encode('utf-8'))
        except socket.error as e:
            raise exception.LogstashConnectionError(
                host=self.host, port=self.port, exception=e
            )
        else:
            LOG.info(
                "Sent {} records to logstash {}:{}".format(
                    len(records), self.host, self.port
                )
            )
        finally:
            self.sock.close()
