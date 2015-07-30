# CHANGELOG:

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
