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
import os
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
        "greendigit_cim_base_url",
        default="https://greendigit-cim.sztaki.hu",
        help="Base URL of GreenDIGIT CIM Service. Specific endpoints will be constructed internally.",
    ),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="greendigit_cim")

LOG = log.getLogger(__name__)


def get_token(email: str, password: str, token_url: str) -> str:
    """Obtain a Bearer token from GreenDIGIT CIM Service using GET method."""
    headers = {"Content-Type": "application/json"}
    params = {"email": email, "password": password}

    resp = requests.get(token_url, headers=headers, params=params, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise ValueError("Token not found in GreenDIGIT CIM response")

    return token


def verify_endpoint(url: str, timeout: int = 10):
    """
    Verify that the endpoint is reachable and SSL is valid.

    Raises:
        ConnectionError if the endpoint is unreachable or SSL verification fails.
    """
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # Check SSL for HTTPS endpoints
    if parsed.scheme == "https":
        context = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    LOG.info(
                        "SSL certificate for %s is valid. Subject: %s",
                        host,
                        cert.get("subject"),
                    )
        except ssl.SSLError as e:
            raise ConnectionError(f"SSL verification failed for {url}: {e}")
        except socket.error as e:
            raise ConnectionError(f"Cannot connect to {url}: {e}")
    else:
        # For HTTP, just check TCP connectivity
        try:
            with socket.create_connection((host, port), timeout=timeout):
                LOG.info("Endpoint %s is reachable", url)
        except socket.error as e:
            raise ConnectionError(f"Cannot connect to {url}: {e}")

    # Optional: simple GET request to check HTTP status
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        LOG.info("Endpoint %s returned status %s", url, resp.status_code)
    except requests.RequestException as e:
        raise ConnectionError(f"Endpoint {url} request failed: {e}")


class GreenDIGITEnergyMessenger(caso.messenger.BaseMessenger):
    """Messenger to send EnergyRecord objects to GreenDIGIT CIM Service."""

    def __init__(self):
        """Initialize the GreenDIGIT CIM Messenger."""
        super().__init__()
        base = CONF.greendigit_cim.greendigit_cim_base_url.rstrip("/")
        self.token_url = f"{base}/gd-kpi-api/v1/token"
        self.publish_url = f"{base}/gd-kpi-api/v1/submit"

    def push(self, records):
        """Send a list of EnergyRecords to GreenDIGIT CIM Service.

        This method first verifies SSL and endpoint availability before publishing.
        """
        # Verify endpoints before sending data
        verify_endpoint(self.token_url)
        verify_endpoint(self.publish_url)

        email = os.environ.get("GREENDIGIT_CIM_EMAIL")
        password = os.environ.get("GREENDIGIT_CIM_PASSWORD")

        if not email or not password:
            raise ValueError(
                "Environment variables GREENDIGIT_CIM_EMAIL and "
                "GREENDIGIT_CIM_PASSWORD must be set"
            )

        # Obtain authentication token
        token = get_token(email, password, self.token_url)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Serialize EnergyRecord objects to JSON
        output = [
            json.loads(r.model_dump_json(by_alias=True, exclude_none=True))
            for r in records
        ]

        # Publish records
        resp = requests.post(self.publish_url, headers=headers, json=output, timeout=60)
        resp.raise_for_status()

        LOG.info(
            "Published %d records to GreenDIGIT CIM (%s), status=%s",
            len(output),
            self.publish_url,
            resp.status_code,
        )
