import unittest
from binstar_client.utils.test.utils import example_path
from ..models import CondaProject, PFile


class CondaProjectTestCase(unittest.TestCase):
    def test_initialize(self):
        cp = CondaProject(example_path('bokeh-apps/weather'))
        self.assertEqual(cp.metadata, {})

        cp = CondaProject(example_path('bokeh-apps/weather'), summary="weather")
        self.assertEqual(cp.metadata, {'summary': 'weather'})

        cp = CondaProject(example_path('bokeh-apps/weather'), description="aa")
        self.assertEqual(cp.metadata, {'description': 'aa'})

    def test_to_stage(self):
        cp = CondaProject(example_path('bokeh-apps/weather'))
        cp.tar_it()
        self.assertEqual(
            cp.to_stage(),
            {'basename': 'weather.tar', 'configuration': {
                'num_of_files': 0, 'size': 10240
            }, 'size': 10240})

    def test_get_project_name_from_file(self):
        prj = CondaProject(example_path('bokeh-apps/timeout.py'))
        self.assertEqual(prj.name, 'timeout')

    def test_get_project_name_from_dir(self):
        prj = CondaProject(example_path('bokeh-apps/weather'))
        self.assertEqual(prj.name, 'weather')

    def test_get_project_name_from_current_dir(self):
        prj = CondaProject('.')
        self.assertEqual(prj.name, 'anaconda-client')


    def test_ignore_empty_options(self):
        prj = CondaProject(example_path('bokeh-apps/weather'), version='1')
        self.assertEqual(prj.metadata['version'], '1')
        self.assertNotIn('summary', prj.metadata)
        self.assertNotIn('description', prj.metadata)


class PFileTestCase(unittest.TestCase):
    def test_size(self):
        pfile = PFile(fullpath=example_path('bokeh-apps/timeout.py'))
        self.assertEqual(pfile.size, 1523)

    def test_basename(self):
        pfile = PFile(fullpath=example_path('bokeh-apps/timeout.py'))
        self.assertEqual(pfile.basename, 'timeout.py')

    def test_str(self):
        pfile = PFile(fullpath=example_path('bokeh-apps/timeout.py'),
                      relativepath='bokeh-apps/timeout.py')
        self.assertEqual(str(pfile), "[1523] bokeh-apps/timeout.py")

    def test_validate_with_function(self):
        def function(**kwargs):
            return kwargs['basename'].endswith('.py')

        pfile = PFile(fullpath=example_path('bokeh-apps/timeout.py'))
        assert pfile.validate(function)

    def test_validate_with_class(self):
        class Validate(object):
            def __init__(self, pfile):
                pass

            def __call__(self):
                return True

        pfile = PFile(fullpath=example_path('bokeh-apps/timeout.py'))
        assert pfile.validate(Validate)


if __name__ == '__main__':
    unittest.main()
