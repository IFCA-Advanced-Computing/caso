# -*- coding: utf-8 -*-

# Copyright 2015 Spanish National Research Council (CSIC)
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

"""Module defining all the options to be managed by oslo."""

import itertools

import caso.extract.base
import caso.extract.manager
import caso.extract.openstack.nova
import caso.extract.prometheus
import caso.keystone_client
import caso.loading
import caso.manager
import caso.messenger
import caso.messenger.logstash
import caso.messenger.ssm


def list_opts():
    """Get the list of all configured options."""
    opts = [
        (
            "DEFAULT",
            itertools.chain(
                caso.manager.opts,
                caso.manager.cli_opts,
                caso.extract.base.opts,
                caso.extract.manager.cli_opts,
            ),
        ),
        ("accelerator", caso.extract.openstack.nova.accelerator_opts),
        ("benchmark", caso.extract.openstack.nova.benchmark_opts),
        ("keystone_auth", caso.keystone_client.opts),
        ("logstash", caso.messenger.logstash.opts),
        ("prometheus", caso.extract.prometheus.opts),
        ("ssm", caso.messenger.ssm.opts),
    ]

    # Add messenger-specific record_types options for all available messengers
    for messenger_name in caso.loading.get_available_messenger_names():
        group_name = f"messenger_{messenger_name}"
        opts.append((group_name, caso.messenger.get_messenger_opts(messenger_name)))

    return opts
