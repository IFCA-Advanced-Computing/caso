Name:        caso
Release:     1%{?dist}
Summary:     cASO is an OpenStack Accounting extractor

License:     ASL 2.0
URL:         https://github.com/IFCA/caso

BuildArch: noarch
BuildRequires: python3-devel
BuildRequires: python3-setuptools
BuildRequires: python3-pbr
BuildRequires: python3-rpm-macros
BuildRequires: pyproject-rpm-macros
Requires: python3
Requires: python3-oslo-config
Requires: python3-oslo-concurrency
Requires: python3-oslo-log
Requires: python3-oslo-utils
Requires: python3-six
Requires: python3-glanceclient
Requires: python3-keystoneauth1
Requires: python3-keystoneclient
Requires: python3-novaclient
Requires: python3-neutronclient
Requires: python3-dateutil
Requires: python3-stevedore
Requires: python3-dirq

%?python_enable_dependency_generator

%generate_buildrequires
%pyproject_buildrequires

%description 

cASO is an OpenStack Accounting extractor to be used in the EGI.eu
Federated Cloud Infrastructure.


%prep
%autosetup -n caso-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
mv %{buildroot}/usr/etc/ %{buildroot}/etc

%check
# No tests available on py3.6, so lets use only the others. The GH action
# build also builds on Ubuntu, that tests the other versions.

%files 
%{_bindir}/caso-extract
%{_bindir}/caso-mapping-migrate
%{_bindir}/caso-projects
%{python3_sitelib}/caso/
%{python3_sitelib}/caso-%{version}*
%config /etc/caso/caso.conf.sample
%config /etc/caso/voms.json.sample
%exclude /etc/caso/caso-config-generator.conf

