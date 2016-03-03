import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client.utils.test.utils import example_path
from binstar_client.utils.projects.filters import (VCSFilter,
                                                   LargeFilesFilter,
                                                   ProjectIgnoreFilter,
                                                   FilesFilter,
                                                   ignore_patterns,
                                                   remove_comments)


class IgnorePatternsTestCase(unittest.TestCase):
    def test_ignore_patterns(self):
        patterns = ignore_patterns(example_path('bokeh-apps/weather'))
        self.assertListEqual(patterns, ['*.rb', '*.pyc', '__pycache__'])


class RemoveCommentsTestCase(unittest.TestCase):
    def test_commented_lines(self):
        c1 = "# Ingored line"
        c2 = "*.pyc # python files"
        c3 = "__pycache__"
        c4 = ""

        self.assertEqual(
            remove_comments(c1),
            ""
        )
        self.assertEqual(
            remove_comments(c2),
            "*.pyc"
        )
        self.assertEqual(
            remove_comments(c3),
            "__pycache__"
        )
        self.assertEqual(
            remove_comments(c4),
            ""
        )


class LargeFilesFilterTestCase(unittest.TestCase):
    def test_valid_file(self):
        pfile = mock.MagicMock(size=100)
        self.assertTrue(LargeFilesFilter([]).run(pfile))

    def test_invalid_file(self):
        pfile = mock.MagicMock(size=3097152)
        self.assertFalse(LargeFilesFilter([]).run(pfile))


class FilesFilterTestCase(unittest.TestCase):
    def test_valid_file(self):
        pfile = mock.MagicMock(relativepath='other-file')
        self.assertTrue(FilesFilter([]).run(pfile))

    def test_invalid_file(self):
        pfile = mock.MagicMock(relativepath='.anaconda/project-local.yml')
        self.assertFalse(FilesFilter([]).run(pfile))


class VCSFilterTestCase(unittest.TestCase):
    def test_can_test(self):
        assert VCSFilter([]).can_filter()

    def test_git_files(self):
        pfile = mock.MagicMock(relativepath=".git/hooks/pre-applypatch", fullpath="")
        self.assertFalse(VCSFilter([]).run(pfile))

    def test_svn_files(self):
        pfile = mock.MagicMock(relativepath=".svn/hooks/pre-applypatch", fullpath="")
        self.assertFalse(VCSFilter([]).run(pfile))

    def test_valid_files(self):
        pfile = mock.MagicMock(relativepath="folder/hooks/applypatch", fullpath="")
        self.assertTrue(VCSFilter([]).run(pfile))


class ProjectIgnoreFilterTestCase(unittest.TestCase):
    def test_can_filter(self):
        example_path('bokeh-apps/weather')
        self.assertTrue(
            ProjectIgnoreFilter([], basepath=example_path('bokeh-apps/weather'))
        )

    def test_cant_filter(self):
        example_path('bokeh-apps/timeout.py')
        self.assertTrue(
            ProjectIgnoreFilter([], basepath=example_path('bokeh-apps/weather'))
        )

    def test_run(self):
        pfile1 = mock.MagicMock(relativepath="dir/file.rb")
        pfile2 = mock.MagicMock(relativepath="dir/file.py")

        f = ProjectIgnoreFilter([], basepath=example_path('bokeh-apps/weather'))

        self.assertFalse(f.run(pfile1))
        self.assertTrue(f.run(pfile2))


if __name__ == '__main__':
    unittest.main()
