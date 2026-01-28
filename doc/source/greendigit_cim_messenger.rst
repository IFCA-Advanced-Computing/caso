GreenDIGIT CIM Messenger
========================

This document provides information on using the GreenDIGIT CIM messenger to publish
energy consumption metrics in cASO.

Overview
--------

The GreenDIGIT CIM messenger sends `EnergyRecord` objects to the GreenDIGIT
Common Information Model (CIM) Service. The messenger supports authentication
via bearer token and allows publishing energy consumption data from cASO extractors
to SZTAKI CIM endpoints.

Configuration
-------------

To use the GreenDIGIT CIM messenger, add the following configuration to your
`caso.conf` file:

```ini
[DEFAULT]
# Add the messenger to your list of messengers
messengers = greendigit_cim

[greendigit_cim]
# SZTAKI GreenDIGIT CIM authentication endpoint (GET method)
get_token_url = https://greendigit-cim.sztaki.hu/gd-kpi-api/token

# SZTAKI GreenDIGIT CIM endpoint to publish energy records
publish_url = https://greendigit-cim.sztaki.hu/gd-kpi-api/submit
```
Environment Variables
---------------------

The GreenDIGIT CIM messenger requires the following environment variables
to be set for authentication:

- `GREENDIGIT_CIM_EMAIL`: The email address used for authentication.
- `GREENDIGIT_CIM_PASSWORD`: The password associated with the email address.

How it Works
------------

The GreenDIGIT CIM messenger performs the following steps:

1. **Authenticate**: Uses the configured get_token_url and the credentials from environment variables to obtain a bearer token.
2. **Serialize Records**: Converts EnergyRecord objects to JSON using field mappings consistent with cASO standards.
3. **Publish Records**: Sends the JSON payload to publish_url via HTTP POST with the bearer token in the Authorization header.

Testing
-------

To test the messenger:

1. Verify that the SZTAKI CIM endpoints are reachable from the host running cASO.
2. Ensure environment variables GREENDIGIT_CIM_EMAIL and GREENDIGIT_CIM_PASS are set.
3. Run cASO in --dry-run mode to preview EnergyRecord objects without publishing.
4. Check logs for successful publication messages or errors.

Troubleshooting
---------------

**Authentication errors:**

- Ensure credentials are correct
- Verify network connectivity to get_token_url
- Ensure the endpoint accepts GET requests

**Publishing errors:**

- Check that publish_url is reachable
- Validate that JSON serialization of EnergyRecord is correct
- Review HTTP status codes in logs for hints

**No records published:**

- Ensure extractors have generated EnergyRecord objects
- Confirm that the messenger is listed in messengers in [DEFAULT]

Technical Details
-----------------

- Uses bearer token authentication
- Records are serialized using model_dump_json with aliases and excluding None values
- HTTP POST to publish_url includes JSON array of EnergyRecord objects
- Logs the number of records sent and HTTP response status

Future Updates
----------------

- SZTAKI CIM may update base URLs or endpoints; configuration via caso.conf allows easy updates without code changes.
- Verify SSL support and endpoint availability for production deployments.
