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

"""Module containing the OpenStack Compute (Nova) record extractor."""

import operator

import dateutil.parser
from dateutil.relativedelta import relativedelta
from dateutil.rrule import MONTHLY
from dateutil.rrule import rrule
import novaclient.exceptions
from oslo_config import cfg
from oslo_log import log

from caso.extract.openstack import base
from caso import record
from datetime import datetime

accelerator_opts = [
    cfg.StrOpt(
        "type_key",
        default="Accelerator:Type",
        help="Metadata key used to retrieve the accelerator type "
        "from the flavor properties.",
    ),
    cfg.StrOpt(
        "vendor_key",
        default="Accelerator:Vendor",
        help="Metadata key used to retrieve the accelerator vendor "
        "from the flavor properties.",
    ),
    cfg.StrOpt(
        "model_key",
        default="Accelerator:Model",
        help="Metadata key used to retrieve the accelerator model "
        "from the flavor properties.",
    ),
    cfg.StrOpt(
        "number_key",
        default="Accelerator:Number",
        help="Metadata key used to retrieve the accelerator number "
        "from the flavor properties.",
    ),
]

benchmark_opts = [
    cfg.StrOpt(
        "name_key",
        default="accounting:benchmark_type",
        help="Metadata key used to retrieve the benchmark type "
        "from the flavor properties.",
    ),
    cfg.StrOpt(
        "value_key",
        default="accounting:benchmark_value",
        help="Metadata key used to retrieve the benchmark value "
        "from the flavor properties.",
    ),
]

CONF = cfg.CONF

CONF.import_opt("region_name", "caso.extract.openstack")
CONF.import_opt("site_name", "caso.extract.base")
CONF.register_opts(benchmark_opts, group="benchmark")
CONF.register_opts(accelerator_opts, group="accelerator")

LOG = log.getLogger(__name__)


