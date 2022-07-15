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

"""
Tests for `caso.extract.manager` module.
"""

import datetime
import uuid

import dateutil.parser
from dateutil import tz
import mock
import six

from caso.extract import manager
from caso.tests import base


class TestCasoManager(base.TestCase):
    def setUp(self):
        super(TestCasoManager, self).setUp()
        self.flags(extractor="mock")
        self.p_extractors = mock.patch("caso.loading.get_available_extractors")
        patched = self.p_extractors.start()
        self.records = [{uuid.uuid4().hex: None}]
        self.m_extractor = mock.MagicMock()
        self.m_extractor.return_value.extract.return_value = self.records
        patched.return_value = {"mock": self.m_extractor}
        self.manager = manager.Manager()

    def tearDown(self):
        self.p_extractors.stop()
        self.reset_flags()

        super(TestCasoManager, self).tearDown()

    def test_extract_empty_projects(self):
        self.flags(projects=[])

        ret = self.manager.get_records()
        self.assertFalse(self.m_extractor.extract.called)
        self.assertEqual(ret, [])

    def test_extract(self):
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])
        extract_from = "1999-12-19"
        extract_to = "2015-12-19"
        self.flags(extract_from=extract_from)
        self.flags(extract_to=extract_to)

        ret = self.manager.get_records()
        self.m_extractor.assert_called_once_with(
            "bazonk",
        )
        self.m_extractor.return_value.extract.assert_called_once_with(
            dateutil.parser.parse(extract_from).replace(tzinfo=tz.tzutc()),
            dateutil.parser.parse(extract_to).replace(tzinfo=tz.tzutc())
        )
        self.assertEqual(self.records, ret)

    def test_get_records_wrong_extract_from(self):
        self.flags(projects=["foo"])
        self.flags(extract_from="1999-12-99")
        self.assertRaises(ValueError,
                          self.manager.get_records)

    def test_get_records_wrong_extract_to(self):
        self.flags(extract_to="1999-12-99")
        self.assertRaises(ValueError,
                          self.manager.get_records)

    def test_get_records_with_lastrun(self):
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])
        lastrun = "1999-12-11"
        extract_to = "2015-12-19"
        self.flags(extract_to=extract_to)

        with mock.patch.object(self.manager, "get_lastrun") as m:
            m.return_value = lastrun

            ret = self.manager.get_records()

            m.assert_called_once_with("bazonk")
            self.m_extractor.assert_called_once_with(
                "bazonk",
            )
            self.m_extractor.return_value.extract.assert_called_once_with(
                dateutil.parser.parse(lastrun).replace(tzinfo=tz.tzutc()),
                dateutil.parser.parse(extract_to).replace(tzinfo=tz.tzutc())
            )
        self.assertEqual(self.records, ret)

    def test_lastrun_exists(self):
        expected = datetime.datetime(2014, 12, 10, 13, 10, 26, 664598)
        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        fopen = mock.mock_open(read_data=str(expected))
        with mock.patch("os.path.exists") as path:
            with mock.patch(builtins_open, fopen):
                path.return_value = True
                self.assertEqual(expected, self.manager.get_lastrun("foo"))

    def test_lastrun_is_invalid(self):
        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'
        fopen = mock.mock_open(read_data="foo")
        with mock.patch("os.path.exists") as path:
            with mock.patch(builtins_open, fopen):
                path.return_value = True
                self.assertRaises(ValueError, self.manager.get_lastrun, "foo")

    def test_write_lastrun_dry_run(self):
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])

        with mock.patch.object(self.manager, "write_lastrun") as m:
            self.manager.get_records()
            m.assert_called_once_with("bazonk")

    def test_write_lastrun(self):
        self.flags(projects=["bazonk"])
        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch(builtins_open, mock.mock_open()) as m:
            self.manager.get_records()
            m.assert_called_once_with("/var/spool/caso/lastrun.bazonk", "w")
