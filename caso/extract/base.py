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

import abc
import json
import warnings

from oslo_config import cfg
from oslo_log import log
import six

from caso import keystone_client

opts = [
    cfg.StrOpt('site_name',
               help='Site name as in GOCDB.'),
    cfg.StrOpt('service_name',
               default='$site_name',
               help='Service name within the site'),
    cfg.StrOpt('benchmark_name_key',
               default='accounting:benchmark_type',
               help='Metadata key used to retrieve the benchmark type '
                    'from the flavor properties.'),
    cfg.StrOpt('benchmark_value_key',
               default='accounting:benchmark_value',
               help='Metadata key used to retrieve the benchmark value '
                    'from the flavor properties.'),
    cfg.ListOpt('projects',
                default=[],
                deprecated_name='tenants',
                help='List of projects to extract accounting records from.'),
    cfg.StrOpt('mapping_file',
               default='/etc/caso/voms.json',
               deprecated_group="extractor",
               help='File containing the VO <-> project mapping as used '
               'in Keystone-VOMS.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = log.getLogger(__name__)

openstack_vm_statuses = {
    'active': 'started',
    'build': 'started',
    'confirming_resize': 'started',
    'deleted': 'completed',
    'error': 'error',
    'hard_reboot': 'started',
    'migrating': 'started',
    'password': 'started',
    'paused': 'paused',
    'reboot': 'started',
    'rebuild': 'started',
    'rescue': 'started',
    'resize': 'started',
    'revert_resize': 'started',
    'verify_resize': 'started',
    'shutoff': 'completed',
    'suspended': 'suspended',
    'terminated': 'completed',
    'stopped': 'stopped',
    'saving': 'started',
    'unknown': 'unknown',
}


@six.add_metaclass(abc.ABCMeta)
class BaseExtractor(object):
    def __init__(self):
        try:
            mapping = json.loads(open(CONF.mapping_file).read())
        except ValueError:
            # FIXME(aloga): raise a proper exception here
            raise
        else:
            self.voms_map = {}
            for vo, vomap in six.iteritems(mapping):
                tenant = vomap.get("tenant", None)
                tenants = vomap.get("tenants", [])
                if tenant is not None:
                    warnings.warn("Using deprecated 'tenant' mapping, please "
                                  "use 'projects' instead", DeprecationWarning)
                if tenants:
                    warnings.warn("Using deprecated 'tenants' mapping, please "
                                  "use 'projects' instead", DeprecationWarning)
                tenants.append(tenant)
                projects = vomap.get("projects", tenants)
                if not projects:
                    LOG.warning("No project mapping found for VO %s" % vo)
                for project in projects:
                    self.voms_map[project] = vo

    def _get_keystone_client(self, project):
        client = keystone_client.get_client(CONF, project)
        return client

    def _get_keystone_user(self, ks_client, uuid):
        try:
            user = ks_client.users.get(user=uuid)
            return user.name
        except Exception:
            return None

    def vm_status(self, status):
        """Return the status corresponding to the OpenStack status.

        :param status: OpenStack status.
        """
        return openstack_vm_statuses.get(status.lower(), 'unknown')

    @abc.abstractmethod
    def extract_for_project(self, project, extract_from):
        """Extract records for a project from given date.

        :param project: Project to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :returns: A dictionary of {"server_id": caso.record.Record"}

        This method should be overriden in a subclass.
        """
