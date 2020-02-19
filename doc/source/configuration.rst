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

Configuration
*************

OpenStack Configuration
=======================

Apart from configuring cASO, several actions need to be performed in your
OpenStack installation in order to be able to extract accounting records.

User credentials (required)
---------------------------

In the next section you will configure an OpenStack Keystone credentials in
order to extract the records. The cASO user has to be a member of each of the
projects (another option is to convert that user in an administrator, but the
former option is a safer approach) for which it is extracting the accounting.
Otherwise, ``cASO`` will not be able to get the usages and will fail.

In order to do so, we are going to setup a new role ``accounting`` a new user
``accounting``, adding it to each of the projects with that role::

    openstack role create accounting
    openstack user create --password <password> accounting
    # For each of the projects, add the user with the accounting role
    openstack role add --user accounting --project <project> accounting

Moreover, this user needs access to Keystone so as to extract the users
information. In this case, we can can grant the user just the rights for
listing the users adding the appropriate rules in your
``/etc/keystone/policy.json`` as follows. Replace the line::

      "identity:list_users": "rule:admin_required",

with::

      "identity:list_users": "rule:admin_required or role:accounting",

Recent Keystone versions leverage a ``/etc/keystone/policy-yaml`` file, if this
is your case, substitute the line::

   "identity:list_users": "rule:admin_required"

with::

   "identity:list_users": "rule:admin_required or role:accounting"


Publishing benchmark information for OpenStack flavors (optional)
-----------------------------------------------------------------

Starting with the V0.4 of the accounting record it is possible to publish
benchmark information. In order to do so, you need to add this information to
the flavor properties and configure caso to retrieve this information. There
are two different values that need to be added to the flavor:

* The benchmark name, indicated with the ``accounting:benchmark_name`` flavor property.
* The benchmark value, indicated with the ``accounting:benchmark_value`` flavor property.

For example, if you are using HEPSPEC06 and the benchmark value is ``99`` for
the flavor ``m1.foo``, the benchmark information is configured as follows::

    openstack flavor set --property accounting:benchmark_name="HEPSPEC06" --property accounting:benchmark_value=99 m1.foo

Using different keys to specify bechmark information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you do not want to use cASO's default flavor properties ``accounting:benchmark_name`` and
``accounting:benchmark_value`` (for example because you are using different benchmark types
and values) you can specify which properties ``cASO`` should look for by using
the ``benchmark_name_key`` ``benchkark_value_key`` in the configuration file.

.. important::

    Please note that there is an OpenStack scheduler filter that removes hosts
    based on flavor properties. In order to not interfere with the behaviour of
    this filter you must prefix the property with a ``scope:`` so that cASO's
    properties are not taken into account for this filtering. When adding these
    properties in cASO's configuration file, please include the complete name
    (i.e. ``scope:property``).

cASO configuration
==================

``cASO`` uses a config file (default at ``/etc/caso/caso.conf``) with several
sections. A sample file is available at
:download:`etc/caso/caso.conf.sample <static/caso.conf.sample>`.

``[DEFAULT]`` section
---------------------

The ``[DEFAULT]`` section configures the basic behavior of ``cASO``. The sample
config file (``/etc/caso/caso.conf.sample``) includes a description
of every option. You should check at least the following options:

* ``extractor`` (default value: ``nova``), specifies which extractor to use for
  getting the data. The following APIs are supported: ``ceilomenter`` and
  ``nova``. Both should generate equivalent information.
* ``site_name`` (default value: ``<None>``). Name of the site as defined in
  GOCDB.
* ``service_name`` (default value: ``$site_name``). Name of the service within
  a site. This is used if you have several endpoints within your site.
* ``projects`` (list value, default empty). List of the projects to extract
  records from.
* ``messengers`` (list, default: ``noop``). List of the messengers to publish
  data to. Records will be pushed to all these messengers, in order. Valid
  messengers shipped with cASO are:

      * ``ssm`` for publishing APEL V0.4 records.
      * ``logstash`` for publishing to Logstash.
      * ``noop`` do nothing at all.

  Note that there might be other messengers available in the system if they are
  registered into the ``caso.messenger`` entry point namespace.
* ``mapping_file`` (default: ``/etc/caso/voms.json``). File containing the
  mapping from VOs to local projects as configured in Keystone-VOMS, in the
  form::

    {
        "VO": {
            "projects": ["foo", "bar"],
        }
    }

* ``benchmark_name_key`` and ``benchmark_value_key``. These two configuration
  options are used by ``cASO`` to retrieve the benchmark information form the
  OpenStack flavors.

``[keystone_auth]`` section
---------------------------

This section is used to specify the authentication credentials to be used to
connect to the OpenStack APIs. cASO leverages the `OpenStack keystoneauth
<https://docs.openstack.org/developer/keystoneauth/>`_ library for
authentication, so that it is possible to use any authentication plugin that is
available there (so starting on version 1.0 of cASO it is possible to use the
Keystone V3 API).

.. important::
   You need to specify the ``auth_type`` that you want to use (normally
   ``v3password`` is a good choice.

   For an exhaustive list of available plugins please refer to the
   `keystoneauth <http://docs.openstack.org/developer/keystoneauth/plugin-options.html#available-plugins>`_
   documentation.

``[ssm]`` section
-----------------

Options defined here configure the SSM messenger. There is only one option
at the moment:

* ``output_path`` (default: ``/var/spool/apel/outgoing/openstack``), directory
  to put the generated SSM records. APEL/SSM should be configured to take
  records from that directory.

``[logstash]`` section
----------------------

Options defined here configure the `logstash <https://www.elastic.co/products/logstash>`_
messenger. Available options:

* ``host`` (default: ``localhost``), host of Logstash server.
* ``port`` (default: ``5000``), Logstash server port.

Other cASO configuration options
--------------------------------

For an exhaustive list of the defined options, please check the following page:

.. toctree::
   :maxdepth: 1
   :titlesonly:

   configuration-file


