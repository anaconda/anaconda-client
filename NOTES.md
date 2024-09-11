# Notes about anaconda-client

* PIL is an optional dependency. It is used to load an icon, after introspecting a conda package. It appears it becomes a part of a `release_data` dictionary under the key `icon`. This is done in the function `binstar_client.inspect_package.conda.inspect_conda_info_dir`.
    * Need to investigate where/how that is used, and then make sure that the backend is actually using it.
    * It also is used by notebook upload functions, but those will be deprecated
