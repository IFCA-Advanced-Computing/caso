# -*- coding: utf-8 -*-
# Copyright 2026 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations
# under the License.

"""Messenger to publish EnergyRecord objects to GreenDIGIT CIM Service."""

import json
import socket
import ssl
from urllib.parse import urlparse

import requests
from oslo_config import cfg
from oslo_log import log

import caso.messenger

# ----------------------------------------------------------------------
# Configuration options
# ----------------------------------------------------------------------
opts = [
    cfg.StrOpt(
        "base_url",
        default="https://greendigit-cim.sztaki.hu",
        help="Base URL of GreenDIGIT CIM Service",
    ),
    cfg.StrOpt(
        "email",
        default=None,
        help="Email for GreenDIGIT CIM authentication.",
    ),
    cfg.StrOpt(
        "password",
        default=None,
        help="Password for GreenDIGIT CIM authentication.",
    ),
    cfg.BoolOpt(
        "verify_ssl",
        default=True,
        help="Whether to verify SSL certificates when connecting to GreenDIGIT CIM.",
    ),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="greendigit_cim")

LOG = log.getLogger(__name__)


def get_token(email: str, password: str, token_url: str) -> str:
    """Obtain a Bearer token from GreenDIGIT CIM Service."""
    params = {"email": email, "password": password}

    resp = requests.get(token_url, params=params, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise ValueError("Token not found in GreenDIGIT CIM response")

    return token


class GreenDIGITEnergyMessenger(caso.messenger.BaseMessenger):
    """Messenger to send EnergyRecord objects to GreenDIGIT CIM Service."""

    def __init__(self):
        """Initialize the messenger."""
        super().__init__()
        base = CONF.greendigit_cim.base_url.rstrip("/")
        self.token_url = f"{base}/gd-cim-api/v1/token"
        self.publish_url = f"{base}/gd-cim-api/v1/submit"

        self.email = CONF.greendigit_cim.email
        self.password = CONF.greendigit_cim.password

        if not self.email or not self.password:
            raise ValueError(
                "greendigit_cim.email and greendigit_cim.password "
                "must be set in configuration"
            )

    def _verify_tls(self, url: str, timeout: int = 10):
        """Check that the HTTPS endpoint has a valid TLS/SSL certificate."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            LOG.warning("Skipping TLS verification for non-HTTPS URL: %s", url)
            return

        host = parsed.hostname
        port = parsed.port or 443
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        raise ConnectionError(f"No SSL certificate presented by {host}")
                    LOG.info(
                        "SSL certificate for %s is valid. Subject: %s",
                        host,
                        cert.get("subject"),
                    )
        except (ssl.SSLError, socket.error) as e:
            raise ConnectionError(f"TLS verification failed for {url}: {e}")

    def push(self, records):
        """Send a list of EnergyRecord objects to GreenDIGIT CIM Service."""
        if CONF.greendigit_cim.verify_ssl:
            self._verify_tls(self.publish_url)

        token = get_token(self.email, self.password, self.token_url)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = [
            json.loads(r.model_dump_json(by_alias=True, exclude_none=True))
            for r in records
        ]

        resp = requests.post(
            self.publish_url, headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()

        LOG.info(
            "Published %d records to GreenDIGIT CIM (%s), status=%s",
            len(payload),
            self.publish_url,
            resp.status_code,
        )
