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
import novaclient.client
from oslo_config import cfg

from caso.extract import base
from caso.extract import utils
from caso import record

CONF = cfg.CONF
CONF.import_opt("site_name", "caso.extract.manager")
CONF.import_opt("user", "caso.extract.base", "extractor")
CONF.import_opt("password", "caso.extract.base", "extractor")
CONF.import_opt("endpoint", "caso.extract.base", "extractor")
CONF.import_opt("insecure", "caso.extract.base", "extractor")


class OpenStackExtractor(base.BaseExtractor):
    def _get_conn(self, tenant):
        client = novaclient.client.Client
        conn = client(
            2,
            CONF.extractor.user,
            CONF.extractor.password,
            tenant,
            CONF.extractor.endpoint,
            insecure=CONF.extractor.insecure,
            service_type="compute")
        conn.authenticate()
        return conn

    def extract_for_tenant(self, tenant, lastrun, extract_to):
        """Extract records for a tenant from given date querying nova.

        This method will get information from nova.

        :param tenant: Tenant to extract records for.
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
        conn = self._get_conn(tenant)
        ks_conn = self._get_keystone_client(tenant)
        users = self._get_keystone_users(ks_conn)
        tenant_id = conn.client.tenant_id
        servers = conn.servers.list(search_opts={"changes-since": lastrun})

        servers = sorted(servers, key=operator.attrgetter("created"))

        if servers:
            start = dateutil.parser.parse(servers[0].created)
            start = start.replace(tzinfo=None)
        else:
            start = lastrun

        aux = conn.usage.get(tenant_id, start, extract_to)
        usages = getattr(aux, "server_usages", [])

        images = conn.images.list()
        records = {}

        vo = self.voms_map.get(tenant)

        for server in servers:
            status = self.vm_status(server.status)
            image_id = None
            for image in images:
# For some old severs, server.image is an empty string, perhaps image was deleted
# so server.image["id"] causes exception if not checked
                if isinstance(server.image, dict):
                    if image.id == server.image['id']:
                        image_id = image.metadata.get("vmcatcher_event_ad_mpuri",
                                                  None)
                        break
                else:
                    image_id = ''
                    break

#                if image.id == server.image['id']:
#                    image_id = image.metadata.get("vmcatcher_event_ad_mpuri",
#                                                  None)
#                    break

            if image_id is None:
                image_id = server.image['id']

            r = record.CloudRecord(server.id,
                                   CONF.site_name,
                                   server.name,
                                   server.user_id,
                                   server.tenant_id,
                                   vo,
                                   cloud_type="OpenStack",
                                   status=status,
                                   image_id=image_id,
                                   user_dn=users.get(server.user_id, None))
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
