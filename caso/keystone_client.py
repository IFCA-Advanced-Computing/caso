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

"""Module containing the management of Keystone Clients for cASO."""

from keystoneauth1 import exceptions
from keystoneauth1 import loading
from keystoneclient.v3 import client as ks_client_v3
from oslo_config import cfg

CONF = cfg.CONF

CFG_GROUP = "keystone_auth"

loading.register_auth_conf_options(CONF, CFG_GROUP)
loading.register_session_conf_options(CONF, CFG_GROUP)

opts = []
opts += loading.get_auth_common_conf_options()
opts += loading.get_session_conf_options()
opts += loading.get_auth_plugin_conf_options("password")


def get_session(conf, project, system_scope=None):
    """Get an auth session."""
    # First try using project_id
    if project:
        system_scope = None
    auth_plugin = loading.load_auth_from_conf_options(
        conf, CFG_GROUP, project_id=project, system_scope=system_scope
    )
    sess = loading.load_session_from_conf_options(conf, CFG_GROUP, auth=auth_plugin)
    try:
        sess.get_token()
    except exceptions.Unauthorized:
        # Failure, now try project_name
        auth_plugin = loading.load_auth_from_conf_options(
            conf, CFG_GROUP, project_name=project, project_id=None
        )
        sess = loading.load_session_from_conf_options(conf, CFG_GROUP, auth=auth_plugin)
    return sess


def get_client(conf, project=None, system_scope=None):
    """Return a client for Keystone."""
    sess = get_session(conf, project, system_scope)
    return ks_client_v3.Client(session=sess, interface="public")
