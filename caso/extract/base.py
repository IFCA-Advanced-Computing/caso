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

accelerator_opts = [
    cfg.StrOpt('type_key',
               default='Accelerator:Type',
               deprecated_name='accelerator_type_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the accelerator type '
                    'from the flavor properties.'),
    cfg.StrOpt('vendor_key',
               default='Accelerator:Vendor',
               deprecated_name='accelerator_vendor_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the accelerator vendor '
                    'from the flavor properties.'),
    cfg.StrOpt('model_key',
               default='Accelerator:Model',
               deprecated_name='accelerator_model_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the accelerator model '
                    'from the flavor properties.'),
    cfg.StrOpt('number_key',
               default='Accelerator:Number',
               deprecated_name='accelerator_number_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the accelerator number '
                    'from the flavor properties.'),
]

benchmark_opts = [
    cfg.StrOpt('name_key',
               default='accounting:benchmark_type',
               deprecated_name='benchmark_name_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the benchmark type '
                    'from the flavor properties.'),
    cfg.StrOpt('value_key',
               default='accounting:benchmark_value',
               deprecated_name='benchmark_value_key',
               deprecated_group='DEFAULT',
               help='Metadata key used to retrieve the benchmark value '
                    'from the flavor properties.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)
CONF.register_opts(benchmark_opts, group="benchmark")
CONF.register_opts(accelerator_opts, group="accelerator")

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
        # FIXME(aloga): add deprecated warning here
        LOG.warning("Using DEPRECATED extractor!! Please update as soon as "
                    "possible!!")
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
                    LOG.warning(f"No project mapping found for VO {vo}")
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


@six.add_metaclass(abc.ABCMeta)
class BaseProjectExtractor(object):
    def __init__(self, project):
        self.project = project

        # FIXME(remove this)
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
                    LOG.warning(f"No project mapping found for VO {vo}")
                for project in projects:
                    self.voms_map[project] = vo

    def vm_status(self, status):
        """Return the status corresponding to the OpenStack status.

        :param status: OpenStack status.
        """
        return openstack_vm_statuses.get(status.lower(), 'unknown')

    @abc.abstractmethod
    def extract(self, extract_from):
        """Extract records for a project from given date.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :returns: A dictionary of {"server_id": caso.record.Record"}

        This method should be overriden in a subclass.
        """
