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

import datetime
import operator

import dateutil.parser
from dateutil import tz
import novaclient.client
from oslo_config import cfg

from caso.extract import base
from caso import record
from keystoneauth1 import session
from keystoneclient.v3 import client as ksclient
from keystoneauth1.identity import v3

CONF = cfg.CONF
CONF.import_opt("site_name", "caso.extract.manager")
CONF.import_opt("user", "caso.extract.base", "extractor")
CONF.import_opt("password", "caso.extract.base", "extractor")
CONF.import_opt("endpoint", "caso.extract.base", "extractor")
CONF.import_opt("insecure", "caso.extract.base", "extractor")


class OpenStackExtractor(base.BaseExtractor):
    def _get_conn(self, tenant):
	auth = v3.Password(auth_url=CONF.extractor.endpoint,
                                 username=CONF.extractor.user,
                                 password=CONF.extractor.password,
                                 project_name=tenant,
				 user_domain_id='default',
                    		 project_domain_id='default')
	sess = session.Session(auth=auth)
	conn = novaclient.client.Client(2, session=sess)
        return conn

    def _get_keystone_conn(self, tenant):
        auth = v3.Password(auth_url=CONF.extractor.endpoint,
                                 username=CONF.extractor.user,
                                 password=CONF.extractor.password,
                                 project_name=tenant,
                                 user_domain_id='default',
                                 project_domain_id='default')
        sess = session.Session(auth=auth)
        keystone = ksclient.Client (session=sess)
	print dir(keystone.users)
        return keystone

    def extract_for_tenant(self, tenant, lastrun):
        """Extract records for a tenant from given date querying nova.

        This method will get information from nova.

        :param tenant: Tenant to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :returns: A dictionary of {"server_id": caso.record.Record"}
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        lastrun = lastrun.replace(tzinfo=None)
        now = datetime.datetime.now(tz.tzutc()).replace(tzinfo=None)
        end = now + datetime.timedelta(days=1)

        # Try and except here
        conn = self._get_conn(tenant)
        tenant_id = conn.client.get_project_id()
	print dir(conn.client)
	user_id = conn.client.get_user_id()
	print user_id
        ks_conn = self._get_keystone_conn(tenant)
        servers = conn.servers.list(search_opts={"changes-since": lastrun})

        servers = sorted(servers, key=operator.attrgetter("created"))

        if servers:
            start = dateutil.parser.parse(servers[0].created)
            start = start.replace(tzinfo=None)
        else:
            start = lastrun

        aux = conn.usage.get(tenant_id, start, end)
        usages = getattr(aux, "server_usages", [])

        images = conn.images.list()
        records = {}

        vo = self.voms_map.get(tenant)

        for server in servers:
            status = self.vm_status(server.status)
            image_id = None
            for image in images:
                if image.id == server.image['id']:
                    image_id = image.metadata.get("vmcatcher_event_ad_mpuri",
                                                  None)
                    break

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
                                   user_dn=ks_conn.users.get(server.user_id))
            records[server.id] = r

        for usage in usages:
            if usage["instance_id"] not in records:
                continue
            instance_id = usage["instance_id"]
            records[instance_id].memory = usage["memory_mb"]
            records[instance_id].cpu_count = usage["vcpus"]
            records[instance_id].disk = usage["local_gb"]

            started = dateutil.parser.parse(usage["started_at"])
            records[instance_id].start_time = int(started.strftime("%s"))
            if usage.get("ended_at", None) is not None:
                ended = dateutil.parser.parse(usage['ended_at'])
                records[instance_id].end_time = int(ended.strftime("%s"))
                wall = ended - started
            else:
                wall = now - started

            wall = int(wall.total_seconds())
            records[instance_id].wall_duration = wall

            cput = int(usage["hours"] * 3600)
            # NOTE(aloga): in some cases there may be rounding errors and cput
            # may be larger than wall.
            records[instance_id].cpu_duration = cput if cput < wall else wall
        return records
