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

import socket

from oslo_config import cfg
from oslo_log import log
import six

from caso import exception
import caso.messenger


opts = [
    cfg.StrOpt('host',
               default="localhost",
               help='Logstash host to send records to.'),
    cfg.IntOpt('port',
               default=5000,
               help='Logstash server port.'),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="logstash")

LOG = log.getLogger(__name__)


class LogstashMessenger(caso.messenger.BaseMessenger):
    """Format and send records to a logstash host."""

    def __init__(self, host=CONF.logstash.host, port=CONF.logstash.port):
        super(LogstashMessenger, self).__init__()
        self.host = CONF.logstash.host
        self.port = CONF.logstash.port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def push(self, records):
        """Push records to logstash using tcp."""
        try:
            self.sock.connect((self.host, self.port))
            for _, record in six.iteritems(records):
                self.sock.sendall(record.as_json() + "\n")
        except socket.error as e:
            raise exception.LogstashConnectionError(host=self.host,
                                                    port=self.port,
                                                    exception=e)
        else:
            LOG.info("Sent %d records to logstash %s:%s" %
                     (len(records), self.host, self.port))
        finally:
            self.sock.close()
