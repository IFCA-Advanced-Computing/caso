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

"""Cloud extractors for cASO."""

import importlib
import typing

if typing.TYPE_CHECKING:
    from caso.extract.openstack.nova import NovaExtractor  # noqa: F401
    from caso.extract.openstack.cinder import CinderExtractor  # noqa: F401
    from caso.extract.openstack.neutron import NeutronExtractor  # noqa: F401
    from caso.extract.prometheus import EnergyConsumptionExtractor  # noqa: F401

# NOTE: the extractors are imported lazily (PEP 562), as importing them pulls in
# all the OpenStack and Prometheus client libraries.
_EXTRACTORS = {
    "NovaExtractor": "caso.extract.openstack.nova",
    "CinderExtractor": "caso.extract.openstack.cinder",
    "NeutronExtractor": "caso.extract.openstack.neutron",
    "EnergyConsumptionExtractor": "caso.extract.prometheus",
}

__all__ = list(_EXTRACTORS)


def __getattr__(name):
    """Import the requested extractor lazily."""
    try:
        module = _EXTRACTORS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module), name)
