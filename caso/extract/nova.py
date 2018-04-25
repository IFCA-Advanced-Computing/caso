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

import operator

import dateutil.parser
import glanceclient.client
import novaclient.client
import novaclient.exceptions
from oslo_config import cfg
from oslo_log import log

from caso.extract import base
from caso import keystone_client
from caso import record

CONF = cfg.CONF
CONF.import_opt("extractor", "caso.extract.manager")
CONF.import_opt("site_name", "caso.extract.manager")
CONF.import_opt("benchmark_name_key", "caso.extract.manager")
CONF.import_opt("benchmark_value_key", "caso.extract.manager")

LOG = log.getLogger(__name__)


class OpenStackExtractor(base.BaseExtractor):
    def __init__(self):
        super(OpenStackExtractor, self).__init__()

    def _get_nova_client(self, project):
        session = keystone_client.get_session(CONF, project)
        return novaclient.client.Client(2, session=session)

    def _get_glance_client(self, project):
        session = keystone_client.get_session(CONF, project)
        return glanceclient.client.Client(2, session=session)

    def build_record(self, server, vo, images, flavors, users):
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
        else:
            bench_name = bench_value = None

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

        r = record.CloudRecord(server.id,
                               CONF.site_name,
                               server.name,
                               server.user_id,
                               server.tenant_id,
                               vo,
                               compute_service=CONF.service_name,
                               status=status,
                               image_id=image_id,
                               user_dn=users.get(server.user_id, None),
                               benchmark_type=bench_name,
                               benchmark_value=bench_value)
        return r

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
        ks_client = self._get_keystone_client(project)
        users = self._get_keystone_users(ks_client)
        project_id = nova.client.session.get_project_id()

        flavors = {}
        for flavor in nova.flavors.list():
            flavors[flavor.id] = flavor.to_dict()
            flavors[flavor.id]["extra"] = flavor.get_keys()

        images = {image.id: image for image in glance.images.list()}
        records = {}

        vo = self.voms_map.get(project)

        # We cannot use 'changes-since' in the servers.list() API query, as it
        # will only include changes that have changed its status after that
        # date. However we cannot just get all the usages and then query
        # server by server, as deleted servers are not returned  by this
        # servers.get() call. What we do is the following:
        #
        # 1.- List all the deleted servers that changed after the start date
        # 2.- Build the records for the period [start, end]
        # 3.- Get all the usages
        # 4.- Iter over the usages and:
        # 4.1.- get information for non deleted servers
        # 4.2.- do nothing with deleted servers, as we collected in in step (2)

        # 1.- List all the deleted servers from that period.
        servers = []
        limit = 200
        marker = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            aux = nova.servers.list(
                search_opts={"changes-since": extract_from,
                             "deleted": True},
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
            server_start = dateutil.parser.parse(server.created)
            server_start = server_start.replace(tzinfo=None)
            # Some servers may be deleted before 'extract_from' but updated
            # afterwards
            server_end = server.__getattr__('OS-SRV-USG:terminated_at')
            if server_end:
                server_end = dateutil.parser.parse(server_end)
                server_end = server_end.replace(tzinfo=None)
            if (server_start > extract_to or
                    (server_end and server_end < extract_from)):
                continue
            records[server.id] = self.build_record(server, vo, images,
                                                   flavors, users)

        # 3.- Get all the usages for the period
        start = extract_from
        aux = nova.usage.get(project_id, start, extract_to)
        usages = getattr(aux, "server_usages", [])

        # 4.- Iter over the results and
        for usage in usages:
            # 4.1 and 4.2 Get the server if it is not yet there
            if usage["instance_id"] not in records:
                server = nova.servers.get(usage["instance_id"])

                server_start = dateutil.parser.parse(server.created)
                server_start = server_start.replace(tzinfo=None)
                if server_start > extract_to:
                    continue
                records[server.id] = self.build_record(server, vo, images,
                                                       flavors, users)
            instance_id = usage["instance_id"]
            records[instance_id].memory = usage["memory_mb"]
            records[instance_id].cpu_count = usage["vcpus"]
            records[instance_id].disk = usage["local_gb"]

            # Start time must be the time when the machine was created
            started = dateutil.parser.parse(usage["started_at"])
            records[instance_id].start_time = int(started.strftime("%s"))

            # End time must ben the time when the machine was ended, but it may
            # be none
            if usage.get('ended_at', None) is not None:
                ended = dateutil.parser.parse(usage["ended_at"])
                records[instance_id].end_time = int(ended.strftime("%s"))
            else:
                ended = None

            # Wall and CPU durations are absolute values, not deltas for the
            # reporting period. The nova API only gives use the usages for the
            # requested period, therefore we need to calculate the wall
            # duration by ourselves, then multiply by the nr of CPUs to get the
            # CPU duration.

            # If the machine has not ended, report consumption until
            # extract_to, otherwise get its consuption by substracting ended -
            # started.
            if ended is not None and ended < extract_to:
                wall = ended - started
            else:
                wall = extract_to - started

            wall = int(wall.total_seconds())
            records[instance_id].wall_duration = wall

            cput = wall * usage["vcpus"]
            records[instance_id].cpu_duration = cput

        return records
