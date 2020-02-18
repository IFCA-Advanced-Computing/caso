# -*- coding: utf-8 -*-

# Copyright 2019 Spanish National Research Council (CSIC)
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

import stevedore

from caso import exception

EXTRACTOR_NAMESPACE = "caso.extractors"
MESSENGER_NAMESPACE = "caso.messenger"


def _get_names(what):
    mgr = stevedore.ExtensionManager(namespace=what)
    return frozenset(mgr.names())


def _get(what):
    mgr = stevedore.ExtensionManager(namespace=what,
                                     propagate_map_exceptions=True)

    return dict(mgr.map(lambda ext: (ext.entry_point.name, ext.plugin)))


def get_available_extractor_names():
    """Get the names of all the extractors that are available on the system.

    :returns: A list of names.
    :rtype: frozenset
    """
    return _get_names(EXTRACTOR_NAMESPACE)


def get_available_extractors():
    """Retrieve all the extractors available on the system.

    :returns: A dict with the entrypoint name as the key and the extractor
              as the value.
    :rtype: dict
    """
    return _get(EXTRACTOR_NAMESPACE)


def get_available_messenger_names():
    """Get the names of all the messengers that are available on the system.

    :returns: A list of names.
    :rtype: frozenset
    """
    return _get_names(MESSENGER_NAMESPACE)


def get_available_messengers():
    """Retrieve all the messengers available on the system.

    :returns: A dict with the entrypoint name as the key and the messenger
              as the value.
    :rtype: dict
    """
    return _get(MESSENGER_NAMESPACE)


def get_enabled_messengers(names):
    """Retrieve all the enabled messengers on the system.

    :returns: An extension manager.
    """

    def cb(names):
        raise exception.MessengerNotFound(names=",".join(list(names)))

    mgr = stevedore.NamedExtensionManager(namespace=MESSENGER_NAMESPACE,
                                          names=names,
                                          name_order=True,
                                          on_missing_entrypoints_callback=cb,
                                          invoke_on_load=True,
                                          propagate_map_exceptions=True)
    return mgr
