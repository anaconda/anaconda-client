import unittest
try:
    from unittest import mock
except ImportError:
    import mock
from binstar_client.utils.projects.inspectors import (DocumentationInspector,
                                                      ProjectFilesInspector)


class DocumentationInspectorTestCase(unittest.TestCase):
    def test_has_doc(self):
        pfile = mock.MagicMock(basename="README", relativepaht="README")
        assert DocumentationInspector([pfile]).has_doc()


class ProjectFilesInspectorTestCase(unittest.TestCase):
    def test_update(self):
        pfile = mock.MagicMock(basename="README")
        pfile.to_dict.return_value = {"basename": "README"}

        metadata = {}
        ProjectFilesInspector([pfile]).update(metadata)

        self.assertEqual(metadata['files'], [{"basename": "README"}])


if __name__ == '__main__':
    unittest.main()
