import inspect
import os


def data_dir(filename):
    base_path = inspect.stack()[1][1]  # function caller path
    test_data = os.path.join(os.path.dirname(base_path), 'data')
    return os.path.join(test_data, filename)


def example_path(example):
    return os.path.join(os.path.dirname(__file__),
                        '../../../example-packages',
                        example)
