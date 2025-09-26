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

"""Tests for `caso._cmd.projects` module."""

import sys
import unittest
from unittest import mock

from oslo_config import cfg

from caso._cmd import projects
from caso.tests import base

CONF = cfg.CONF


class TestProjectsCommand(base.TestCase):
    """Test case for the projects command module."""

    def setUp(self):
        """Set up test fixtures."""
        super(TestProjectsCommand, self).setUp()

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_main_success(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test main function with successful project retrieval."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.projects_and_vos.return_value = [('project1', 'vo1'), ('project2', 'vo2')]
        
        # Mock keystone project retrieval
        mock_project = mock.MagicMock()
        mock_project.name = 'Project One'
        mock_manager.extractor_manager.keystone.projects.get.return_value = mock_project
        
        with mock.patch('builtins.print') as mock_print:
            projects.main()
            
            # Verify setup calls
            mock_parse_args.assert_called_once_with(sys.argv)
            mock_log_setup.assert_called_once_with(cfg.CONF, "caso")
            mock_manager_cls.assert_called_once()
            
            # Verify manager methods called
            mock_manager.projects_and_vos.assert_called_once()
            
            # Verify print was called with expected output format
            self.assertTrue(mock_print.called)
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertIn("'project1 (Project One) mapped to VO 'vo1'", print_calls)

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_main_with_keystone_error(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test main function when keystone project retrieval fails."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.projects_and_vos.return_value = [('project1', 'vo1')]
        
        # Mock keystone to raise an exception
        mock_manager.extractor_manager.keystone.projects.get.side_effect = Exception("Keystone error")
        
        with mock.patch('builtins.print') as mock_print:
            projects.main()
            
            # Verify error messages were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            error_messages = [call for call in print_calls if call.startswith("ERROR:")]
            self.assertTrue(len(error_messages) >= 2)  # Should have at least 2 error messages
            self.assertTrue(any("Could not get project project1" in msg for msg in error_messages))

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_migrate_dry_run_mode(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test migrate function in dry run mode."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.extractor_manager.voms_map.items.return_value = [('project1', 'vo1')]
        
        # Set dry_run flag
        self.flags(dry_run=True, vo_property='caso_vo')
        with mock.patch('builtins.print') as mock_print:
            projects.migrate()
            
            # Verify setup calls
            mock_parse_args.assert_called_once_with(sys.argv)
            mock_log_setup.assert_called_once_with(cfg.CONF, "caso")
            mock_manager._load_managers.assert_called_once()
            
            # Verify print statements for dry run
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            warning_printed = any("WARNING: Running in 'dry-run' mode" in call for call in print_calls)
            self.assertTrue(warning_printed)
            
            # Should print the openstack command but not execute it
            openstack_cmd_printed = any("openstack project set --property" in call for call in print_calls)
            self.assertTrue(openstack_cmd_printed)

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_migrate_with_projects_dry_run(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test migrate function with project migration in dry run mode."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.extractor_manager.voms_map.items.return_value = []
        
        # Set flags for project migration
        self.flags(dry_run=True, migrate_projects=True, projects=['project1'], caso_tag='caso')
        with mock.patch('builtins.print') as mock_print:
            projects.migrate()
            
            # Verify print statements for project tagging
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            tag_cmd_printed = any("openstack project set --tag caso project1" in call for call in print_calls)
            self.assertTrue(tag_cmd_printed)

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_migrate_actual_execution(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test migrate function with actual execution (not dry run)."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.extractor_manager.voms_map.items.return_value = [('project1', 'vo1')]
        
        # Mock successful keystone update
        mock_manager.extractor_manager.keystone.projects.update.return_value = None
        
        # Set flags for actual execution
        self.flags(dry_run=False, vo_property='caso_vo')
        with mock.patch('builtins.print') as mock_print:
            projects.migrate()
            
            # Verify keystone update was called
            mock_manager.extractor_manager.keystone.projects.update.assert_called_once_with(
                'project1', caso_vo='vo1'
            )
            
            # Should not print warning about dry run
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            warning_printed = any("WARNING: Running in 'dry-run' mode" in call for call in print_calls)
            self.assertFalse(warning_printed)

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_migrate_keystone_update_error(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test migrate function when keystone update fails."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.extractor_manager.voms_map.items.return_value = [('project1', 'vo1')]
        
        # Mock keystone update to raise an exception
        mock_manager.extractor_manager.keystone.projects.update.side_effect = Exception("Update failed")
        
        # Set flags for actual execution
        self.flags(dry_run=False, vo_property='caso_vo')
        with mock.patch('builtins.print') as mock_print:
            projects.migrate()
            
            # Verify error messages were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            error_messages = [call for call in print_calls if call.startswith("ERROR:")]
            self.assertTrue(len(error_messages) >= 2)  # Should have at least 2 error messages
            self.assertTrue(any("could not add property for project project1" in msg for msg in error_messages))

    @mock.patch('caso.config.parse_args')
    @mock.patch('oslo_log.log.setup')
    @mock.patch('caso.manager.Manager')
    def test_migrate_project_tagging_error(self, mock_manager_cls, mock_log_setup, mock_parse_args):
        """Test migrate function when project tagging fails."""
        # Setup mocks
        mock_manager = mock.MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.extractor_manager.voms_map.items.return_value = []
        
        # Mock project get and tag operations
        mock_project = mock.MagicMock()
        mock_project.add_tag.side_effect = Exception("Tag failed")
        mock_manager.extractor_manager.keystone.projects.get.return_value = mock_project
        
        # Set flags for project migration
        self.flags(dry_run=False, migrate_projects=True, projects=['project1'], caso_tag='caso')
        with mock.patch('builtins.print') as mock_print:
            projects.migrate()
            
            # Verify error messages were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            error_messages = [call for call in print_calls if call.startswith("ERROR:")]
            self.assertTrue(len(error_messages) >= 2)  # Should have at least 2 error messages
            self.assertTrue(any("could not add tag for project project1" in msg for msg in error_messages))