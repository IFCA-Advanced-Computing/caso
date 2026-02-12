Prometheus Extractor for Energy Consumption Metrics
====================================================

This document provides information on using the Prometheus extractor to gather energy consumption metrics in cASO.

Overview
--------

The Prometheus extractor queries a Prometheus instance to retrieve energy consumption metrics for each VM in the configured projects and generates ``EnergyRecord`` objects that can be published through cASO's messenger system.

The extractor uses the ``prometheus-api-client`` library to connect to Prometheus and calculate energy consumption in Watt-hours (Wh) from instantaneous power samples stored in Prometheus.

Configuration
-------------

To use the Prometheus extractor, add the following configuration to your ``caso.conf`` file:

.. code-block:: ini

   [DEFAULT]
   # Add prometheus to your list of extractors
   extractor = nova,cinder,prometheus

   [prometheus]
   # Prometheus server endpoint URL
   prometheus_endpoint = http://localhost:9090

   # Name of the Prometheus metric to query
   prometheus_metric_name = prometheus_value

   # Name of the label that matches the VM UUID
   vm_uuid_label_name = uuid

   # List of label filters as key:value pairs
   labels = type_instance:scaph_process_power_microwatts

   # Frequency between samples in seconds
   prometheus_step_seconds = 30

   # Whether to verify SSL when connecting to Prometheus
   prometheus_verify_ssl = true

How It Works
------------

The Prometheus extractor:

1. **Scans VMs**: Retrieves the list of VMs from Nova for each configured project
2. **Queries Per VM**: For each VM, executes a Prometheus query using the configured metric name and labels
3. **Builds Labels**: Combines the configured label filters with the VM UUID label (e.g., ``{type_instance="scaph_process_power_microwatts", uuid="vm-uuid"}``)
4. **Calculates Energy**: Uses the formula ``sum_over_time(metric_name{labels}[query_range]) * (step_seconds/3600) / 1000000`` to convert microwatt power samples to Watt-hours
5. **Creates Records**: Generates an ``EnergyRecord`` for each VM with energy consumption data and execution metrics

Configuration Parameters
------------------------

