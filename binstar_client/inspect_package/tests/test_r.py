from __future__ import print_function, unicode_literals

import unittest

from binstar_client.inspect_package import r
from binstar_client.utils.test.utils import data_dir


expected_package_data = {
    'license': 'GPL-2 | GPL-3',
    'name': 'rfordummies',
    'summary': 'Code Examples to Accompany the Book "R for Dummies"'
}


expected_version_data = {
    'description': 'Contains all the code examples in the book "R for Dummies" (1st\n    edition). '
                   'You can view the table of contents as well as the sample code for each\n    chapter.',
    'version': '0.1.2',
}

expected_file_data = {
    'attrs': {
        'NeedsCompilation': 'no',
        'suggests': [
            'fortunes',
            'stringr',
            'sos',
            'XLConnect',
            'reshape2',
            'ggplot2',
            'foreign',
            'lattice',
        ],
        'depends': [],
        'type': 'source',
    },
    'basename': 'rfordummies_0.1.2.tar.gz',
}


class Test(unittest.TestCase):
    maxDiff = None
    def test_r(self):
        filename = data_dir('rfordummies_0.1.2.tar.gz')
        with open(filename, 'rb') as fd:
            package_data, version_data, file_data = r.inspect_r_package(filename, fd)

        self.assertEqual(expected_package_data, package_data)
        self.assertEqual(expected_version_data, version_data)
        self.assertEqual(expected_file_data, file_data)


if __name__ == "__main__":
    unittest.main()
