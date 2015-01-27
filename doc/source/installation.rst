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

If you are planning to use caso for generating accounting records for EGI,
you will need a valid APEL/SSM configuration. Follow the documentation
available at the `EGI FedCloud wiki
<https://wiki.egi.eu/wiki/Fedcloud-tf:WorkGroups:Scenario4#Publishing_Records>`_

Installation
------------

At the command line::

    $ pip install caso

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv caso
    $ pip install caso
    
On CentOS 6, you can use Software Collections to install Python 2.7 and then libffi-devel, which is also required::
    
    $ yum -y install centos-release-SCL
    $ yum -y install python27
    $ yum -y install libffi-devel
    
You can then install pip for that version of Python and use that to install caso::

    $ scl enable python27
    $ easy_install-2.7 pip
    $ pip install caso