- **prometheus_endpoint**: URL of the Prometheus server (default: ``http://localhost:9090``)
- **prometheus_metric_name**: Name of the metric to query (default: ``prometheus_value``)
- **vm_uuid_label_name**: Name of the label that matches the VM UUID in Prometheus metrics (default: ``uuid``)
- **labels**: List of label filters as ``key:value`` pairs to filter the Prometheus metric. The VM UUID label will be added automatically (default: ``["type_instance:scaph_process_power_microwatts"]``)
- **prometheus_step_seconds**: Frequency between samples in the time series, in seconds (default: ``30``)
- **prometheus_verify_ssl**: Whether to verify SSL certificates when connecting to Prometheus (default: ``true``)

Example Configurations
----------------------

For Scaphandre Energy Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scaphandre exports energy metrics in microwatts:

.. code-block:: ini

   [prometheus]
   prometheus_endpoint = http://prometheus.example.com:9090
   prometheus_metric_name = prometheus_value
   vm_uuid_label_name = uuid
   labels = type_instance:scaph_process_power_microwatts
   prometheus_step_seconds = 30
   prometheus_verify_ssl = false

For Custom Energy Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~

If you have custom energy metrics with different labels:

.. code-block:: ini

   [prometheus]
   prometheus_endpoint = http://prometheus.example.com:9090
   prometheus_metric_name = my_custom_power_metric
   vm_uuid_label_name = instance_id
   labels = environment:production,datacenter:dc1
   prometheus_step_seconds = 60
   prometheus_verify_ssl = true

For Multiple Label Filters
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify multiple label filters:

.. code-block:: ini

   [prometheus]
   prometheus_endpoint = http://prometheus.example.com:9090
   prometheus_metric_name = node_power_watts
   vm_uuid_label_name = vm_uuid
   labels = type_instance:power_consumption,source:ipmi,rack:rack42
   prometheus_step_seconds = 30
   prometheus_verify_ssl = true

Energy Record Format
--------------------

The Prometheus extractor generates ``EnergyRecord`` objects with the following fields:

- ``ExecUnitID``: VM UUID
- ``StartExecTime``: Start time of the measurement period (ISO 8601 format)
- ``EndExecTime``: End time of the measurement period (ISO 8601 format)
- ``EnergyWh``: Energy consumption in Watt-hours (normalized with CPU normalization factor)
- ``Work``: CPU duration divided by EnergyWh
- ``Efficiency``: CPU duration divided by (wall clock time × vCPUs)
- ``WallClockTime_s``: Wall clock time in seconds
- ``CpuDuration_s``: CPU duration in seconds (wall time × vCPUs)
- ``SuspendDuration_s``: Suspend duration in seconds
- ``CPUNormalizationFactor``: CPU normalization factor (to account for other hardware components)
- ``ExecUnitFinished``: 1 if VM is deleted, 0 otherwise
- ``Status``: VM status (active, stopped, etc.)
- ``Owner``: VO/project owner
- ``SiteName``: Site name (from configuration)
- ``CloudComputeService``: Service name (from configuration)
- ``CloudType``: Cloud type (e.g., ``openstack``)

Integration with Messengers
---------------------------

Energy records can be published through any cASO messenger, just like other record types:

.. code-block:: ini

   [DEFAULT]
   messengers = ssm,logstash

The records will be serialized as JSON with field mapping according to the accounting standards.

Testing
-------

To test your Prometheus extractor configuration:

1. Verify Prometheus is accessible from cASO
2. Test your metric exists in Prometheus UI with a sample VM UUID
3. Run cASO with the ``--dry-run`` option to preview records without publishing
4. Check the logs for any errors or warnings

Example
-------

Here's a complete example configuration for Scaphandre metrics:

.. code-block:: ini

   [DEFAULT]
   extractor = prometheus
   site_name = MY-SITE
   service_name = MY-SITE-CLOUD
   messengers = ssm

   [prometheus]
   prometheus_endpoint = http://prometheus.example.com:9090
   prometheus_metric_name = prometheus_value
   vm_uuid_label_name = uuid
   labels = type_instance:scaph_process_power_microwatts
   prometheus_step_seconds = 30
   prometheus_verify_ssl = false

   [ssm]
   output_path = /var/spool/apel/outgoing/openstack

Troubleshooting
---------------

**No records extracted:**

- Verify Prometheus is accessible
- Check that your metric exists in Prometheus UI
- Ensure the metric has data for the configured time range
- Verify VMs exist in the configured projects
- Check that the metric has the required labels (those specified in ``labels`` config and the VM UUID label specified by ``vm_uuid_label_name``)

**Connection timeout:**

- Check network connectivity to Prometheus
- Verify Prometheus is not overloaded
- If using SSL, ensure certificates are valid or set ``prometheus_verify_ssl = false``

**Invalid query results:**

- Ensure your metric contains instantaneous power values in microwatts (as reported by Scaphandre, for example)
- Check that the metric has the UUID label matching VM UUIDs (configured via ``vm_uuid_label_name``)
- Verify the label filters match your configuration
- Test the query in Prometheus UI:

.. code-block:: text

   sum_over_time(prometheus_value{type_instance="scaph_process_power_microwatts", uuid="<vm-uuid>"}[1h])

**No VMs found:**

- Verify the projects are correctly configured in cASO 
- Check that VMs exist in the OpenStack environment
- Ensure cASO has proper credentials to query Nova

Technical Details
-----------------

The energy calculation uses the following formula:

.. code-block:: text

   energy_wh = sum_over_time(metric{labels}[range]) * (step_seconds / 3600) / 1000000

Where:

- ``step_seconds / 3600`` converts µW·s to µWh
- Division by ``1000000`` converts µWh to Wh

This approach works with metrics that export instantaneous power consumption in microwatts, sampled at the configured frequency.
