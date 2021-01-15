=========================
cASO multi-region support
=========================

* In case the monitored projects rely on a specific region, define the
  following variable in the /etc/caso/caso.conf

.. code-block:: bash

  [DEFAULT]
  region_name = <REGION>


* In case the monitored Project(s) rely on different regions, prepare different
  files /etc/caso/caso-<REGION>.conf

.. code-block:: bash

  [DEFAULT]
  region_name = <REGION>


* List the Project(s) in the /etc/caso/voms.json as from the documentation

.. code-block:: JSON

  {
    "Project1": {
      "projects": ["Project1"]
    },
    "Project2": {
      "projects": ["Project2"]
    }
  }

* Execute caso-extract for each Project (and related REGION) to be monitored (Project1-REGION1, Project2-REGION2)

.. code-block:: bash

    /usr/bin/caso-extract --projects "Project1" --config-file /etc/caso/caso-<REGION1>.conf
    /usr/bin/caso-extract --projects "Project2" --config-file /etc/caso/caso-<REGION2>.conf
