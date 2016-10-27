from __future__ import unicode_literals

from os.path import join, exists
import os
import unittest
import shutil
import tempfile
import subprocess
import sys

from binstar_client.scripts import cli
from binstar_client.tests.fixture import CLITestCase


class Test(CLITestCase):

    def test_write_env(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)

        env = dict(os.environ)
        env[str('BINSTAR_CONFIG_DIR')] = str(tmpdir)

        def main(*args):
            return subprocess.check_output((sys.executable, cli.__file__) + args, env=env)

        main('config', '--set', 'url', 'http://localhost:5000')

        self.assertTrue(exists(join(tmpdir, 'data')))
        self.assertTrue(exists(join(tmpdir, 'data', 'config.yaml')))
        self.assertEqual(open(join(tmpdir, 'data', 'config.yaml')).read(), '''\
url: http://localhost:5000
''')

        output = main('config', '--show-sources')

        self.assertEqual(output.replace(b'\r', b''), u'''\
==> {config} <==
url: http://localhost:5000

'''.format(config=join(tmpdir, 'data', 'config.yaml')).encode('utf-8'))


if __name__ == '__main__':
    unittest.main()
