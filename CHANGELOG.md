# CHANGELOG:

## Unreleased
### Added
* `anaconda upload` learned to include whether `info/has_prefix` exists in a conda package as metadata (as true/false).

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
