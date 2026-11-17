# -*- coding: utf-8 -*-

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

"""Tests for the Logstash messenger."""

import json
import socket
from unittest import mock

import pytest

from caso import exception
from caso.messenger import logstash


def test_push_sends_one_json_line_per_record(cloud_record, ip_record):
    """Each record must be sent as a JSON document followed by a newline."""
    messenger = logstash.LogstashMessenger(host="example.org", port=1234)

    with mock.patch("socket.create_connection") as m_conn:
        sock = m_conn.return_value.__enter__.return_value
        messenger.push([cloud_record, ip_record])

    m_conn.assert_called_once_with(("example.org", 1234))
    assert sock.sendall.call_count == 2
    for call in sock.sendall.call_args_list:
        payload = call.args[0]
        assert isinstance(payload, bytes)
        assert payload.endswith(b"\n")
        json.loads(payload)


def test_push_raises_on_connection_error(cloud_record):
    """Connection errors must be wrapped in a cASO exception."""
    messenger = logstash.LogstashMessenger(host="example.org", port=1234)

    with mock.patch("socket.create_connection", side_effect=socket.error("boom")):
        with pytest.raises(exception.LogstashConnectionError):
            messenger.push([cloud_record])