class NovaExtractor(base.BaseOpenStackExtractor):
    """An OpenStack Compute (Nova) record extractor for cASO."""

    def __init__(self, project, vo):
        """Get a Nova record extractor for a given project."""
        super(NovaExtractor, self).__init__(project, vo)

        self.nova = self._get_nova_client()
        self.glance = self._get_glance_client()
        self.neutron = self._get_neutron_client()

        self.flavors = self._get_flavors()
        self.images = self._get_images()

    def _build_acc_records(self, server, server_record, extract_from, extract_to):
        records = {}
        flavor = self.flavors.get(server.flavor["id"])
        if not flavor:
            return records

        acc_type = flavor["extra"].get(CONF.accelerator.type_key)
        acc_model = flavor["extra"].get(CONF.accelerator.model_key)
        acc_vendor = flavor["extra"].get(CONF.accelerator.vendor_key)
        acc_count = flavor["extra"].get(CONF.accelerator.number_key)
        if all([acc_type, acc_model, acc_count, acc_vendor]):
            acc_model = " ".join([acc_vendor, acc_model])
        else:
            return records

        # loop over the reported period and create one monthly record
        # not just take extract_from/to but consider server start/end
        start_date = max(server_record.start_time, extract_from)
        from_month = datetime(start_date.year, start_date.month, 1)
        if server_record.end_time:
            end_date = min(server_record.end_time, extract_to)
        else:
            end_date = extract_to
        to_month = datetime(end_date.year, end_date.month, 1)
        for month in rrule(MONTHLY, dtstart=from_month, until=to_month):
            record_start = max(month, server_record.start_time)
            record_end = min(month + relativedelta(months=+1), extract_to)
            if server_record.end_time:
                record_end = min(record_end, server_record.end_time)
            duration = (record_end - record_start).total_seconds()
            if duration < 0:
                # something weird happened, but don't send negative records
                continue
            month_record = record.AcceleratorRecord(
                measurement_month=month.month,
                measurement_year=month.year,
                uuid=server_record.uuid,
                fqan=server_record.fqan,
                compute_service=server_record.compute_service,
                site_name=server_record.site_name,
                count=acc_count,
                available_duration=int(duration),
                accelerator_type=acc_type,
                user_dn=server_record.user_dn,
                model=acc_model,
            )
            record_id = f"{server_record.uuid}-{month.month}-{month.year}"
            records[record_id] = month_record
        return records

    def _count_ips_on_server(self, server):
        count = 0
        for _name, value in server.addresses.items():
            for ip in value:
                if ip["OS-EXT-IPS:type"] == "floating":
                    count += 1
        return count

    def vm_status(self, status):
        """Return the status corresponding to the OpenStack status.

        :param status: OpenStack status.
        """
        openstack_vm_statuses = {
            "active": "started",
            "build": "started",
            "confirming_resize": "started",
            "deleted": "completed",
            "error": "error",
            "hard_reboot": "started",
            "migrating": "started",
            "password": "started",
            "paused": "paused",
            "reboot": "started",
            "rebuild": "started",
            "rescue": "started",
            "resize": "started",
            "revert_resize": "started",
            "verify_resize": "started",
            "shutoff": "completed",
            "suspended": "suspended",
            "terminated": "completed",
            "stopped": "stopped",
            "saving": "started",
            "unknown": "unknown",
        }
        return openstack_vm_statuses.get(status.lower(), "unknown")

    def _build_record(self, server):
        user = self.users[server.user_id]

        server_start = self._get_server_start(server)
        server_end = self._get_server_end(server)

        status = self.vm_status(server.status)

        image_id = None
        if server.image:
            image = self.images.get(server.image["id"])
            image_id = server.image["id"]
            if image:
                if image.get("vmcatcher_event_ad_mpuri", None) is not None:
                    image_id = image.get("vmcatcher_event_ad_mpuri", None)

        flavor = self.flavors.get(server.flavor["id"])
        if flavor:
            bench_name = flavor["extra"].get(CONF.benchmark.name_key)
            bench_value = flavor["extra"].get(CONF.benchmark.value_key)
            memory = flavor["ram"]
            cpu_count = flavor["vcpus"]
            disk = flavor["disk"] + flavor["OS-FLV-EXT-DATA:ephemeral"]
        else:
            bench_name = bench_value = None
            memory = cpu_count = disk = 0

        if not all([bench_name, bench_value]):
            if any([bench_name, bench_value]):
                LOG.warning(f"Benchmark for flavor {flavor} not properly set")
            else:
                LOG.debug(
                    f"Benchmark information for flavor {flavor} not set,"
                    " please indicate the corret name_key and value_key "
                    "in the [benchmark] section of the configuration "
                    "file or set the correct properties in the flavor."
                )

        floating_ips = self._count_ips_on_server(server)

        vm_name = server.name.encode("ascii", errors="ignore")

        r = record.CloudRecord(
            uuid=server.id,
            site_name=CONF.site_name,
            name=vm_name,
            user_id=server.user_id,
            group_id=server.tenant_id,
            fqan=self.vo,
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
            disk=disk,
            public_ip_count=floating_ips,
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
        server_end = server.__getattr__("OS-SRV-USG:terminated_at")
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

    def _get_servers(self, extract_from):
        servers = []
        limit = 200
        marker = None
        # Use a marker and iter over results until we do not have more to get
        while True:
            aux = self.nova.servers.list(
                search_opts={"changes-since": extract_from}, limit=limit, marker=marker
            )
            servers.extend(aux)

            if len(aux) < limit:
                break
            marker = aux[-1].id

        servers = sorted(servers, key=operator.attrgetter("created"))
        return servers

    def _get_images(self):
        images = {image.id: image for image in self.glance.images.list()}
        return images

    def _get_flavors(self):
        flavors = {}
        for flavor in self.nova.flavors.list():
            flavors[flavor.id] = flavor.to_dict()
            flavors[flavor.id]["extra"] = flavor.get_keys()
        return flavors

    def _get_usages(self, start, end):
        aux = self.nova.usage.get(self.project_id, start, end)
        usages = getattr(aux, "server_usages", [])
        return usages

    def _process_servers_for_period(self, servers, extract_from, extract_to):
        for server in servers:
            server_start = self._get_server_start(server)
            server_end = self._get_server_end(server)

            # Some servers may be deleted before 'extract_from' but updated
            # afterwards
            if server_start > extract_to or (server_end and server_end < extract_from):
                continue

            self.records[server.id] = self._build_record(server)
            self.acc_records.update(
                self._build_acc_records(
                    server, self.records[server.id], extract_from, extract_to
                )
            )

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
                self.records[server.id].wall_duration = wall
                # If we are republishing, the machine reports status completed,
                # but it is not True for this period, so we need to fake the
                # status and remove the end time for the server
                self.records[server.id].end_time = None

                if self.records[server.id].status == "completed":
                    self.records[server.id].status = self.vm_status("active")

                cput = wall * self.records[server.id].cpu_count
                self.records[server.id].cpu_duration = cput

    def _process_usages_for_period(self, usages, extract_from, extract_to):
        for usage in usages:
            # 4.1 and 4.2 Get the server if it is not yet there
            if usage["instance_id"] not in self.records:
                try:
                    server = self.nova.servers.get(usage["instance_id"])
                except novaclient.exceptions.ClientException as e:
                    LOG.warning(
                        "Cannot get server '{}' from the Nova API, probably "
                        "because it is an error in the DB. Please refer to "
                        "the following page for more details: "
                        "https://caso.readthedocs.io/en/stable/"
                        "troubleshooting.html#cannot-find-vm-in-api".format(
                            usage["instance_id"]
                        )
                    )
                    if CONF.debug:
                        LOG.exception(e)

                    continue

                server_start = self._get_server_start(server)
                if server_start > extract_to:
                    continue

                record = self._build_record(server)
                acc_records = self._build_acc_records(
                    server, record, extract_from, extract_to
                )
                self.acc_records.update(acc_records)

                server_start = record.start_time

                # End time must ben the time when the machine was ended, but it
                # may be none
                if usage.get("ended_at", None) is not None:
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

                self.records[server.id] = record

            # Adjust resources that may not be
            record = self.records[usage["instance_id"]]
            record.memory = usage["memory_mb"]
            record.cpu_count = usage["vcpus"]
            record.disk = usage["local_gb"]

    def extract(self, extract_from, extract_to):
        """Extract records for a project from given date querying nova.

        This method will get information from nova.

        :param project: Project to extract records for.
        :param extract_from: datetime.datetime object indicating the date to
                             extract records from
        :param extract_to: datetime.datetime object indicating the date to
                           extract records to
        :returns: A list of records
        """
        # Some API calls do not expect a TZ, so we have to remove the timezone
        # from the dates. We assume that all dates coming from upstream are
        # in UTC TZ.
        extract_from = extract_from.replace(tzinfo=None)
        extract_to = extract_to.replace(tzinfo=None)

        # Our records
        self.records = {}
        self.acc_records = {}

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
        servers = self._get_servers(extract_from)
        # 2.- Build the records for the period. Drop servers outside the period
        # (we do this manually as we cannot limit the query to a period, only
        # changes after start date).
        self._process_servers_for_period(servers, extract_from, extract_to)

        # 3.- Get all the usages for the period
        usages = self._get_usages(extract_from, extract_to)
        # 4.- Iter over the results and
        # This one will also generate accelerator records if GPU flavors
        # are found.
        self._process_usages_for_period(usages, extract_from, extract_to)

        return list(self.records.values()) + list(self.acc_records.values())
