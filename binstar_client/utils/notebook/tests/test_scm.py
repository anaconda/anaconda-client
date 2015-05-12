import unittest
from binstar_client.utils.notebook import SCMCollection, SCMFile


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


if __name__ == '__main__':
    unittest.main()
