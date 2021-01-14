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
import six

from caso.extract import manager
from caso.tests import base


class TestCasoManager(base.TestCase):
    def setUp(self):
        super(TestCasoManager, self).setUp()
        self.flags(extractor="nova")
        self.p_extractor = mock.patch("caso.loading.get_available_extractors")
        self.p_extractor.return_value = {'nova': mock.MagicMock()}
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
            ret1, ret2 = self.manager.get_records()
            self.assertFalse(m.called)
        self.assertEqual({}, ret1)
        self.assertEqual({}, ret2)

    def test_extract(self):
        records = {uuid.uuid4().hex: None}
        ip_records = {uuid.uuid4().hex: None}
        self.flags(projects=["bazonk"])
        extract_from = "1999-12-19"
        extract_to = "2015-12-19"
        self.flags(extract_from=extract_from)
        self.flags(extract_to=extract_to)

        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch(builtins_open) as fopen, \
                mock.patch.object(self.manager.extractor,
                                  "extract_for_project") as m:

            aux = six.StringIO()
            fopen.return_value.__enter__ = lambda x: aux
            fopen.return_value.__exit__ = mock.Mock()

            m.return_value = [records, ip_records]
            ret1, ret2 = self.manager.get_records()
            m.assert_called_once_with(
                "bazonk",
                dateutil.parser.parse(extract_from),
                dateutil.parser.parse(extract_to)
            )
            fopen.assert_called_once_with(
                '/var/spool/caso/lastrun.bazonk',
                'w'
            )
        self.assertEqual(records, ret1)
        self.assertEqual(ip_records, ret2)

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
        records = {uuid.uuid4().hex: None}
        ip_records = {uuid.uuid4().hex: None}
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])
        lastrun = "1999-12-11"
        extract_to = "2015-12-19"
        self.flags(extract_to=extract_to)

        with mock.patch.object(self.manager.extractor,
                               "extract_for_project") as m, \
                mock.patch.object(self.manager, "get_lastrun") as m_lr:

            m_lr.return_value = lastrun
            m.return_value = [records, ip_records]

            ret1, ret2 = self.manager.get_records()

            m_lr.assert_called_once_with("bazonk")
            m.assert_called_once_with(
                "bazonk",
                dateutil.parser.parse(lastrun),
                dateutil.parser.parse(extract_to)
            )
        self.assertEqual(records, ret1)
        self.assertEqual(ip_records, ret2)

    def test_lastrun_exists(self):
        expected = datetime.datetime(2014, 12, 10, 13, 10, 26, 664598)
        aux = six.StringIO(str(expected))

        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch("os.path.exists") as path, \
                mock.patch(builtins_open) as fopen:
            fopen.return_value.__enter__ = lambda x: aux
            fopen.return_value.__exit__ = mock.Mock()
            path.return_value = True

            self.assertEqual(expected, self.manager.get_lastrun("foo"))

    def test_lastrun_is_invalid(self):
        aux = six.StringIO("foo")

        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch("os.path.exists") as path:
            with mock.patch(builtins_open) as fopen:
                fopen.return_value.__enter__ = lambda x: aux
                fopen.return_value.__exit__ = mock.Mock()
                path.return_value = True

                self.assertRaises(ValueError, self.manager.get_lastrun, "foo")
