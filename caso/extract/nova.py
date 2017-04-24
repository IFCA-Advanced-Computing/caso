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
from oslo_config import cfg
from oslo_log import log

from caso.extract import base
from caso.extract import utils
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

    def extract_for_project(self, project, lastrun, extract_to):
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
        lastrun = lastrun.replace(tzinfo=None)

        # Try and except here
        nova = self._get_nova_client(project)
        glance = self._get_glance_client(project)
        ks_client = self._get_keystone_client(project)
        users = self._get_keystone_users(ks_client)
        project_id = nova.client.session.get_project_id()

        flavors = {flavor.id: flavor for flavor in nova.flavors.list()}

        servers = []
        limit = 200
        marker = None
        # Iter over results until we do not have more to get
        while True:
            aux = nova.servers.list(search_opts={"changes-since": lastrun},
                                    limit=limit,
                                    marker=marker)
            servers.extend(aux)

            if len(aux) < limit:
                break
            marker = aux[-1].id

        servers = sorted(servers, key=operator.attrgetter("created"))

        if servers:
            start = dateutil.parser.parse(servers[0].created)
            start = start.replace(tzinfo=None)
        else:
            start = lastrun

        aux = nova.usage.get(project_id, start, extract_to)
        usages = getattr(aux, "server_usages", [])

        images = {image.id: image for image in glance.images.list()}
        records = {}

        vo = self.voms_map.get(project)

        for server in servers:
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
                bench_name = flavor.get_keys().get(CONF.benchmark_name_key)
                bench_value = flavor.get_keys().get(CONF.benchmark_value_key)
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
            records[server.id] = r

        for usage in usages:
            if usage["instance_id"] not in records:
                continue
            instance_id = usage["instance_id"]
            records[instance_id].memory = usage["memory_mb"]
            records[instance_id].cpu_count = usage["vcpus"]
            records[instance_id].disk = usage["local_gb"]

            started = dateutil.parser.parse(usage["started_at"])
            if usage.get('ended_at', None) is not None:
                ended = dateutil.parser.parse(usage["ended_at"])
            else:
                ended = None

            # Since the nova API only gives you the "changes-since",
            # we need to filter the machines that changed outside
            # the interval
            if utils.server_outside_interval(lastrun, extract_to, started,
                                             ended):
                del records[instance_id]
                continue

            records[instance_id].start_time = int(started.strftime("%s"))
            if ended is not None:
                records[instance_id].end_time = int(ended.strftime("%s"))
                wall = ended - started
            else:
                wall = extract_to - started

            wall = int(wall.total_seconds())
            records[instance_id].wall_duration = wall

            cput = int(usage["hours"] * 3600)
            # NOTE(aloga): in some cases there may be rounding errors and cput
            # may be larger than wall.
            records[instance_id].cpu_duration = cput if cput < wall else wall
        return records
