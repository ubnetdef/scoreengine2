import importlib
from typing import Union

from . import celery_app


@celery_app.task(soft_time_limit=30)
def check_task(data):
    try:
        check_function = _get_check_function(**data['check'])
    except (AttributeError, ImportError):
        # TODO: log this? ignore this?
        print('There was en error getting the check function')
        raise

    check_function(CheckData(data))
    return data


def _get_check_function(file_name, function_name):
    check_module_name = 'scoreengine.checks.{}'.format(file_name)
    check_module = importlib.import_module(check_module_name)
    check_function = getattr(check_module, function_name)
    return check_function


class CheckData:
    def __init__(self, data):
        self._data = data

    @property
    def config(self):
        return self._data['config']

    @property
    def service_name(self):
        return self._data['service_name']

    @property
    def passed(self):
        return self._data['passed']

    @passed.setter
    def passed(self, value: bool):
        self._data['passed'] = value

    def add_output(self, message: Union[bytes, str], *args, **kwargs):
        if not isinstance(message, str):
            message = message.decode()
        self._data['output'].append(message.format(*args, **kwargs))

    def export(self):
        return self._data
