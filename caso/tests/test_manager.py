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
Tests for `caso.manager` module.
"""

import datetime

from dateutil import tz
import mock
from oslo_concurrency.fixture import lockutils as lock_fixture
import six

from caso import manager
from caso.tests import base


class TestCasoManager(base.TestCase):

    REQUIRES_LOCKING = True

    def setUp(self):
        self.useFixture(lock_fixture.ExternalLockFixture())
        super(TestCasoManager, self).setUp()
        self.patchers = {
            "makedirs": mock.patch('caso.utils.makedirs'),
            "extract": mock.patch('caso.extract.manager.Manager'),
            "messenger": mock.patch('caso.messenger.Manager'),
        }
        self.mocks = {}
        for k, p in six.iteritems(self.patchers):
            self.mocks[k] = p.start()

        self.manager = manager.Manager()

    def tearDown(self):
        for p in self.patchers.values():
            p.stop()

        super(TestCasoManager, self).tearDown()

    def test_lastrun_does_not_exist(self):
        self.manager.last_run_file = "foobarbarz/does/not/exist"
        expected = datetime.datetime(1970, 1, 1, 0, 0)
        self.assertEqual(expected, self.manager.lastrun)

    def test_lastrun_exists(self):
        expected = datetime.datetime(2014, 12, 10, 13, 10, 26, 664598)
        aux = six.StringIO(str(expected))

        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch("os.path.exists") as path:
            with mock.patch(builtins_open) as fopen:
                fopen.return_value.__enter__ = lambda x: aux
                fopen.return_value.__exit__ = mock.Mock()
                path.return_value = True

                self.assertEqual(expected, self.manager.lastrun)

    def test_lastrun_is_invalid(self):
        aux = six.StringIO("foo")

        # NOTE(aloga): manager.lastrun is a property, so we need to
        # create our own callable here.
        def call(self):
            return self.manager.lastrun

        if six.PY3:
            builtins_open = 'builtins.open'
        else:
            builtins_open = '__builtin__.open'

        with mock.patch("os.path.exists") as path:
            with mock.patch(builtins_open) as fopen:
                fopen.return_value.__enter__ = lambda x: aux
                fopen.return_value.__exit__ = mock.Mock()
                path.return_value = True

                self.assertRaises(ValueError, call, self)

    def test_dry_run(self):
        self.flags(dry_run=True)
        # NOTE(aloga): cannot patch a property of an instance, see
        # https://code.google.com/p/mock/issues/detail?id=117
        with mock.patch("caso.manager.Manager.lastrun",
                        new_callable=mock.PropertyMock) as lastrun:
            lastrun.return_value = datetime.datetime.now(tz.tzutc())
            mngr = manager.Manager()
            mngr.messenger.push_to_all.assert_not_called()
            mngr.run()
            self.assertFalse(mngr.messenger.push_to_all.called)
