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


============
Installation
============


Pre-requisites
--------------

If you are planning to use ``cASO`` for generating accounting records for EGI,
you will need a valid APEL/SSM configuration. Follow the documentation
available at the `EGI.eu Federated Cloud documentation
<https://egi-federated-cloud.readthedocs.io/en/latest/federation.html#apel-and-accounting-portal>`_
in order to set it up.

Installation
------------

The best way to install cASO and have the most up to date version is using the
repositories and packages provided in the EGI AppDB:

    https://appdb.egi.eu/store/software/caso

Manual installation
*******************

Even the reccomended method is to use a package from the EGI AppDB, it is
possible to install it from the `Python Pacakge Index
<https://pypi.org/project/caso/>`_ as follows::

    $ pip install caso

Or you can install it on a virtualenv::

    $ virtualenv --python python3 caso
    $ source caso/bin/activate
    (caso) $ pip install caso
