# Changelog

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
