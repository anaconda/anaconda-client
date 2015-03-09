import logging
from os import path

import yaml


log = logging.getLogger(__name__)

PACKAGE_TYPE = 'installer'

def is_installer(filename):
    # TODO: allow
    if not filename.endswith('.sh'):
        return False

    with open(filename) as fd:
        fd.readline()
        cio_copyright = fd.readline()
        # Copyright (c) 2012-2014 Continuum Analytics, Inc.
        # TODO: it would be great if the installers had a unique identifier in the header
        if "Copyright" not in cio_copyright:
            return False
        if "Continuum Analytics, Inc." not in cio_copyright:
            return False
        return True

    return False

def inspect_package(filename, fileobj):

    lines = [fileobj.readline().strip(" #\n") for i in range(11)]
    try:
        installer_data = yaml.load("\n".join(lines[4:]))
    finally:
        log.error("Could not load installer info as YAML")


    summary = "Conda installer for platform %s" % installer_data.pop('PLAT')
    name = installer_data.pop('NAME')
    version = installer_data.pop('VER')
    attrs = installer_data

    package_data = {'name': name,
                    'summary': summary,
                    'license': None,

                    }
    release_data = {
                    'version': version,
                    'description': summary,
                    }
    file_data = {
                 'basename': path.basename(filename),
                 'attrs': attrs,
                 'binstar_package_type': 'file',
                 }

    return package_data, release_data, file_data
