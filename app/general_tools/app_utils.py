import inspect
import os


def get_app_root():
    current_dir = os.path.dirname(inspect.stack()[0][1])
    return os.path.dirname(os.path.dirname(current_dir))


def get_resources_dir():
    return os.path.join(get_app_root(), 'resources')


def get_output_dir():
    return os.path.join(get_app_root(), 'output')
