from __future__ import print_function, unicode_literals, absolute_import
from subprocess import check_output
import os


def main():
    output = check_output(['git', 'describe', '--always', '--long']).strip()
    output = output.decode().split('-')
    if len(output) == 3:
        version, build, commit = output
    else:
        raise Exception("Could not git describe, (got %s)" % output)

    print("Version: %s" % version)
    print("Build: %s" % build)
    print("Commit: %s" % commit)
    print()
    print("Writing binstar_client/_version.py")
    with open('binstar_client/_version.py', 'w') as fd:
        if build == '0':
            fd.write('__version__ = "%s"\n' % (version))
        else:
            fd.write('__version__ = "%s.post%s"\n' % (version, build))
        fd.write('__commit__ = "%s"\n' % (commit))
    SRC_DIR = os.environ.get('SRC_DIR', '.')

    conda_version_path = os.path.join(SRC_DIR, '__conda_version__.txt')
    print("Writing %s" % conda_version_path)
    with open(conda_version_path, 'w') as conda_version:
        conda_version.write(version)

    conda_buildnum_path = os.path.join(SRC_DIR, '__conda_buildnum__.txt')
    print("Writing %s" % conda_buildnum_path)

    with open(conda_buildnum_path, 'w') as conda_buildnum:
        conda_buildnum.write(build)


if __name__ == '__main__':
    main()
