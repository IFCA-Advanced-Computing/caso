..
      Copyright 2014 Spanish National Research Council

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=======================================
cASO, an OpenStack Accounting extractor
=======================================

``cASO`` is an accounting reporter (currently supports `Cloud Accounting Usage Records
<https://wiki.egi.eu/wiki/Fedcloud-tf:WorkGroups:Scenario4#Cloud_Accounting_Usage_Record>`_)
for OpenStack deployments. ``cASO`` gets usage information from OpenStack
public APIs (no access to DB is required) and can generate valid
output for `Apel SSM <https://wiki.egi.eu/wiki/APEL>`_ or `logstash <http://logstash.net/>`_.

.. image:: /static/caso-diagram.png


Contents:

.. toctree::
   :maxdepth: 1

   release-notes
   installation
   configuration
   configuration-file
   multi-region
   usage
   troubleshooting
