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
        """Build an individual record.

        :returns: a StorageRecord, or None if the volume was created after the
                  extraction period.
        """
        volume_creation = dateutil.parser.parse(volume.created_at)
        if volume_creation > extract_to:
            return None

        user = self.users[volume.user_id]
        measure_time = self._get_measure_time()

        start_time = max(volume_creation, extract_from)
        active_duration = int((extract_to - start_time).total_seconds())

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
            start_time=start_time,
            volume_creation=volume_creation,
            capacity=volume.size,
            user_dn=user,
        )

        # Multi-attach volumes may be attached to several servers, report all of
        # them and the time since the first attachment.
        attachments = volume.attachments if volume.status == "in-use" else []
        if attachments:
            attached_at = min(
                dateutil.parser.parse(a["attached_at"]) for a in attachments
            )
            attached_at = max(attached_at, extract_from)
            r.attached_duration = (extract_to - attached_at).total_seconds()
            r.attached_to = ",".join(a["server_id"] for a in attachments)

        return r

    def _get_volumes(self, extract_from):
        """Get all volumes for a given date."""
        return self._list_paginated(
            self.cinder.volumes.list,
            "created_at",
            search_opts={"changes-since": extract_from},
        )

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
            r = self._build_record(vol, extract_from, extract_to)
            if r is not None:
                self.str_records[vol.id] = r

        return list(self.str_records.values())
