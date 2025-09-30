# Prometheus Extractor for Energy Consumption Metrics

This document provides information on using the Prometheus extractor to gather energy consumption metrics in cASO.

## Overview

The Prometheus extractor queries a Prometheus instance to retrieve energy consumption metrics and generates `EnergyRecord` objects that can be published through cASO's messenger system.

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
# This is the default query - customize it based on your Prometheus metrics
prometheus_query = sum(rate(node_energy_joules_total[5m])) * 300 / 3600000

# Timeout for Prometheus API requests (in seconds)
prometheus_timeout = 30
```

## Customizing the PromQL Query

The default query assumes you have a metric called `node_energy_joules_total` that tracks energy consumption in joules. The query:

1. Calculates the rate of energy consumption over 5 minutes
2. Multiplies by 300 (5 minutes in seconds) to get total joules
3. Divides by 3,600,000 to convert from joules to kWh

You should customize this query based on your specific Prometheus metrics and requirements.

### Example Queries

**For IPMI power metrics:**
```promql
sum(ipmi_power_watts) * 5 * 60 / 1000 / 3600
```

**For RAPL energy metrics:**
```promql
sum(rate(node_rapl_package_joules_total[5m])) * 300 / 3600000
```

**For Scaphandre metrics:**
```promql
sum(rate(scaph_host_power_microwatts[5m])) * 300 / 1000000 / 3600
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
2. Test your PromQL query directly in Prometheus
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
prometheus_query = sum(rate(node_energy_joules_total[5m])) * 300 / 3600000
prometheus_timeout = 30

[ssm]
output_path = /var/spool/apel/outgoing/openstack
```

## Troubleshooting

**No records extracted:**
- Verify Prometheus is accessible
- Check that your query returns results in Prometheus UI
- Ensure the time range (extract_from/extract_to) covers periods with data

**Connection timeout:**
- Increase `prometheus_timeout` value
- Check network connectivity to Prometheus
- Verify Prometheus is not overloaded

**Invalid query results:**
- Ensure your query returns numeric values
- Check the query format matches PromQL syntax
- Verify the metrics exist in your Prometheus instance
