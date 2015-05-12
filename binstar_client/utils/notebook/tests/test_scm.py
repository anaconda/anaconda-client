import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from binstar_client.utils.notebook import SCMCollection, SCMFile, SCM


packages = [
    {
        u'basename': u'538-sandler.ipynb',
        u'md5': u'a05b1e807998cb85ea49a52f4318bb19',
        u'version': u'1431445024'
    }, {
        u'basename': u'declared_dangerous_dogs.csv',
        u'md5': u'9dfac6839a6691a99566fe8730fafc1b',
        u'version': u'1431445024'
    }, {
        u'basename': u'538-sandler.ipynb',
        u'md5': u'a05b1e807998cb85ea49a52f4318bb19',
        u'version': u'1431458412'
    }
]


class SCMFileTestCase(unittest.TestCase):
    def test_equal(self):
        file1 = SCMFile('same.txt', version='1')
        file2 = SCMFile('same.txt', version='2')

        self.assertEqual(file1, file2)
        self.assertTrue(file2 > file1)


class SCMCollectionTestCase(unittest.TestCase):
    def test_detect(self):
        file1 = SCMFile('same.txt', version='1')
        file2 = SCMFile('same.txt', version='2')
        file3 = SCMFile('other.txt', version='2')
        file4 = SCMFile('other2.txt', version='2')

        col = SCMCollection()
        col._elements = [file1, file3]
        self.assertEqual(col.detect(file4), None)
        self.assertEqual(col.detect(file2), file1)

    def test_choose(self):
        file1 = SCMFile('same.txt', version='1')
        file2 = SCMFile('same.txt', version='2')
        col = SCMCollection()

        self.assertEqual(col.choose(file1, file2), file2)

    def test_append(self):
        file1 = SCMFile('same.txt', version='1')
        file2 = SCMFile('same.txt', version='2')
        file3 = SCMFile('other.txt', version='2')
        file4 = SCMFile('other2.txt', version='2')

        col = SCMCollection()
        col.append(file1)
        col.append(file2)
        col.append(file3)
        col.append(file4)

        self.assertEqual(col._elements, [file2, file3, file4])

    def test_substract_equal_zero(self):
        file1 = SCMFile('same.txt', version='1')
        file2 = SCMFile('same.txt', version='1')
        col1 = SCMCollection([file1])
        col2 = SCMCollection([file2])
        self.assertEqual(len(col1 - col2), 0)

    def test_substract_vs_empty(self):
        file1 = SCMFile('same.txt', version='1')
        col3 = SCMCollection([file1])
        col4 = SCMCollection([])
        self.assertEqual(len(col3 - col4), 1)


class SCMTestCase(unittest.TestCase):
    def test_pull(self):
        binstar = mock.Mock()
        binstar.package.return_value = packages
        scm = SCM(binstar, 'username', 'project')
        print scm._uploaded
        scm.pull()

        self.assertEqual(len(scm._uploaded), 2)

    def test_local(self):
        binstar = mock.Mock()
        scm = SCM(binstar, 'username', 'project')

        scm.local(packages)
        self.assertEqual(len(scm._local), 2)

    def test_diff(self):
        uploaded = [
            {
                'basename': 'file1',
                'md5': '1',
                'version': '1'
            }, {
                'basename': 'file2',
                'md5': '1',
                'version': '1'
            }
        ]

        local = [
            {
                'basename': 'file1',
                'md5': '2',
                'version': '2'
            }, {
                'basename': 'file2',
                'md5': '1',
                'version': '2'
            }, {
                'basename': 'file3',
                'md5': '1',
                'version': '2'
            }
        ]

        binstar = mock.Mock()
        binstar.package.return_value = uploaded
        scm = SCM(binstar, 'username', 'project')
        scm.pull()
        scm.local(local)

        diff = scm.diff()
        self.assertEqual(len(diff), 2)


if __name__ == '__main__':
    unittest.main()
