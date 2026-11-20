# Changelog

## [5.2.3](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.2.2...v5.2.3) (2026-11-20)


### Bug Fixes

* avoid Bandit false positive in Nova status map ([ec08cab](https://github.com/IFCA-Advanced-Computing/caso/commit/ec08cabd163e0677802fe2d524f3c2cdf483f592))
* **cinder:** report all attachments and skip volumes created after period ([7174079](https://github.com/IFCA-Advanced-Computing/caso/commit/71740795b9f8021602fe7585338ee5c2e068a193))
* **extract:** do not map a None project when reading the VO mapping file ([aefab8f](https://github.com/IFCA-Advanced-Computing/caso/commit/aefab8ff67b708976217c7105946f6ce66bbdd40))
* **logstash:** make the messenger work with the current record objects ([a8af774](https://github.com/IFCA-Advanced-Computing/caso/commit/a8af774f9ec115fb41c99a46b46e14af696027b3))
* **messenger:** keep pushing to other messengers when one of them fails ([76858b4](https://github.com/IFCA-Advanced-Computing/caso/commit/76858b4566aef048455d469467b9e8ef3adf0fa1))
* **neutron:** filter floating IPs by project and keep IPv4/IPv6 records ([61b907e](https://github.com/IFCA-Advanced-Computing/caso/commit/61b907e83aa882efc4a601bb5ce94cc4a79f0276))
* **nova:** do not use an undefined wall time for servers ended in period ([052a67c](https://github.com/IFCA-Advanced-Computing/caso/commit/052a67c02c287fb49de4a0f2a8a84efd07daeef8))
* **prometheus:** account deleted VMs and query only their running period ([51e2d36](https://github.com/IFCA-Advanced-Computing/caso/commit/51e2d367cae1a6956bd8e0541bce1afc6b028875))
* **prometheus:** interpolate VM name and UUID in debug message ([378d8d6](https://github.com/IFCA-Advanced-Computing/caso/commit/378d8d638cd4d83c558e2e616e8b617ec2cf75cf))
* **record:** treat naive datetimes as UTC regardless of the host time zone ([a94340e](https://github.com/IFCA-Advanced-Computing/caso/commit/a94340ea318cbd7a05c807c49b08bb14d2677f3d))


### Performance Improvements

* **extract:** import the extractors lazily from the extract packages ([6252cdc](https://github.com/IFCA-Advanced-Computing/caso/commit/6252cdc914a9a61bf95ee2c659eb708e9018a593))
* **loading:** get plugin names without importing all the plugins ([a24c867](https://github.com/IFCA-Advanced-Computing/caso/commit/a24c867fa148b67c60f70e1495abaf844596a052))


### Documentation

* point project URLs to the IFCA-Advanced-Computing organization ([40f487b](https://github.com/IFCA-Advanced-Computing/caso/commit/40f487bc555ce4b3875b19335d80a3c01af316b2))
* **readme:** load the EU logo from master and fix acknowledgement typo ([a9b3846](https://github.com/IFCA-Advanced-Computing/caso/commit/a9b38465a6a3d2fb6735e15ea87069e1ac568777))
* **releasenotes:** add notes for the record, extractor and messenger fixes ([319eadc](https://github.com/IFCA-Advanced-Computing/caso/commit/319eadcf3b711d6fb0b9dfdf27491fb75d019da1))

## [5.2.2](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.2.1...v5.2.2) (2026-07-15)


### Bug Fixes

* refactor write_lastrun method to accept extract_to parameter ([d3c952e](https://github.com/IFCA-Advanced-Computing/caso/commit/d3c952ec4efa445953136574efe3dafdebad627b))
* update write_lastrun assertion to include extract_to parameter ([3311bec](https://github.com/IFCA-Advanced-Computing/caso/commit/3311becf4cbea15bd50111cfb60b680f8c1d8d60))


### Documentation

* Update badge for Python Testing in README ([b0bb171](https://github.com/IFCA-Advanced-Computing/caso/commit/b0bb1715a92bcbf21d36c042c96f216bad864a9c))

## [5.2.1](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.2.0...v5.2.1) (2026-02-12)


### Features

* add mapping configuration between record types and messengers ([0041867](https://github.com/IFCA-Advanced-Computing/caso/commit/004186796406af7daa9da2b49a4e8d2559b66f22))
* Add Prometheus extractor and EnergyRecord for energy consumption metrics ([6938099](https://github.com/IFCA-Advanced-Computing/caso/commit/6938099d53d40d506b1e7e8d706f381f7da85cfb))
* ensure CPU and Wall time is not zero ([741c448](https://github.com/IFCA-Advanced-Computing/caso/commit/741c448485e6bd79d824a33be9cafe20146d00e7))
* Implement energy record publication to CIM ([#170](https://github.com/IFCA-Advanced-Computing/caso/issues/170)) ([#171](https://github.com/IFCA-Advanced-Computing/caso/issues/171)) ([69881f7](https://github.com/IFCA-Advanced-Computing/caso/commit/69881f7bf5cb15131fca58317cacbc08a6b0ca6a))


### Bug Fixes

* correct energy record calculations and add CPU normalization factor ([53e6d38](https://github.com/IFCA-Advanced-Computing/caso/commit/53e6d38a54431895db09841c0229cfed4a61a63f))
* do not request all tenants when listing servers ([2540db3](https://github.com/IFCA-Advanced-Computing/caso/commit/2540db3516bc5548fea82f581548dfe728b4e7df))
* Do not use a scoped client when getting user information ([3eed5b0](https://github.com/IFCA-Advanced-Computing/caso/commit/3eed5b075f2fa8a11bae81cf42b27e4535c446ec)), closes [#173](https://github.com/IFCA-Advanced-Computing/caso/issues/173)
* include entrypoint for greendigit_cim ([b187d51](https://github.com/IFCA-Advanced-Computing/caso/commit/b187d513310f0ed4bb07012724b187109b8d3406))
* Integrate energy_consumed_wh function using prometheus-api-client ([390db52](https://github.com/IFCA-Advanced-Computing/caso/commit/390db52080a877ed727102eeb985a3059e44d40f))
* remove deprecated prometheus_query_range configuration and update related documentation ([59fc0ca](https://github.com/IFCA-Advanced-Computing/caso/commit/59fc0ca6c2c2e595369139f60a5356c40e946d7b))
* remove unnecessary blank lines in base.py and logstash.py ([d73a579](https://github.com/IFCA-Advanced-Computing/caso/commit/d73a5798cf4f312434701fc107278ff1cf6ddc63))
* Rename to EnergyConsumptionExtractor and update EnergyRecord format ([ac35ab1](https://github.com/IFCA-Advanced-Computing/caso/commit/ac35ab12ccc35cba0c85dd43822fa76db3b583d8))
* update documentation for Prometheus extractor and GreenDIGIT CIM messenger configuration ([e0884d9](https://github.com/IFCA-Advanced-Computing/caso/commit/e0884d9368d861b3b9923b555bdd3a59664da279))
* Update Prometheus extractor to scan VMs and support query templating ([a1c6b8c](https://github.com/IFCA-Advanced-Computing/caso/commit/a1c6b8c44b24e5b80e89d631a13f1ed254e12838))


### Documentation

* add documentation for messenger record type filtering ([b6959a2](https://github.com/IFCA-Advanced-Computing/caso/commit/b6959a2a510f58b76510b01d34fb8f600b25d527))
* add release notes for messenger record type filtering ([7be9c3c](https://github.com/IFCA-Advanced-Computing/caso/commit/7be9c3c8aa5d180c4e12a7ddfe1e8234827e4cec))


### Miscellaneous Chores

* release 5.2.1 ([a035867](https://github.com/IFCA-Advanced-Computing/caso/commit/a035867b5e75787db17a2a30d7b64f1ebee17632))

## [5.2.0](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.1.0...v5.2.0) (2025-10-08)


### Features

* do not fail if lastrun is invalid ([74eb6bd](https://github.com/IFCA-Advanced-Computing/caso/commit/74eb6bd6df41bfc0d57683524caa2e8ca80ba021)), closes [#146](https://github.com/IFCA-Advanced-Computing/caso/issues/146)


### Bug Fixes

* Move system_scope check to the keystone_client ([75031e7](https://github.com/IFCA-Advanced-Computing/caso/commit/75031e77ab3f727388351eb60fd4d07c85c3c58c))

## [5.1.0](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.0.1...v5.1.0) (2024-12-03)


### Features

* VolumeCreationTime variable added ([9f9745e](https://github.com/IFCA-Advanced-Computing/caso/commit/9f9745ee58b046ce20688c27c0430fdad96ecec5))


### Bug Fixes

* do not assume admin privileges on keystone ([6daa0de](https://github.com/IFCA-Advanced-Computing/caso/commit/6daa0de5efc94064724a3e54019dd6f50d669dac)), closes [#124](https://github.com/IFCA-Advanced-Computing/caso/issues/124)
* remove duplicated key in dict ([949f6bf](https://github.com/IFCA-Advanced-Computing/caso/commit/949f6bf40c9e670b79ccfd6f6294050fbafff739))

## [5.0.1](https://github.com/IFCA-Advanced-Computing/caso/compare/v5.0.0...v5.0.1) (2024-09-27)


### Miscellaneous Chores

* release 5.0.1 ([3cee70d](https://github.com/IFCA-Advanced-Computing/caso/commit/3cee70d1c1f7e5f4dd38f57eed8e18521bf0285a))

## [5.0.0](https://github.com/IFCA-Advanced-Computing/caso/compare/4.1.1...v5.0.0) (2024-09-27)


### ⚠ BREAKING CHANGES

* use Pydantic 2 and move records to use computed_fields

### Features

* include release please ([248ffcd](https://github.com/IFCA-Advanced-Computing/caso/commit/248ffcd33dee010164e57ce1e209371fd1f0b9e1))
* use Pydantic 2 and move records to use computed_fields ([2181e9c](https://github.com/IFCA-Advanced-Computing/caso/commit/2181e9cbd2fc853bde7efd2191499ceaa5dcab49))


### Bug Fixes

* fix some validation errors to be aligned to latest pydantic v2 ([115ffa6](https://github.com/IFCA-Advanced-Computing/caso/commit/115ffa62c5ac62c8fc7932d984a29ab8048dd29c))
* set explicit stacklevel on warnings ([e034663](https://github.com/IFCA-Advanced-Computing/caso/commit/e034663510b5c6b4edf34ed36ad3e9fc51a362f9))
* solve mypy errors ([4ed35c4](https://github.com/IFCA-Advanced-Computing/caso/commit/4ed35c41da1e7b8c585dcb0477473fefef03a87b))
* use POSIX timestamps for SSM cloud records ([c1df014](https://github.com/IFCA-Advanced-Computing/caso/commit/c1df014973442dfd7537fbeb179c51bf582b8a13)), closes [#113](https://github.com/IFCA-Advanced-Computing/caso/issues/113)
