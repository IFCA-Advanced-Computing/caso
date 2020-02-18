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
