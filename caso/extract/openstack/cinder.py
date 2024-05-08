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

"""Module containing the OpenStack Volume (Cinder) record extractor."""

import operator

import datetime
import dateutil.parser
from oslo_config import cfg
from oslo_log import log

from caso.extract.openstack import base
from caso import record

CONF = cfg.CONF

CONF.import_opt("region_name", "caso.extract.openstack")
CONF.import_opt("site_name", "caso.extract.base")

LOG = log.getLogger(__name__)


class CinderExtractor(base.BaseOpenStackExtractor):
    """An OpenStack Volume (Cinder) record extractor for cASO."""

    def __init__(self, project, vo):
        """Get a Cinder record extractor for a given project."""
        super(CinderExtractor, self).__init__(project, vo)

        self.cinder = self._get_cinder_client()

    def _build_record(self, volume, extract_from, extract_to):
        """Build an individual record."""
        user = self.users[volume.user_id]
        measure_time = self._get_measure_time()

        vol_start = volume.__getattr__("created_at")
        vol_created = dateutil.parser.parse(vol_start)
        if vol_created < extract_from:
            vol_created = extract_from

        active_duration_delta = (extract_to - vol_created)
        ms = active_duration_delta.microseconds
        td = datetime.timedelta(microseconds=ms)
        active_duration = (active_duration_delta - td).total_seconds()

        r = record.StorageRecord(
            uuid=volume.id,
            site_name=CONF.site_name,
            name=volume.name,
            user_id=volume.user_id,
            group_id=self.project_id,
            fqan=self.vo,
            compute_service=CONF.service_name,
            status=volume.status,
            active_duration=active_duration,
            measure_time=measure_time,
            start_time=vol_created,
            capacity=volume.size,
            user_dn=user,
        )

        if volume.status == "in-use":
            attached_to = volume.attachments[0]["server_id"]
            attached_at = volume.attachments[0]["attached_at"]
            attached_at = dateutil.parser.parse(attached_at)
            if attached_at < extract_from:
                attached_at = extract_from
            attacht = (extract_to - attached_at).total_seconds()
            r.attached_duration = attacht
            r.attached_to = attached_to

        return r

    def _get_volumes(self, extract_from):
        """Get all volumes for a given date."""
        volumes = []
        limit = 200
        marker = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            aux = self.cinder.volumes.list(
                search_opts={"changes-since": extract_from}, limit=limit, marker=marker
            )
            volumes.extend(aux)

            if len(aux) < limit:
                break
            marker = aux[-1].id

        volumes = sorted(volumes, key=operator.attrgetter("created_at"))
        return volumes

    def extract(self, extract_from, extract_to):
        """Extract records for a project from given date querying cinder.

        This method will get information from cinder.

        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of storage records
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        extract_from = extract_from.replace(tzinfo=None)
        extract_to = extract_to.replace(tzinfo=None)

        # Our storage records
        self.str_records = {}

        volumes = self._get_volumes(extract_from)

        for vol in volumes:
            self.str_records[vol.id] = self._build_record(vol, extract_from, extract_to)

        return list(self.str_records.values())
