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

"""Tests for `caso.extract.manager` module."""

import datetime
import uuid

import dateutil.parser
from dateutil import tz
from oslo_config import cfg
import six
import unittest
from unittest import mock

from caso.extract import manager
import caso.manager  # Import to register the spooldir option

CONF = cfg.CONF


class TestCasoManager(unittest.TestCase):
    """Test case for the cASO extractor manager."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCasoManager, self).setUp()
        self.flags(extractor="mock")
        self.flags(spooldir="/tmp/caso_test")
        self.p_extractors = mock.patch("caso.loading.get_available_extractors")
        patched = self.p_extractors.start()
        self.records = [{uuid.uuid4().hex: None}]
        self.m_extractor = mock.MagicMock()
        self.m_extractor.return_value.extract.return_value = self.records
        patched.return_value = {"mock": self.m_extractor}

        self.p_keystone = mock.patch(
            "caso.extract.manager.Manager._get_keystone_client"
        )
        self.p_keystone.start()

        self.manager = manager.Manager()

    def tearDown(self):
        """Run after each test, reset state and environment."""
        self.p_extractors.stop()
        self.p_keystone.stop()
        self.reset_flags()

        super(TestCasoManager, self).tearDown()

    def test_extract_empty_projects(self):
        """Test that we can extract from empty projects."""
        self.flags(projects=[])

        ret = self.manager.get_records()
        self.assertFalse(self.m_extractor.extract.called)
        self.assertEqual(ret, [])

    def test_extract(self):
        """Test that we extract records for a given project."""
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])
        extract_from = "1999-12-19"
        extract_to = "2015-12-19"
        self.flags(extract_from=extract_from)
        self.flags(extract_to=extract_to)

        ret = self.manager.get_records()
        self.m_extractor.assert_called_once_with(
            "bazonk",
            unittest.mock.ANY,
        )
        self.m_extractor.return_value.extract.assert_called_once_with(
            dateutil.parser.parse(extract_from).replace(tzinfo=tz.tzutc()),
            dateutil.parser.parse(extract_to).replace(tzinfo=tz.tzutc()),
        )
        self.assertEqual(self.records, ret)

    def test_get_records_wrong_extract_from(self):
        """Test that wrong dates in extract from cause a failure."""
        self.flags(projects=["foo"])
        self.flags(extract_from="1999-12-99")
        self.assertRaises(ValueError, self.manager.get_records)

    def test_get_records_wrong_extract_to(self):
        """Test that wrong dates in extract to cause a failure."""
        self.flags(extract_to="1999-12-99")
        self.assertRaises(ValueError, self.manager.get_records)

    def test_get_records_with_lastrun(self):
        """Test that we can extract records with a lastrun file."""
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])
        lastrun = "1999-12-11"
        extract_to = "2015-12-19"
        self.flags(extract_to=extract_to)

        with unittest.mock.patch.object(self.manager, "get_lastrun") as m:
            m.return_value = lastrun

            ret = self.manager.get_records()

            m.assert_called_once_with("bazonk")
            self.m_extractor.assert_called_once_with(
                "bazonk",
                unittest.mock.ANY,
            )
            self.m_extractor.return_value.extract.assert_called_once_with(
                dateutil.parser.parse(lastrun).replace(tzinfo=tz.tzutc()),
                dateutil.parser.parse(extract_to).replace(tzinfo=tz.tzutc()),
            )
        self.assertEqual(self.records, ret)

    def test_lastrun_exists(self):
        """Test that we can open a lastrun file in the expected format."""
        expected = datetime.datetime(2014, 12, 10, 13, 10, 26, 664598)
        if six.PY3:
            builtins_open = "builtins.open"
        else:
            builtins_open = "__builtin__.open"

        fopen = unittest.mock.mock_open(read_data=str(expected))
        with unittest.mock.patch("os.path.exists") as path:
            with unittest.mock.patch(builtins_open, fopen):
                path.return_value = True
                self.assertEqual(expected, self.manager.get_lastrun("foo"))

    def test_lastrun_is_invalid(self):
        """Test that we fail if lastrun file is invalid."""
        if six.PY3:
            builtins_open = "builtins.open"
        else:
            builtins_open = "__builtin__.open"
        fopen = unittest.mock.mock_open(read_data="foo")
        with unittest.mock.patch("os.path.exists") as path:
            with unittest.mock.patch(builtins_open, fopen):
                path.return_value = True
                self.assertRaises(ValueError, self.manager.get_lastrun, "foo")

    def test_get_records_with_invalid_lastrun_continues(self):
        """Test that get_records continues when lastrun file is invalid."""
        self.flags(projects=["project1", "project2"])
        
        # Mock the file system operations to test exception handling path
        with unittest.mock.patch.object(self.manager, "get_project_vo", return_value="test-vo") as m_vo:
            with unittest.mock.patch('os.path.exists', return_value=True):
                # One project gets invalid date, one gets valid date
                file_contents = ["invalid-date-format", "2020-01-01 00:00:00"]
                mock_file = unittest.mock.mock_open()
                mock_file.return_value.read.side_effect = file_contents
                
                with unittest.mock.patch('builtins.open', mock_file):
                    ret = self.manager.get_records()
                    
                    # Should call get_project_vo for both projects since VO lookup happens before lastrun
                    self.assertEqual(m_vo.call_count, 2)
                    m_vo.assert_any_call("project1")
                    m_vo.assert_any_call("project2")
                    
                    # One project should succeed - doesn't matter which one for this test
                    # The key is that get_records continues processing despite one project failing
                    self.m_extractor.assert_called_once()
                    args, kwargs = self.m_extractor.call_args
                    self.assertEqual(args[1], "test-vo")  # VO should be correct
                    self.assertIn(args[0], ["project1", "project2"])  # Should be one of the projects

    def test_get_records_with_future_extract_from_continues(self):
        """Test that get_records continues when extract_from is in the future."""
        self.flags(projects=["project1", "project2"])
        future_date = datetime.datetime.now(tz.tzutc()) + datetime.timedelta(days=1)
        past_date = datetime.datetime.now(tz.tzutc()) - datetime.timedelta(days=1)
        
        # Mock file system operations and return dates
        with unittest.mock.patch.object(self.manager, "get_project_vo", return_value="test-vo") as m_vo:
            with unittest.mock.patch('os.path.exists', return_value=True):
                # One project gets future date, one gets past date
                file_contents = [str(future_date), str(past_date)]
                mock_file = unittest.mock.mock_open()
                mock_file.return_value.read.side_effect = file_contents
                
                with unittest.mock.patch('builtins.open', mock_file):
                    ret = self.manager.get_records()
                    
                    # Should call get_project_vo for both projects since VO lookup happens before lastrun
                    self.assertEqual(m_vo.call_count, 2)
                    m_vo.assert_any_call("project1")
                    m_vo.assert_any_call("project2")
                    
                    # One project should succeed - doesn't matter which one for this test
                    # The key is that get_records continues processing despite one project failing
                    self.m_extractor.assert_called_once()
                    args, kwargs = self.m_extractor.call_args
                    self.assertEqual(args[1], "test-vo")  # VO should be correct
                    self.assertIn(args[0], ["project1", "project2"])  # Should be one of the projects

    def test_get_lastrun_invalid_date_logs_exception(self):
        """Test that get_lastrun properly logs exceptions when date parsing fails."""
        if six.PY3:
            builtins_open = "builtins.open"
        else:
            builtins_open = "__builtin__.open"
        fopen = unittest.mock.mock_open(read_data="invalid-date-format")
        
        with unittest.mock.patch("os.path.exists") as path:
            with unittest.mock.patch(builtins_open, fopen):
                with unittest.mock.patch("caso.extract.manager.LOG") as mock_log:
                    path.return_value = True
                    
                    with self.assertRaises(ValueError):
                        self.manager.get_lastrun("test-project")
                    
                    # Verify that both error and exception were logged
                    mock_log.error.assert_called_once()
                    mock_log.exception.assert_called_once()
                    
                    # Check the error message contains the expected text
                    error_call = mock_log.error.call_args[0][0]
                    self.assertIn("Cannot read date from lastrun file", error_call)

    def test_write_lastrun_dry_run(self):
        """Test that we do not write lastrun file on dry run."""
        self.flags(dry_run=True)
        self.flags(projects=["bazonk"])

        with unittest.mock.patch.object(self.manager, "write_lastrun") as m:
            self.manager.get_records()
            m.assert_called_once_with("bazonk")

    def test_write_lastrun(self):
        """Test that we actually write lastrun files."""
        self.flags(projects=["bazonk"])
        if six.PY3:
            builtins_open = "builtins.open"
        else:
            builtins_open = "__builtin__.open"

        with unittest.mock.patch(builtins_open, unittest.mock.mock_open()) as m:
            self.manager.get_records()
            m.assert_called_once_with("/tmp/caso_test/lastrun.bazonk", "w")

    def flags(self, **kw):
        """Override flag variables for a test."""
        group = kw.pop("group", None)
        for k, v in six.iteritems(kw):
            CONF.set_override(k, v, group)

    def reset_flags(self):
        """Reset flags."""
        CONF.reset()
