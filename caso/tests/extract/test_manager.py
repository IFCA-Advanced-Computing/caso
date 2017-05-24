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
import mock

from caso.extract import manager
from caso.tests import base


class TestCasoManager(base.TestCase):
    def setUp(self):
        super(TestCasoManager, self).setUp()
        manager.SUPPORTED_EXTRACTORS = {"nova": "foo.Bar"}
        self.flags(extractor="nova")
        self.p_extractor = mock.patch.dict('sys.modules',
                                           {'foo': mock.MagicMock()})
        self.p_extractor.start()
        self.manager = manager.Manager()

    def tearDown(self):
        self.p_extractor.stop()
        self.reset_flags()

        super(TestCasoManager, self).tearDown()

    def test_extract_empty_projects(self):
        self.flags(projects=[])

        with mock.patch.object(self.manager.extractor,
                               "extract_for_project") as m:
            self.manager._extract("1999-12-19", "2015-10-23")
            self.assertFalse(m.called)
        self.assertEqual({}, self.manager.records)

    def test_extract(self):
        records = {uuid.uuid4().hex: None}
        self.flags(projects=["bazonk"])

        with mock.patch.object(self.manager.extractor,
                               "extract_for_project") as m:
            m.return_value = records
            self.manager._extract("1999-12-19", "2015-12-19")
            m.assert_called_once_with("bazonk", "1999-12-19", "2015-12-19")
        self.assertEqual(records, self.manager.records)

    def test_get_records_wrong_extract_from(self):
        self.flags(extract_from="1999-12-99")
        self.assertRaises(ValueError,
                          self.manager.get_records)

    def test_get_records_wrong_extract_to(self):
        self.flags(extract_to="1999-12-99")
        self.assertRaises(ValueError,
                          self.manager.get_records)

    def test_get_records_wrong_lastrun(self):
        self.assertRaises(ValueError,
                          self.manager.get_records,
                          lastrun="1999-12-99")

    def test_get_records_with_extract_from_and_to(self):
        date = "1999-12-11"
        end_date = "2015-12-11"
        dt = dateutil.parser.parse(date)
        parsed_end_date = dateutil.parser.parse(end_date)
        self.flags(extract_from=date, extract_to=end_date)

        with mock.patch.object(self.manager, "_extract") as m:
            self.manager.get_records()
            m.assert_called_with(dt, parsed_end_date)

    def test_get_records_with_lastrun(self):
        date = "1999-12-11"

        dt = dateutil.parser.parse(date)
        mock_now = datetime.datetime(2016, 4, 19, 15, 4, 14, 468060)

        with mock.patch.object(self.manager, "_extract") as m:
            with mock.patch('caso.extract.manager.datetime') as MockDatetime:
                MockDatetime.datetime.utcnow.return_value = mock_now

                self.manager.get_records(lastrun=date)
                m.assert_called_with(dt, mock_now)
