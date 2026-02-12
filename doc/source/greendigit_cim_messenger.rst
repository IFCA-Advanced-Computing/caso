GreenDIGIT CIM Messenger
========================

This document provides information on using the GreenDIGIT CIM messenger to publish
energy consumption metrics in cASO.

Overview
--------

The GreenDIGIT CIM messenger sends ``EnergyRecord`` objects to the GreenDIGIT
Common Information Model (CIM) Service. The messenger supports authentication
via bearer token and allows publishing energy consumption data from cASO extractors
to SZTAKI CIM endpoints.

Additionally, the messenger verifies SSL certificates and endpoint availability
before publishing to ensure reliability in production environments.

Configuration
-------------

To use the GreenDIGIT CIM messenger, add the following configuration to your
``caso.conf`` file:

.. code-block:: ini

   [DEFAULT]
   # Add the messenger to your list of messengers
   messengers = greendigit_cim

   [greendigit_cim]
   # Base URL of SZTAKI GreenDIGIT CIM Service.
   # Specific endpoints for authentication (/gd-cim-api/v1/token) and publishing (/gd-cim-api/v1/submit)
   # will be constructed internally by the messenger.
   base_url = https://greendigit-cim.sztaki.hu

   # Credentials used to obtain the bearer token
   email = user@example.org
   password = secret-password

   # SSL verification (recommended for production)
   verify_ssl = true

   [messenger_greendigit_cim]
   # Only energy records will be published to this messenger
   record_types = energy

How it Works
------------

The GreenDIGIT CIM messenger performs the following steps:

1. **Verify Endpoints**: Checks that the authentication and publishing endpoints are reachable and that SSL certificates are valid.
2. **Authenticate**: Uses the configured base URL and the credentials provided in ``caso.conf`` to obtain a bearer token from ``/gd-cim-api/v1/token``.
3. **Serialize Records**: Converts ``EnergyRecord`` objects to JSON using field mappings consistent with cASO standards.
4. **Publish Records**: Sends the JSON payload to ``/gd-cim-api/v1/submit`` via HTTP POST with the bearer token in the ``Authorization`` header.
5. **Logging**: Records the number of published records and HTTP response status.

Testing
-------

To test the messenger:

1. Verify that the SZTAKI CIM endpoints are reachable from the host running cASO.
2. Ensure the credentials are correctly set in ``caso.conf``.
3. Run cASO in ``--dry-run`` mode to preview ``EnergyRecord`` objects without publishing.
4. Check logs for successful publication messages or errors.

Troubleshooting
---------------

**Authentication errors:**

- Ensure credentials are correct.
- Verify network connectivity to ``base_url``.
- Ensure the authentication endpoint is reachable.

**Publishing errors:**

- Check that the publish endpoint is reachable.
- Validate that JSON serialization of ``EnergyRecord`` is correct.
- Review HTTP status codes in logs for hints.

**No records published:**

- Ensure extractors have generated ``EnergyRecord`` objects.
- Confirm that the messenger is listed in ``messengers`` in the ``[DEFAULT]`` section.

Technical Details
-----------------

- Uses bearer token authentication.
- Records are serialized using ``model_dump_json`` with aliases and excluding ``None`` values.
- HTTP POST to ``/gd-cim-api/v1/submit`` includes a JSON array of ``EnergyRecord`` objects.
- Verifies SSL and endpoint availability before publishing.
- Logs the number of records sent and HTTP response status.
