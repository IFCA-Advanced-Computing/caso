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
import os
import os.path

import dateutil.parser
from dateutil import tz
from oslo_concurrency import lockutils
from oslo_config import cfg

import caso.extract.manager
import caso.messenger
from caso import utils

opts = [
    cfg.ListOpt('messengers',
                default=['caso.messenger.noop.NoopMessenger'],
                help='List of messenger that will dispatch records. '
                'valid values are %s' %
                ["%s.%s" % (i.__module__, i.__name__)
                 for i in caso.messenger.all_managers()]),
    cfg.StrOpt('spooldir',
               default='/var/spool/caso',
               help='Spool directory.'),
]

override_lock = cfg.StrOpt(
    "lock_path",
    default=os.environ.get("CASO_LOCK_PATH", "$spooldir"),
    help="Directory to use for lock files. For security, the specified "
         "directory should only be writable by the user running the "
         "processes that need locking. Defaults to environment variable "
         "CASO_LOCK_PATH or $spooldir"
)
opts.append(override_lock)

cli_opts = [
    cfg.BoolOpt('dry-run',
                deprecated_name='dry_run',
                default=False,
                help='Extract records but do not push records to SSM. This '
                'will not update the last run date.'),
]

CONF = cfg.CONF

CONF.register_opts(opts)
CONF.register_cli_opts(cli_opts)


class Manager(object):
    def __init__(self):
        utils.makedirs(CONF.spooldir)
        self.last_run_file = os.path.join(CONF.spooldir, "lastrun")

        self.extractor_manager = caso.extract.manager.Manager()
        self.messenger = caso.messenger.Manager()

        self.lock_path = CONF.lock_path

    @property
    def lastrun(self):
        if os.path.exists(self.last_run_file):
            with open(self.last_run_file, "r") as fd:
                date = fd.read()
        else:
            date = "1970-01-01"

        try:
            date = dateutil.parser.parse(date)
        except Exception:
            # FIXME(aloga): raise a proper exception here
            raise
        return date

    def run(self):
        @lockutils.synchronized("caso_should_not_run_in_parallel",
                                lock_path=self.lock_path, external=True)
        def synchronized():
            records = self.extractor_manager.get_records(lastrun=self.lastrun)
            if not CONF.dry_run:
                self.messenger.push_to_all(records)
                with open(self.last_run_file, "w") as fd:
                    fd.write(str(datetime.datetime.now(tz.tzutc())))

        return synchronized()
