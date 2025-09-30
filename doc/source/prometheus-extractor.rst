# Prometheus Extractor for Energy Consumption Metrics

This document provides information on using the Prometheus extractor to gather energy consumption metrics in cASO.

## Overview

The Prometheus extractor queries a Prometheus instance to retrieve energy consumption metrics for each VM in the configured projects and generates `EnergyRecord` objects that can be published through cASO's messenger system.

## Configuration

To use the Prometheus extractor, add the following configuration to your `caso.conf` file:

```ini
[DEFAULT]
# Add prometheus to your list of extractors
extractor = nova,cinder,prometheus

[prometheus]
# Prometheus server endpoint URL
prometheus_endpoint = http://localhost:9090

# PromQL query to retrieve energy consumption in kWh
# Use {{uuid}} as a template variable for the VM UUID
prometheus_query = sum(rate(libvirt_domain_info_energy_consumption_joules_total{uuid=~"{{uuid}}"}[5m])) * 300 / 3600000

# Timeout for Prometheus API requests (in seconds)
prometheus_timeout = 30
```

## How It Works

The Prometheus extractor:

1. **Scans VMs**: Retrieves the list of VMs from Nova for each configured project
2. **Queries Per VM**: For each VM, executes a customizable Prometheus query
3. **Template Variables**: Replaces `{{uuid}}` in the query with the actual VM UUID
4. **Creates Records**: Generates an `EnergyRecord` for each VM with energy consumption data

## Customizing the PromQL Query

The query template can use `{{uuid}}` as a placeholder for the VM UUID. The default query assumes you have energy consumption metrics labeled with the VM UUID.

### Example Queries

**For libvirt domain energy metrics:**
```promql
sum(rate(libvirt_domain_info_energy_consumption_joules_total{uuid=~"{{uuid}}"}[5m])) * 300 / 3600000
```

**For per-VM IPMI power metrics:**
```promql
avg_over_time(ipmi_power_watts{instance=~".*{{uuid}}.*"}[5m]) * 5 * 60 / 1000 / 3600
```

**For VM-specific RAPL energy metrics:**
```promql
sum(rate(node_rapl_package_joules_total{vm_uuid="{{uuid}}"}[5m])) * 300 / 3600000
```

**For Scaphandre per-process metrics:**
```promql
sum(rate(scaph_process_power_consumption_microwatts{exe=~".*qemu.*",cmdline=~".*{{uuid}}.*"}[5m])) * 300 / 1000000 / 3600
```

## Energy Record Format

The Prometheus extractor generates `EnergyRecord` objects with the following fields:

- `uuid`: Unique identifier for the record
- `measurement_time`: Timestamp when the measurement was taken
- `site_name`: Name of the site (from configuration)
- `user_id`: User identifier (optional for energy records)
- `group_id`: Project/group identifier
- `user_dn`: User Distinguished Name (optional)
- `fqan`: Fully Qualified Attribute Name (VO mapping)
- `energy_consumption`: Energy consumption value (in kWh)
- `energy_unit`: Unit of measurement (default: "kWh")
- `compute_service`: Service name (from configuration)

## Integration with Messengers

Energy records can be published through any cASO messenger, just like other record types:

```ini
[DEFAULT]
messengers = ssm,logstash
```

The records will be serialized as JSON with field mapping according to the accounting standards.

## Testing

To test your Prometheus extractor configuration:

1. Verify Prometheus is accessible from cASO
2. Test your PromQL query directly in Prometheus UI with a sample UUID
3. Run cASO with the `--dry-run` option to preview records without publishing
4. Check the logs for any errors or warnings

## Example

Here's a complete example configuration:

```ini
[DEFAULT]
extractor = prometheus
site_name = MY-SITE
service_name = MY-SITE-CLOUD
messengers = ssm

[prometheus]
prometheus_endpoint = http://prometheus.example.com:9090
prometheus_query = sum(rate(libvirt_domain_info_energy_consumption_joules_total{uuid=~"{{uuid}}"}[5m])) * 300 / 3600000
prometheus_timeout = 30

[ssm]
output_path = /var/spool/apel/outgoing/openstack
```

## Troubleshooting

**No records extracted:**
- Verify Prometheus is accessible
- Check that your query returns results in Prometheus UI (replace {{uuid}} with an actual VM UUID)
- Ensure the time range (extract_from/extract_to) covers periods with data
- Verify VMs exist in the configured projects

**Connection timeout:**
- Increase `prometheus_timeout` value
- Check network connectivity to Prometheus
- Verify Prometheus is not overloaded

**Invalid query results:**
- Ensure your query returns numeric values
- Check the query format matches PromQL syntax
- Verify the metrics exist in your Prometheus instance for the VMs
- Test the query with a real VM UUID in Prometheus UI

**No VMs found:**
- Verify the projects are correctly configured in cASO
- Check that VMs exist in the OpenStack environment
- Ensure cASO has proper credentials to query Nova
