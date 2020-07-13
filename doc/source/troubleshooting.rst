..
      Copyright 2015 Spanish National Research Council

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============
Troubleshooting
===============

Cannot-find-VM-in-API
---------------------

.. DANGER::
   There is not a single recipe to fix this issue, and this involves touching
   and modifying the DB directly. We reccomend that you ignore these messages,
   unless you know what you are doing.

In the logs you can see the following warnings (caso version < 1.4.4)::

    WARNING caso.extract.nova [-] Cannot get server '072e77c0-4295-4a83-9bdf-6afde796a00d' from the Nova API, probably because it is an old VM that whose metadata is wrong in the DB. There will be no record generated for this VM. : NotFound: Instance 072e77c0-4295-4a83-9bdf-6afde796a00d could not be found. (HTTP 404) (Request-ID: req-8eabf5d8-b722-4ee4-b211-aec36fc0499e)

Or the following one (caso version >= 1.4.4 )::

    WARNING caso.extract.nova [-] Cannot get server '072e77c0-4295-4a83-9bdf-6afde796a00d' from the Nova API, probably because it is an error in the DB. Please refer to the following page for more details: https://caso.readthedocs.io/en/stable/troubleshooting.html#Cannot-find-VM-in-API

These errors are caused by a VM that is in a bad state on the DB. The
``os-simple-tenant-usage`` API is returning instances that cannot be obtained
from the API.

This may be caused by any of the following cases:

 1. VMs that have changed their status on a date that enters into the extrating period.
 2. VMs that are terminated and deleted, but their status is incorrect (i.e. no
 value for ``terminated_at``). This can be fixed by setting a ``terminated_at``
 value that is correct, directly in the DB.
