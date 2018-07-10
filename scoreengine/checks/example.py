from . import check_function


@check_function('Example check that always passes')
def check_example(check):
    return True
