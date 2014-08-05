import tarfile
from email.parser import Parser
from os import path

def inspect_r_package(filename, fileobj):

    tf = tarfile.open(filename, fileobj=fileobj)

    pkg_info = next(name for name in tf.getnames() if name.endswith('/DESCRIPTION'))
    fd = tf.extractfile(pkg_info)
    raw_attrs = dict(Parser().parse(fd).items())

    name = raw_attrs.pop('Package')
    version = raw_attrs.pop('Version')
    summary = raw_attrs.pop('Title', None)
    description = raw_attrs.pop('Description', None)
    license = raw_attrs.pop('License', None)

    attrs = {}
    attrs['NeedsCompilation'] = raw_attrs.get('NeedsCompilation', 'no')
    attrs['depends'] = raw_attrs.get('Depends', '').split(',')
    attrs['suggests'] = raw_attrs.get('Suggests', '').split(',')

    built = raw_attrs.get('Built')

    if built:
        r, _, date, platform = built.split(';')
        r_version = r.strip('R ')
        attrs['R'] = r_version
        attrs['os'] = platform.strip()
        attrs['type'] = 'package'
    else:
        attrs['type'] = 'source'

    package_data = {'name': name,
                    'summary': summary,
                    'license': license,
                    }
    release_data = {
                    'version': 'version',
                    'description': description,
                    }
    file_data = {
                 'basename': path.basename(filename),
                 'attrs': attrs,
                 }

    return package_data, release_data, file_data
