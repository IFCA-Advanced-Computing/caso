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

========
Usage
========

command line
------------

``cASO`` provides the ``caso-extract`` command to generate new records from
your OpenStack deployment.
``caso-extract -h`` will show a complete list of available arguments.

Use the ``--extract-from`` argument to specify the date from when the records
should be extracted. If no value is set, then ``cASO`` will extract the records
from the last run. If equal to "None", then extract records from the beggining
of time.  If not time zone is specified, UTC will be used.

.. important::
   If you are running an OpenStack Nova version lower than Kilo there is a
   `bug <https://bugs.launchpad.net/nova/+bug/1398086>`_ in its API, making
   impossible to paginate over deleted results.

   Since nova is limiting the results to 1000 by default, if you are expecting
   more than 1000 results you will get just the last 1000.  This is important
   if you are publishing data for the first time, or if you are republishing
   all your accounting). If this is your case, adjust the ``osapi_max_limit``
   to a larger value in ``/etc/nova/nova.conf``.

Running as a cron job
---------------------

The best way of running ``cASO`` is via a cron job like the following::

    10 * * * * caso-extract

Migration from OSSSM
--------------------

If you had a previous installation of osssm, you can migrate to ``cASO``
following these steps:

#. Remove the previous osssm installation (e.g. remove ``apel-ssm-openstack`` rpm).
#. Remove any cron jobs related to ``osssm.extract`` or ``osssm.push``, a single
   cron job as described above is enough. You should keep the cron job that executes
   ``ssmsend``, this is still needed to send the records to the accounting database.
