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

"""Module containing the base class for all OpenStack extractors."""

import datetime
import functools
import operator

import cinderclient.v3.client
import dateutil.parser
import glanceclient.client
import keystoneauth1.exceptions.http
import neutronclient.v2_0.client
import novaclient.client
from oslo_config import cfg
from oslo_log import log

from caso.extract import base
from caso import keystone_client

CONF = cfg.CONF

opts = [
    cfg.StrOpt(
        "region_name",
        default=None,
        help="OpenStack Region to use. This option will force cASO to "
        "extract records from a specific OpenStack Region, if "
        "there are several defined in the OpenStack site. "
        "Defaults to None.",
    ),
]

CONF.register_opts(opts)

LOG = log.getLogger(__name__)


class BaseOpenStackExtractor(base.BaseProjectExtractor):
    """Base OpenStack Extractor that all other extractors should inherit from."""

    def __init__(self, project, vo):
        """Initialize the OpenStack extractor for a given project."""
        super(BaseOpenStackExtractor, self).__init__(project)

        self.keystone = self._get_keystone_client()
        self.keystone_unscoped = self._get_keystone_client(project_scoped=False)
        self.project_id = self._get_project_id()

        self.vo = vo

        class Users:
            def __init__(self, parent):
                self._users = {}
                self.parent = parent

            def get(self, key, default=None):
                return self[key] or default

            def keys(self):
                return self._users.keys()

            def values(self):
                return self._users.values()

            def __getitem__(self, key):
                if key is None:
                    return None
                if key not in self._users:
                    self._users[key] = self.parent._get_keystone_user(key)
                return self._users.get(key, None)

        # Membership in keystone can be direct (a user belongs to a project) or
        # via group membership, therefore we cannot get a list directly. We
        # will build this aftewards
        self.users = Users(self)

    @functools.cached_property
    def _keystone_session(self):
        """Keystone session for the project, shared by all the service clients."""
        return keystone_client.get_session(CONF, self.project)

    def _get_keystone_session(self):
        """Get a Keystone session for the configured project in the object."""
        return self._keystone_session

    def _get_keystone_client(self, project_scoped=True):
        """Get a Keystone Client for the configured project in the object."""
        client = keystone_client.get_client(
            CONF, project=self.project if project_scoped else None, system_scope="all"
        )
        return client

    def _get_cinder_client(self):
        """Get Cinder client with keystone session."""
        session = self._get_keystone_session()
        return cinderclient.v3.client.Client(session=session)

    def _get_glance_client(self):
        """Get a glance client with a keystone session."""
        session = self._get_keystone_session()
        return glanceclient.client.Client(2, session=session)

    def _get_neutron_client(self):
        """Get a neutron client with a keystone session."""
        session = self._get_keystone_session()
        return neutronclient.v2_0.client.Client(session=session)

    def _get_nova_client(self):
        """Get a nova client with a keystone session."""
        region_name = CONF.region_name
        session = self._get_keystone_session()
        return novaclient.client.Client(2, session=session, region_name=region_name)

    @staticmethod
    def _get_server_start(server):
        """Get the creation time of a server as a naive datetime in UTC."""
        # We use created, as the start_time may change upon certain actions!
        server_start = dateutil.parser.parse(server.created)
        server_start = server_start.replace(tzinfo=None)
        return server_start

    @staticmethod
    def _get_server_end(server):
        """Get the end time of a server as a naive datetime in UTC, if any."""
        server_end = getattr(server, "OS-SRV-USG:terminated_at")
        if server_end is None:
            # If the server has no end_time, and no launched_at, we should use
            # server.created as the end time (i.e. VM has not started at all)
            if getattr(server, "OS-SRV-USG:launched_at") is None:
                server_end = server.created
            # Then, if a server is deleted, stuck in task_status deleting, and
            # the end time is None, we have to return the updated time as the
            # end date, otherwise these server will never be completed.
            elif server.status == "DELETED":
                server_end = server.updated
        if server_end:
            server_end = dateutil.parser.parse(server_end)
            server_end = server_end.replace(tzinfo=None)
        return server_end

    def _get_flavors(self):
        """Get all the flavors (including extra specs) indexed by their ID."""
        flavors = {}
        for flavor in self.nova.flavors.list():
            flavors[flavor.id] = flavor.to_dict()
            flavors[flavor.id]["extra"] = flavor.get_keys()
        return flavors

    @staticmethod
    def _list_paginated(list_method, sort_attr, limit=200, **kwargs):
        """Get all the resources from a paginated OpenStack list method.

        :param list_method: method accepting ``limit`` and ``marker`` arguments.
        :param sort_attr: attribute used to sort the returned resources.
        :param limit: maximum number of resources to request per call.
        :param kwargs: extra arguments passed to ``list_method``.
        :returns: a list of resources sorted by ``sort_attr``.
        """
        resources = []
        marker = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            batch = list_method(limit=limit, marker=marker, **kwargs)
            resources.extend(batch)
            if len(batch) < limit:
                break
            marker = batch[-1].id

        return sorted(resources, key=operator.attrgetter(sort_attr))

    def _get_project_id(self):
        """Get the project ID from the project in the object."""
        return self.keystone.projects.get(self.project).id

    def _get_keystone_user(self, uuid):
        """Get the Keystone username for a given uuid."""
        try:
            user = self.keystone_unscoped.users.get(user=uuid)
            return user.name
        except keystoneauth1.exceptions.http.Forbidden as e:
            LOG.error(f"Unauthorized to get user {uuid}")
            LOG.exception(e)
            return None
        except Exception as e:
            LOG.debug(f"Exception while getting user {uuid}")
            LOG.exception(e)
            return None

    @staticmethod
    def _get_measure_time():
        """Get current measurement time as a naive datetime in UTC.

        All the dates handled by the extractors are naive datetimes in UTC.
        """
        return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
