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

Available options
=================

Apart from other options, the following ones are the ones that specify how to
extract accountig records:

.. option:: --config-dir DIR

  Path to a config directory to pull `*.conf` files from. This file set is
  sorted, so as to provide a predictable parse order if individual options are
  over-ridden. The set is parsed after the file(s) specified via previous
  --config-file, arguments hence over-ridden options in the directory take
  precedence.  This option must be set from the command-line.

.. option:: --config-file PATH

  Path to a config file to use. Multiple config files can be specified, with
  values in later files taking precedence. Defaults to None. This option must
  be set from the command-line.

.. option:: --debug, -d

  If set to true, the logging level will be set to DEBUG
                        instead of the default INFO level.

.. option:: --dry-run, --dry_run

  Extract records but do not push records to SSM. This will not update the last
  run date.

.. option:: --extract-from EXTRACT_FROM, --extract_from EXTRACT_FROM

   Extract records that have changed after this date.  This means that if a
   record has started before this date, and it has changed after this date
   (i.e. it is still running or it has ended) it will be reported. If it is not
   set, extract records from last run. If it is set to None and last run file
   is not present, it will extract records from the beginning of time. If no
   time zone is specified, UTC will be used.

.. option:: --extract-to EXTRACT_TO, --extract_to EXTRACT_TO

   Extract record changes until this date. If it is not set, we use now. If a
   server has ended after this date, it will be included, but the consuption
   reported will end on this date. If no time zone is specified, UTC will be
   used.
.. option:: --extractor EXTRACTOR

   Which extractor to use for getting the data. If you do not specify anything,
   nova will be used. Allowed values: nova

.. option:: --projects PROJECTS, --tenants PROJECTS

   List of projects to extract accounting records from.

Running as a cron job
---------------------

The best way of running ``cASO`` is via a cron job like the following::

    10 * * * * caso-extract
