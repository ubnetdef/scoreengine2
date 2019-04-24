import random
import string

import winrm

from . import check_function, config


# DEFAULTS
winrm_config = {
    'transport': 'ntlm',
    'server_cert_validation': 'ignore',
    'read_timeout_sec': 15,
    'operation_timeout_sec': 10,
}
# /DEFAULTS

# CONFIG
if 'winrm' in config['checks']:
    winrm_config.update(config['checks']['winrm'])
# /CONFIG


@check_function('Establish a WinRM connection and execute a basic command')
def check_connect(check):
    check.add_output('Connecting to {HOST!r} as {USER!r} and running command...', **check.config)

    session = winrm.Session(
        'https://{}:5986'.format(check.config['HOST']),
        auth=(check.config['USER'], check.config['PASS']),
        **winrm_config,
    )
    expected = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=100))
    response = session.run_cmd('echo ' + expected)

    check.add_output('... connected!')

    actual = response.std_out.strip().decode()
    if actual != expected:
        check.add_output(
            'ERROR: unexpected result from command (expected {!r}, got {!r}).',
            expected,
            actual,
        )
        return False

    return True
