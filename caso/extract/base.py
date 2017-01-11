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

import keystoneclient.v2_0.client
from oslo_config import cfg
from oslo_log import log
import six

opts = [
    cfg.StrOpt('user',
               default='accounting',
               help='User to authenticate as.'),
    cfg.StrOpt('password',
               default='',
               help='Password to authenticate with.'),
    cfg.StrOpt('endpoint',
               default='',
               help='Keystone endpoint to autenticate with.'),
    cfg.BoolOpt('insecure',
                default=False,
                help='Perform an insecure connection (i.e. do '
                'not verify the server\'s certificate. DO NOT USE '
                'IN PRODUCTION.'),
    cfg.StrOpt('mapping_file',
               default='/etc/caso/voms.json',
               help='File containing the VO <-> tenant mapping as used '
               'in Keystone-VOMS.'),
    cfg.StrOpt('project_domain_id',
               default='',
               help='Project domain id. Required for Keystone v3.'),
    cfg.StrOpt('user_domain_id',
               default='',
               help='User domaing id. Required for Keystone v3.'),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="extractor")

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
            mapping = json.loads(open(CONF.extractor.mapping_file).read())
        except ValueError:
            # FIXME(aloga): raise a proper exception here
            raise
        else:
            self.voms_map = {}
            for vo, vomap in mapping.iteritems():
                tenant = vomap.get("tenant", None)
                tenants = vomap.get("tenants", [])
                if tenant is not None:
                    LOG.warning("Using deprecated 'tenant' mapping, please "
                                "use 'tenants' instead")
                tenants.append(tenant)
                if not tenants:
                    LOG.warning("No tenant mapping found for VO %s" % tenant)
                for tenant in tenants:
                    self.voms_map[tenant] = vo

    def _get_keystone_users(self, ks_client):
        tenant_id = ks_client.tenant_id
        users = ks_client.users.list(tenant_id=tenant_id)
        return {u.id: u.name for u in users}

    def vm_status(self, status):
        """Return the status corresponding to the OpenStack status.

        :param status: OpenStack status.
        """
        return openstack_vm_statuses.get(status.lower(), 'unknown')

    @abc.abstractmethod
    def extract_for_tenant(self, tenant, extract_from):
        """Extract records for a tenant from given date.

        :param tenant: Tenant to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :returns: A dictionary of {"server_id": caso.record.Record"}

        This method should be overriden in a subclass.
        """
