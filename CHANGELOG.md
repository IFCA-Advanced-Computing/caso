# Changelog

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
