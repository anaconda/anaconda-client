# CHANGELOG:

## Next version

## Version 1.7.2 (2018/08/29)

### Fixed

* Wheels upload doesn't work with wheel==0.31.0
* Add `--skip-existing` flag for uploading large batches of packages

## Version 1.7.1 (2018/08/02)

### Fixed

* Fix files download and add more output information
* Fix typos in the help text

## Version 1.7.0 (2018/07/16) - Not released

### Fixed

* Add move command for label handling
* Add copy subcommand for label handling
* Add option to download specific package type
* Fix text mentions of Anaconda Cloud
* Clear in-line help for "package type" option in "upload" command
* Fixed get_server_api call on get_binstar

## Version 1.6.14 (2018/03/19)

### Fixed

* Fixed get_server_api call on get_binstar

## Version 1.6.13 (2018/03/13)

### Fixed

* Re-added get_binstar function

## Version 1.6.12 (2018/03/12)

### Fixed

* Fixed behavior of the url config setting
* Fixed upload command help
* Upload now reads Jupyter notebooks metadata

## Version 1.6.11 (2018/02/20)

### Fixed

* Fixed loading of tagged config files under Python 3

## Version 1.6.10 (2018/02/19)

### Added

* Added support for setting a default upload user
* Show warnings when lock down and read-only headers are present

## Version 1.6.9 (2018/01/31)

### Fixed

* Fixed upload message when package_types is empty
* Revert to using PyYAML instead of ruamel.yaml

## Version 1.6.8 (2018/01/24)

### Fixed

* Fixed ruamel.yaml dependency.

## Version 1.6.7 (2018/01/18)

### Added

* Refactored logging.
* Replaced PyYAML with ruamel.yaml.

### Fixed

* Fixed logging of error messages.

## Version 1.6.6 (2017/12/04)

### Added

* Deprecated verify_ssl in favor of ssl_verify
* Validation to prevent uploading package with more than one type

### Fixed

* Using seconds on environment version
* Sending package_type field on upload
* Display correct file type when uploading
* Refactor of `data_dir`/`data_path` function
* Fixed token generation when server uses Kerberos authentication
* Using session to upload packages when the storage is in the same server as the API
* Fixed file uploads with special characters
* Fixed problems with pretty printing
* Removed from-channel and to-channel options from copy command
* Raise exception after logging error message when package upload fails
* Fixed installer detection

## Version 1.6.5 (2017/09/08)

### Fixed

* Fixes to allow conda 3 to build
* Removed unused dependency

## Version 1.6.4 (2017/09/08)

### Added

* Add `https://` to domain URL when is missing
* Added `--platform` filter
* Displaying build information on packages table
* Notebook validation on upload
* Warning message when token is about to expire

## Version 1.6.3 (2017/04/24)

### Issues Closed

