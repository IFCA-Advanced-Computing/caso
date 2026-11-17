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

"""Tests for `caso.manager` module."""

from unittest import mock

from oslo_config import cfg
import pytest

from caso import manager

CONF = cfg.CONF


@pytest.fixture
def caso_manager(tmp_path):
    """Get a cASO manager with the extractor and messenger managers mocked."""
    CONF.set_override("spooldir", str(tmp_path))
    CONF.set_override("lock_path", str(tmp_path))
    with mock.patch("caso.extract.manager.Manager") as m_extract, mock.patch(
        "caso.messenger.Manager"
    ) as m_messenger:
        m_extract.return_value.get_records.return_value = ["record"]
        yield manager.Manager(), m_extract.return_value, m_messenger.return_value
    CONF.clear_override("spooldir")
    CONF.clear_override("lock_path")
    CONF.clear_override("dry_run")


def test_run_pushes_records(caso_manager):
    """Records must be extracted and pushed to the messengers."""
    mgr, extractor, messenger = caso_manager
    CONF.set_override("dry_run", False)

    mgr.run()

    extractor.get_records.assert_called_once_with()
    messenger.push_to_all.assert_called_once_with(["record"])


def test_run_dry_run_does_not_push(caso_manager):
    """Records must not be pushed when running in dry-run mode."""
    mgr, extractor, messenger = caso_manager
    CONF.set_override("dry_run", True)

    mgr.run()

    extractor.get_records.assert_called_once_with()
    messenger.push_to_all.assert_not_called()


def test_projects_and_vos_skips_failing_projects(caso_manager):
    """A project whose VO cannot be obtained must not stop the iteration."""
    mgr, extractor, _ = caso_manager
    extractor.projects = ["p1", "p2"]
    extractor.get_project_vo.side_effect = [Exception("boom"), "vo2"]

    assert list(mgr.projects_and_vos()) == [("p2", "vo2")]
