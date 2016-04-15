import os


def example_path(example):
    return os.path.join(os.path.dirname(__file__),
                        '../../../example-packages',
                        example)
