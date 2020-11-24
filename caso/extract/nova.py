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

import ipaddress
import operator

import dateutil.parser
import glanceclient.client
import neutronclient.v2_0.client
import novaclient.client
import novaclient.exceptions
from oslo_config import cfg
from oslo_log import log

from caso.extract import base
from caso import keystone_client
from caso import record
from datetime import datetime

CONF = cfg.CONF

opts = [
    cfg.StrOpt('region_name',
               default=None,
               help='OpenStack Region to use. This option will force cASO to '
                    'extract records from a specific OpenStack Region, in '
                    'there are several defined in the OpenStack site. '
                    'Defaults to None.')
]

CONF.register_opts(opts)

CONF.import_opt("site_name", "caso.extract.base")
CONF.import_opt("benchmark_name_key", "caso.extract.base")
CONF.import_opt("benchmark_value_key", "caso.extract.base")

LOG = log.getLogger(__name__)


class OpenStackExtractor(base.BaseExtractor):
    def __init__(self):
        super(OpenStackExtractor, self).__init__()

    def _get_nova_client(self, project):
        region_name = CONF.region_name
        session = keystone_client.get_session(CONF, project)
        return novaclient.client.Client(2, session=session,
                                        region_name=region_name)

    def _get_glance_client(self, project):
        session = keystone_client.get_session(CONF, project)
        return glanceclient.client.Client(2, session=session)

    def _get_neutron_client(self, project):
        session = keystone_client.get_session(CONF, project)
        return neutronclient.v2_0.client.Client(session=session)

    def build_record(self, server, vo, images, flavors, user):
        server_start = self._get_server_start(server)
        server_end = self._get_server_end(server)

        status = self.vm_status(server.status)

        image_id = None
        if server.image:
            image = images.get(server.image['id'])
            image_id = server.image['id']
            if image:
                if image.get("vmcatcher_event_ad_mpuri", None) is not None:
                    image_id = image.get("vmcatcher_event_ad_mpuri", None)

        flavor = flavors.get(server.flavor["id"])
        if flavor:
            bench_name = flavor["extra"].get(CONF.benchmark_name_key)
            bench_value = flavor["extra"].get(CONF.benchmark_value_key)
            memory = flavor["ram"]
            cpu_count = flavor["vcpus"]
            disk = flavor["disk"] + flavor["OS-FLV-EXT-DATA:ephemeral"]
        else:
            bench_name = bench_value = None
            memory = cpu_count = disk = None

        if not all([bench_name, bench_value]):
            if any([bench_name, bench_value]):
                LOG.warning("Benchmark for flavor %s not properly set" %
                            flavor)
            else:
                LOG.debug("Benchmark information for flavor %s not set,"
                          "plase indicate the corret benchmark_name_key "
                          "and benchmark_value_key in the configuration "
                          "file or set the correct properties in the "
                          "flavor." % flavor)

        r = record.CloudRecord(
            server.id,
            CONF.site_name,
            server.name,
            server.user_id,
            server.tenant_id,
            vo,
            start_time=server_start,
            end_time=server_end,
            compute_service=CONF.service_name,
            status=status,
            image_id=image_id,
            user_dn=user,
            benchmark_type=bench_name,
            benchmark_value=bench_value,
            memory=memory,
            cpu_count=cpu_count,
            disk=disk
        )
        return r

    def build_ip_record(self, tenant_id, vo, user,
                        ip_count, version, user_id=None):
        measure_time = self._get_measure_time()

        r = record.IPRecord(
            measure_time,
            CONF.site_name,
            user_id,
            tenant_id,
            user,
            vo,
            version,
            ip_count,
            compute_service=CONF.service_name
        )

        return r

    @staticmethod
    def _get_server_start(server):
        # We use created, as the start_time may change upon certain actions!
        server_start = dateutil.parser.parse(server.created)
        server_start = server_start.replace(tzinfo=None)
        return server_start

    @staticmethod
    def _get_server_end(server):
        server_end = server.__getattr__('OS-SRV-USG:terminated_at')
        if server_end is None:
            # If the server has no end_time, and no launched_at, we should use
            # server.created as the end time (i.e. VM has not started at all)
            if server.__getattr__("OS-SRV-USG:launched_at") is None:
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

    @staticmethod
    def _get_measure_time():
        measure_time = datetime.now()
        return measure_time

    def extract_for_project(self, project, extract_from, extract_to):
        """Extract records for a project from given date querying nova.

        This method will get information from nova.

        :param project: Project to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A dictionary of {"server_id": caso.record.Record"}
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        extract_from = extract_from.replace(tzinfo=None)

        # Try and except here
        nova = self._get_nova_client(project)
        glance = self._get_glance_client(project)
        neutron = self._get_neutron_client(project)
        ks_client = self._get_keystone_client(project)

        # Membership in keystone can be direct (a user belongs to a project) or
        # via group membership.
        users = {}
        project_id = nova.client.session.get_project_id()

        flavors = {}
        for flavor in nova.flavors.list():
            flavors[flavor.id] = flavor.to_dict()
            flavors[flavor.id]["extra"] = flavor.get_keys()

        images = {image.id: image for image in glance.images.list()}
        records = {}
        ip_records = {}
        ip_counts = {}
        floatings = []

        vo = self.voms_map.get(project)
        if vo is None:
            LOG.warning("No mapping could be found for project '%s', "
                        "please check mapping file!", project_id)

        # We cannot use just 'changes-since' in the servers.list() API query,
        # as it will only include servers that have changed its status after
        # that date. However we cannot just get all the usages and then query
        # server by server, as deleted servers are not returned  by the usages
        # call. Moreover, Nova resets the start_time after performing some
        # actions on the server (rebuild, resize, rescue). If we use that time,
        # we may get a drop in the wall time, as a server that has been resized
        # in the middle of its lifetime will suddenly change its start_time
        #
        # Therefore, what we do is the following (hackish approach)
        #
        # 1.- List all the servers that changed its status after the start time
        #     for the reporting period
        # 2.- Build the records for the period [start, end] using those servers
        # 3.- Get all the usages, being aware that the start time may be wrong
        # 4.- Iter over the usages and:
        # 4.1.- get information for servers that are not returned by the query
        #       in (1), for instance servers that have not changed it status.
        #       We build then the records for those severs
        # 4.2.- For all the servers, adjust the CPU, memory and disk resources
        #       as the flavor may not exist, but we can get those resources
        #       from the usages API.

        # Lets start

        # 1.- List all the deleted servers from that period.
        servers = []
        limit = 200
        marker = None
        ip = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            aux = nova.servers.list(
                search_opts={"changes-since": extract_from},
                limit=limit,
                marker=marker
            )
            servers.extend(aux)

            if len(aux) < limit:
                break
            marker = aux[-1].id

        servers = sorted(servers, key=operator.attrgetter("created"))

        # 2.- Build the records for the period. Drop servers outside the period
        # (we do this manually as we cannot limit the query to a period, only
        # changes after start date).
        for server in servers:

            server_start = self._get_server_start(server)
            server_end = self._get_server_end(server)

            # Some servers may be deleted before 'extract_from' but updated
            # afterwards
            if (server_start > extract_to or
                    (server_end and server_end < extract_from)):
                continue

            user = users.get(server.user_id, None)
            if not user:
                user = self._get_keystone_user(ks_client, server.user_id)
                users[server.user_id] = user
                ip_counts[user] = 0

            records[server.id] = self.build_record(server, vo, images,
                                                   flavors, user)

            for name, value in server.addresses.items():
                for i in value:
                    if i["OS-EXT-IPS:type"] == "floating":
                        ip = i
                        floatings.append(ip['addr'])
                        ip_counts[user] += 1

            # Wall and CPU durations are absolute values, not deltas for the
            # reporting period. The nova API only gives use the usages for the
            # requested period, therefore we need to calculate the wall
            # duration by ourselves, then multiply by the nr of CPUs to get the
            # CPU duration.

            # If the machine has not ended, report consumption until
            # extract_to, otherwise get its consuption by substracting ended -
            # started (done by the record).
            if server_end is None or server_end > extract_to:
                wall = extract_to - server_start
                wall = int(wall.total_seconds())
                records[server.id].wall_duration = wall
                # If we are republishing, the machine reports status completed,
                # but it is not True for this period, so we need to fake the
                # status and remove the end time for the server
                records[server.id].end_time = None

                if records[server.id].status == "completed":
                    records[server.id].status = self.vm_status("active")

        # Build IP records for each of the users
        list_user_id = list(users.keys())
        list_user_name = list(users.values())

        ip_version = '4'
        if ip is not None:
            ip_version = ipaddress.ip_address(ip['addr']).version

        for user, count in ip_counts.items():
            user_id = list_user_id[list_user_name.index(user)]
            if count == 0:
                continue

            ip_records[user] = self.build_ip_record(project_id,
                                                    vo,
                                                    user,
                                                    count,
                                                    ip_version,
                                                    user_id=user_id)

        # 3.- Get all the usages for the period
        start = extract_from
        aux = nova.usage.get(project_id, start, extract_to)
        usages = getattr(aux, "server_usages", [])

        floating_ips = neutron.list_floatingips(project_id)

        # 4.- Iter over the results and
        for usage in usages:
            # 4.1 and 4.2 Get the server if it is not yet there
            if usage["instance_id"] not in records:
                try:
                    server = nova.servers.get(usage["instance_id"])
                except novaclient.exceptions.ClientException as e:
                    LOG.warning(
                        "Cannot get server '%s' from the Nova API, probably "
                        "because it is an error in the DB. Please refer to "
                        "the following page for more details: "
                        "https://caso.readthedocs.io/en/stable/"
                        "troubleshooting.html#cannot-find-vm-in-api"
                        % usage["instance_id"]
                    )
                    if CONF.debug:
                        LOG.exception(e)

                    continue

                server_start = self._get_server_start(server)
                if server_start > extract_to:
                    continue

                user = users.get(server.user_id, None)
                if not user:
                    user = self._get_keystone_user(ks_client, server.user_id)
                    users[server.user_id] = user

                record = self.build_record(server, vo, images,
                                           flavors, user)

                server_start = record.start_time

                # End time must ben the time when the machine was ended, but it
                # may be none
                if usage.get('ended_at', None) is not None:
                    server_end = dateutil.parser.parse(usage["ended_at"])
                    record.end_time = server_end
                else:
                    server_end = None

                # Wall and CPU durations are absolute values, not deltas for
                # the reporting period. The nova API only gives use the usages
                # for the requested period, therefore we need to calculate the
                # wall duration by ourselves, then multiply by the nr of CPUs
                # to get the CPU duration.

                # If the machine has not ended, report consumption until
                # extract_to, otherwise get its consuption by substracting
                # ended - started (done by the record).
                if server_end is None or server_end > extract_to:
                    wall = extract_to - server_start
                    wall = int(wall.total_seconds())
                    record.wall_duration = wall
                    # If we are republishing, the machine reports status
                    # completed, but it is not True for this period, so we need
                    # to fake the status
                    if record.status == "completed":
                        record.status = self.vm_status("active")

                cput = wall * usage["vcpus"]
                record.cpu_duration = cput

                records[server.id] = record

            # Adjust resources that may not be
            record = records[usage["instance_id"]]
            record.memory = usage["memory_mb"]
            record.cpu_count = usage["vcpus"]
            record.disk = usage["local_gb"]

        # Build records for IPs not assigned to any server,
        # but allocated to project
        user = None
        ip_counts[user] = 0
        for floating_ip in floating_ips["floatingips"]:
            ip = floating_ip["floating_ip_address"]
            status = floating_ip["status"]
            if (ip not in floatings) and (status == "DOWN"):
                ip_start = datetime.strptime(floating_ip["created_at"],
                                             '%Y-%m-%dT%H:%M:%SZ')
                if ip_start > extract_to:
                    continue
                else:
                    ip_counts[user] += 1

        ip_records[user] = self.build_ip_record(project_id, vo,
                                                user,
                                                ip_counts[user],
                                                ip_version)

        return records, ip_records