%changelog
* Wed Jun 06 2023 Alvaro Lopez Garcia <aloga@ifca.unican.es> 4.2.0
- fix: use POSIX timestamps for SSM cloud records
- Render JSON dates as timestamp integers
- Do not render records using .dict() but usin JSON
- Include type annotations on fixtures
- Records must implement an SSM rendering by themselves
* Mon Apr 10 2023 Alvaro Lopez Garcia <aloga@ifca.unican.es> 4.1.0
- Remove duplicated option
- Let operators mark projects directly on keystone
- Use Keystone properties to load VO mapping.
- Move VM status method to Nova extractor
- nova: move accelerator and benchmark options to correct place
- extractors: move projects options to correct place
- Load VO mapping in correct place
- Move all clients to the base class
- Remove old last run file management
- Add migrate command to ease migration
- Set UUID also for IP records
- Provide better error message when pushing records
- Fix noop messenger
- Include project names in project listing
- Update documentation
- Include caso-projects in usage commands
- Remove deprecated option
- Update configuration file
- Default to all OpenStack extractors
* Thu Mar 20 2023 Alvaro Lopez Garcia <aloga@ifca.unican.es> 4.0.0
- Remove deprecated extractor base class
- Allow to configure more than one extractor
- Adapt neutron extractor code to new format
- Transform records into pydantic models, and start using typing hints
- Include type checking with mypy
- Add Cinder storage extractor
- Fix pydantic model errors
- Typing on SSM
- Ensure that properties are also rendered as JSON
- Make code black
- Remove unused exceptions
- Encode VM names in ASCII
- Image ID can be missing if removed from Glance
- Rename abbreviated variables and methods in SSM messenger
- Catch exception when creating directories
- keystone_client: user project_id None when using name
- Fix error when image id is not a uuid
- Update sample configuration file
- Add an storage record class and publish through SSM
- get lastRun back working
- Fix issues with times and dates in extractors and records
- Uniform formatting of strings
- Avoid calling get_keystone_user if already failed
- Adapt types
- Fix GPU record generation
* Wed Mar 16 2022 Alvaro Lopez Garcia <aloga@ifca.unican.es> 3.0.0
- Support only for Python 3
- Code improvements and bugfixes
* Thu Feb 04 2021 Alvaro Lopez Garcia <aloga@ifca.unican.es> 2.1.1
- d1bd16b Do not rely on f-strings
* Tue Feb 02 2021 Alvaro Lopez Garica <aloga@ifca.unican.es> 2.1.0
- 80870b6 Remove ceilometer code
- 2495353 extractor: new per-project base extractor
- 57c00f5 nova extractor: refactor code to make it simpler
- de4de15 Fix record format, and use correct message format for publication
* Wed Jan 20 2021 Alvaro Lopez Garcia <aloga@ifca.unican.es> 2.0.0
- a25b676 Remove documentation warnings
- 9ee7e17 Fix requirements with proper versions
- 56ebfc7 Include Read the Docs configuration file
- 968462a Support for multi-region + documentation
- 9ea7179 Switch to Travis-CI.com
- baf3ed4 Update Travis configuration
- d7444ff Update cASO requirements
- 36a47c7 Update pbr required version
- bd90f8b Fix tox configuration
- 32426dc Improve package metadata
- 203aeaf Drop Python 2 support
- d5b28da Update CONTRIBUTING guidelines
- 53a3da3 Manage release notes through documentation
- 9b2d644 Remove inline conditional
- d2ebbec Improve code indentation
- 64914aa Format IP record following JSON schema
- 9279e3e IP Accounting: Fixes and some comments
- 5cb2ba3 Add Ip Accounting
- 592bde5 ssm: add entrypoints for V2 and V4 messengers
- 1576b04 Update LOG message with link to documentation
- f4b594a Generate a warning if a VO mapping is not found
- e858386 Change error to warning when a VM cannot be loaded
- ee3035d Allow projects to be specified as IDs
* Tue Mar 24 2020 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.4.3
- 34a7fc6 Fix bug that made cASO report only last project configured
- c8325f5 Ensure that we return integers for wall/cpu duration
* Tue Mar 03 2020 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.4.2
- 3b88759 Servers deleted with end_time=None must have an end time
* Tue Dec 10 2019 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.4.0
- 8a6870 Update sample cfg file
- 38013fd Add "max-size" to limit output records sent to the messenger
* Tue Oct 15 2019 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.3.3
- 3503e5c Do not fail if querying for a server throws an error in the API
- 796c50e Fix wrong record generation
* Tue Oct 01 2019 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.3.1
- 723d8fd Use correct version string
- 4b73f19 setup: set proper content type for description
- a6cd2d9 Use the public keystone interface
- 540b4e7 Document keystone policy configuration
- bd228ae tox: remove py34
- 0e8cadb Improve and fix duration calculation and server status
- 6df46e9 record: use properties for {start,end}_time
- 181aa81 Use correct server's start time
- 6f68e12 Fix lock path management
- 4f475f3 Avoid iteritems
- a77e54e Add locking so that cASO does not run in parallel
- a9d2e7a Update configuration files
* Fri Jun 01 2018 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.2.0
- 2161a33 Fix record extraction and do not request only deleted records
- ae6eb97 Do not lazy-load the extra specs for each flavor
- 08e1471 github: add pull request and issue template
- c703585 Add python 3.6 as supported version
- a86c638 Add and change some meta files to the repository
- 34cc6dc Remove old references to "tenant(s)" in the docs and examples
* Thu Aug 03 2017 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.1.1
- 11520c0 Do not create records for instances outside the reporting period
* Wed May 24 2017 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.1.0
- 345da26 Deprecate underscored options
- d35fefc Report correct durations using periods
- c873858 Take pagination into account
- 6b99fdb fix test failure due to oslo.cfg update
- 6c4c7e5 remove old helper script
* Mon Feb 27 2017 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.0.1
- bb3605b Include "OpenStack" string in the user agent
- 50e1dee Use scope in flavor properties
* Fri Feb 24 2017 Alvaro Lopez Garcia <aloga@ifca.unican.es> 1.0.0
- 822d5bf update sample configuration file
- 786d5c3 Fix missing flavor name in logging
- 178ee50 Fix failure when server does not have image_id
- 586484d extract benchmark information
- d551b86 doc: Update user creation section in configuration
- 66ae4f4 log additional message before extracting records
- cb625c8 do not use tenant_id but project_id
- ad79a63 do not use nova.images but glance client
- debee59 do not use absolute path for cfg files
- 87e55e2 add bandit security linter
- a8b2b5e Add shields.io badges
- b049137 update python3 version
- 9ab70fb Fix typo in log message
- 4d8511f Improve documentation
- d013ec2 Use keystoneauth1 and sessions for authentication
- fd08e4f remove redundant help message
- 3a720f6 Do not put extractors options under CONF.extractor
- 1ad5142 Add service name to the nova extractor
- f4093be Implement version 0.4 of the SSM messenger
- cbd80f2 Implement v0.4 of the CloudRecord
- 3fff9e6 Add initial version to CloudRecord
- ef7199f Implement a base SSM messenger
- ceb2049 Deprecate old ssm messager
- 4faac7c Move "messenger" option to caso manager
- ee96428 Merge pull request #36 from alvarolopez/master
- f082711 Merge pull request #30 from Pigueiras/patch
- a4995fb Fix pep8 and flake8
- 328516e Adapt extractors to use the new extract_to parameter
- 6b35f60 Add option --extract-to to the parameters

* Thu Jan 26 2017 Alvaro Lopez Garcia <aloga@ifca.unican.es> 0.3.3
- Initial RPM version