* [Issue 398](https://github.com/Anaconda-Platform/anaconda-client/issues/398) - Trouble build 1.6.2 on Windows

### Pull Requests Merged

* [PR 390](https://github.com/Anaconda-Platform/anaconda-client/pull/390) - Send more package metadata when uploading a file
* [PR 394](https://github.com/Anaconda-Platform/anaconda-client/pull/394) - Send metadata attributes when uploading a new release
* [PR 395](https://github.com/Anaconda-Platform/anaconda-client/pull/395) - Switch from conda-kapsel to anaconda-project
* [PR 402](https://github.com/Anaconda-Platform/anaconda-client/pull/402) - Allows to upload private packages
* [PR 405](https://github.com/Anaconda-Platform/anaconda-client/pull/405) - Put some JSON in test notebook foo.ipynb
* [PR 407](https://github.com/Anaconda-Platform/anaconda-client/pull/407) - Trying with conda.bat if conda.exe doesn't exists

## Version 1.6.2 (2017/02/15)

### Issues Closed

#### Bugs fixed

* [Issue 336](https://github.com/Anaconda-Platform/anaconda-client/issues/336) - anaconda download generates an error for notebook files
* [Issue 153](https://github.com/Anaconda-Platform/anaconda-client/issues/153) - binstar package --list-collaborators option broken

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 389](https://github.com/Anaconda-Platform/anaconda-client/pull/389) - Better error message for the server not found exception
* [PR 386](https://github.com/Anaconda-Platform/anaconda-client/pull/386) - Fix/download non notebook files

In this release 2 pull requests were closed.

## 1.6.1 (2017-01-31)
* Support reading package information from `about.json` instead of `recipe.json`
(@jjhelmus)

## 1.6.0 (2016-12-08)
* Add trial license generation endpoint for registered users

## 1.5.5 (2016-11-17)
* fix reading of conda root prefix on a detached environment in Python 3

## 1.5.4 (2016-11-09)

### Fixed
* `anaconda config` should expand paths before reading them

## 1.5.3 (2016-10-27)

### Fixed
* `anaconda config --set` should use `BINSTAR_CONFIG_DIR`
* Save `<host>.token` to the old directory, so `conda` can read them

## 1.5.2 (2016-10-20)

### Added

* `anaconda upload` will extract icons from conda packages
* Added explicit license file
* Added some clarity on help file for -u switch (PR#360)

### Fixed
* Removed workaround for old requests versions
* `anaconda upload` would raise an exception if a file was interactively
not overwritten (#364)

### Changed
* `anaconda-client` will load configuration files with the extension `.yaml` from 
  the directories `~/.continuum/anaconda-client`, `/etc/anaconda-client` and `$PREFIX/etc/anaconda-client`.

## 1.5.1 (2016-08-01)

### Added
* `anaconda upload` learned to include whether `info/has_prefix`
  exists in a conda package as metadata (as true/false).
* `anaconda upload` can upload projects with a kapsel.yml (for
  conda kapsel)

### Fixed
* `anaconda groups` subcommand had several bugs, and was difficult to use (#312)
* `anaconda upload` will do the minimal amount of work to parse a conda package (@brentp) (#311)
* `anaconda upload` had Unicode errors when dealing with Jupyter notebooks (#306)

## 1.4.0 (2016-03-24)

  * `BinstarClient.user_packages` learned arguments `platform`, `package_type`,
    `type_`, and `access`

## 1.3.1

  * Fix pip 8.1 issue with py27. #303
  * Fix `anaconda copy` problem with labels. #304

## 1.3.0

  * `notebook` subcommand is going to be deprecated. Showing deprecation warnings for now. #300
  * `anaconda upload` can upload notebooks with thumbnails. #300
  * `anaconda upload` can upload environments. #301
  * Fix/netrc auth. #298
  * Fix OpenSSL issue. #297
  * Improve performance when dealing with tar files. #293 (@brentp)
  * `anaconda login` supports kerberos. #278
  * Typos. #284 (@barentsen) and #276
  * Error when failing to delete data. #273
  * Docs cleanup. #272

## 1.2.2

  * Learned the `anaconda label` command and `--label` arguments to replace the `--channel` options and `anaconda channel` command (#262)
  * `anaconda auth --remove` learned the `--organization` argument to remove a token for an organization (#260)
  * `anaconda upload` can be told not to create packages automatically by setting the new `auto_register` configuration option to `no` (#270)
  * Learned to read an API token from the environment variable `ANACONDA_API_TOKEN` (#269)
  * Additional bug fixes (#204 #268 Anaconda-Server/docs.anaconda.org#63)

## 1.2.1

  * Produce warning about broken version of Requests with PyOpenSSL

## 1.2.0

  * Fix issue with `anaconda download` when server uses file storage

## 1.1.2

  * Fix issue with big packages #126

## 1.1.0

  * `anaconda download` new subcommand
  * `anaconda upload` can upload notebooks
  * notebooks versions compatible with conda
  * Pillow is no longer a hard dependency

## 1.0.2

  * Support Jupyter

## 1.0.0

  * Rename into **anaconda-client** #193
  * Executable renamed into **anaconda** #193
  * Remove duplicated changelog

## 0.14.0

  * full rename into conda-server #187
  * Replace error messages into warnings #188
  * New entry point #186

## 0.12.0

  * conda-server notebook include thumbnail
  * versioneer
  * renamed into conda-server

## 0.11.0

  * binstar notebook upload/download
  * Fix bug in collaborators list
  * Fix unicode issues

## 0.10.4
  * Fix remove token file from Windows environments
  * Replace api.binstar.org for api.anaconda.org

## 0.10.2
  * Added ability to upload ipython notebooks (*.ipynb files)
  * Added ability to upload cas installers (*.sh files)
  * Fixed issue with binstar-build - need to output to stdout at least every minute even with -q/--quiet option
  * Misc fixes: typos, better error messages, etc.
  * Use conda info attribute 'subdir' in preperation for noarch support
