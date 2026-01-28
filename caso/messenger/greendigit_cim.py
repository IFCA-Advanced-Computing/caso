# -*- coding: utf-8 -*-

# Copyright 2026 Spanish National Research Council (CSIC)
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

"""Messenger to publish EnergyRecord objects to GreenDIGIT CIM Service."""

import json
import os

import requests
from oslo_config import cfg
from oslo_log import log

import caso.messenger
from caso.record import EnergyRecord


# ----------------------------------------------------------------------
# Configuration options
# ----------------------------------------------------------------------

opts = [
    cfg.StrOpt(
        "get_token_url",
        default="https://greendigit-cim.sztaki.hu/gd-kpi-api/token",
        help="GreenDIGIT CIM authentication endpoint (Bearer token). Use GET method.",
    ),
    cfg.StrOpt(
        "publish_url",
        default="https://greendigit-cim.sztaki.hu/gd-kpi-api/submit",
        help="GreenDIGIT CIM endpoint to publish energy records.",
    ),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="greendigit_cim")

LOG = log.getLogger(__name__)


def get_token(email: str, password: str) -> str:
    """Obtain a Bearer token from GreenDIGIT CIM Service using GET method."""

    url = CONF.greendigit_cim.get_token_url
    headers = {"Content-Type": "application/json"}
    params = {"email": email, "password": password}

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()

    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise ValueError("Token not found in GreenDIGIT CIM response")

    return token


class GreenDIGITEnergyMessenger(caso.messenger.BaseMessenger):
    """Messenger to send EnergyRecord objects to GreenDIGIT CIM Service."""

    def __init__(self):
        super(GreenDIGITEnergyMessenger, self).__init__()
        self.publish_url = CONF.greendigit_cim.publish_url

    def push(self, records):
        """Send a list of EnergyRecords to GreenDIGIT CIM Service."""

        email = os.environ.get("GREENDIGIT_CIM_EMAIL")
        password = os.environ.get("GREENDIGIT_CIM_PASSWORD")

        if not email or not password:
            raise ValueError(
                "Environment variables GREENDIGIT_CIM_EMAIL and "
                "GREENDIGIT_CIM_PASSWORD must be set"
            )

        token = get_token(email, password)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        output = [
            json.loads(r.model_dump_json(by_alias=True, exclude_none=True))
            for r in records
        ]

        resp = requests.post(self.publish_url, headers=headers, json=output)
        resp.raise_for_status()

        LOG.info(
            "Published %d records to GreenDIGIT CIM (%s), status=%s",
            len(output),
            self.publish_url,
            resp.status_code,
        )
