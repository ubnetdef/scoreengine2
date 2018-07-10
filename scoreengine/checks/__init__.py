from functools import wraps
from typing import Callable

from scoreengine import config  # as a convenience for checks
from scoreengine.tasks import CheckData


def check_function(expectation: str):
    def decorator(actual_check_function: Callable):
        @wraps(actual_check_function)
        def wrapper(check: CheckData):
            check.add_output('ScoreEngine: {} Check', check.service_name)
            check.add_output('EXPECTED: {}', expectation)
            check.add_output('OUTPUT:')

            # TODO: verify if this is the desired behavior
            try:
                result = actual_check_function(check)
            except Exception as e:
                check.passed = False
                check.add_output("ERROR: {}: {}", type(e).__name__, e)
            else:
                check.passed = bool(result)
            if check.passed:
                check.add_output('Check successful!')
        return wrapper
    return decorator
