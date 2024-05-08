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

"""Tests for the OpenStack nova extractor."""

from caso.extract.openstack import nova

import unittest


class TestCasoManager(unittest.TestCase):
    """Test case for Nova extractor."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCasoManager, self).setUp()
        self.flags(mapping_file="etc/caso/voms.json.sample")
        self.extractor = nova.NovaExtractor()

    def tearDown(self):
        """Run after each test, reset state and environment."""
        self.reset_flags()

        super(TestCasoManager, self).tearDown()
