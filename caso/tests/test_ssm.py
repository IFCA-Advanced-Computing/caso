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

"""Test for SSM messenger."""

import pytest

import caso.exception
from caso.messenger import ssm


def test_empty_records_does_nothing(monkeypatch):
    """Test that empty records do nothing."""
    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        assert messenger.push([]) is None


def test_weird_record_raises(monkeypatch):
    """Test that empty records do nothing."""
    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        with pytest.raises(caso.exception.CasoError):
            messenger.push([None, "gfaga"])


def test_cloud_records_pushed(monkeypatch, cloud_record_list, expected_entries_cloud):
    """Test that cloud records are correctly rendered."""

    def mock_push(entries_cloud, entries_ip, entries_accelerator, entries_storage):
        assert set(entries_cloud) == set(expected_entries_cloud)

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        m.setattr(messenger, "_push", mock_push)
        messenger.push(cloud_record_list)


def test_ip_records_pushed(monkeypatch, ip_record_list, expected_entries_ip):
    """Test that IP records are correctly rendered."""

    def mock_push(entries_cloud, entries_ip, entries_accelerator, entries_storage):
        assert set(entries_ip) == set(expected_entries_ip)

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        m.setattr(messenger, "_push", mock_push)
        messenger.push(ip_record_list)


def test_accelerator_records_pushed(
    monkeypatch, accelerator_record_list, expected_entries_accelerator
):
    """Test that Accelerator records are correctly rendered."""

    def mock_push(entries_cloud, entries_ip, entries_accelerator, entries_storage):
        import pprint

        pprint.pprint(entries_accelerator)
        assert set(entries_accelerator) == set(expected_entries_accelerator)

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        m.setattr(messenger, "_push", mock_push)
        messenger.push(accelerator_record_list)


def test_cloud_ip_records_pushed(
    monkeypatch,
    cloud_record_list,
    expected_entries_cloud,
    ip_record_list,
    expected_entries_ip,
):
    """Test that cloud and IP records are correctly rendered."""

    def mock_push(entries_cloud, entries_ip, entries_accelerator, entries_storage):
        assert set(entries_cloud) == set(expected_entries_cloud)
        assert set(entries_ip) == set(expected_entries_ip)

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: None)
        messenger = ssm.SSMMessenger()

        m.setattr(messenger, "_push", mock_push)
        messenger.push(cloud_record_list + ip_record_list)


class _MockQueue:
    @staticmethod
    def add(message):
        """Add a message to the fake queue."""
        pass


def test_complete_cloud_message(
    monkeypatch, expected_entries_cloud, expected_message_cloud
):
    """Test a complete cloud message."""

    def mock_add(message):
        assert message == expected_message_cloud

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: _MockQueue())
        messenger = ssm.SSMMessenger()

        m.setattr(messenger.queue, "add", mock_add)
        messenger._push_message_cloud(expected_entries_cloud)


def test_complete_ip_message(monkeypatch, expected_entries_ip, expected_message_ip):
    """Test a complete cloud message."""

    def mock_add(message):
        print(message)
        print(expected_message_ip)
        assert message == expected_message_ip

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: _MockQueue())
        messenger = ssm.SSMMessenger()

        m.setattr(messenger.queue, "add", mock_add)
        messenger._push_message_ip(expected_entries_ip)


def test_complete_accelerator_message(
    monkeypatch, expected_entries_accelerator, expected_message_accelerator
):
    """Test a complete cloud message."""

    def mock_add(message):
        print(message)
        print(expected_message_accelerator)
        assert message == expected_message_accelerator

    with monkeypatch.context() as m:
        m.setattr("caso.utils.makedirs", lambda x: None)
        m.setattr("dirq.QueueSimple.QueueSimple", lambda x: _MockQueue())
        messenger = ssm.SSMMessenger()

        m.setattr(messenger.queue, "add", mock_add)
        messenger._push_message_accelerator(expected_entries_accelerator)
