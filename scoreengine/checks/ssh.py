import paramiko
import time

from . import check_function, config


# DEFAULTS
ssh_config = {
    'timeout': 10,
}
# /DEFAULTS

# CONFIG
if 'ssh' in config['checks']:
    ssh_config.update(config['checks']['ssh'])
# /CONFIG


@check_function('Establish an SSH connection and execute a basic command')
def check_connect(check):
    with paramiko.SSHClient() as client:
        # Allow connecting without known host keys
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        check.add_output('Connecting to {HOST!r} as {USER!r} ...', **check.config)
        client.connect(
            hostname=check.config['HOST'],
            username=check.config['USER'],
            password=check.config['PASS'],
            timeout=ssh_config['timeout'],
        )
        check.add_output('... connected!')

        check.add_output('Executing command whoami ...')
        stdin, stdout, stderr = client.exec_command('whoami')
        actual_user = next(stdout).rstrip()  # strip trailing new line
        if actual_user != check.config['USER']:
            check.add_output(
                'ERROR: unexpected result (expected {!r}, got {!r}).',
                check.config['USER'],
                actual_user,
            )
            return False
        check.add_output('... command ran successfully!')

    return True


@check_function('Establish an SSH connection and execute a basic command')
def check_connect_ledger(check):
    with paramiko.SSHClient() as client:
    
        # Allow connecting without known host keys
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        check.add_output('Connecting to {HOST!r} as {USER!r} ...', **check.config)
        client.connect(
            hostname=check.config['HOST'],
            username=check.config['USER'],
            password=check.config['PASS'],
            timeout=ssh_config['timeout'],)
            
        check.add_output('... connected!')
        check.add_output('Checking content of ledger file')
        stdin, stdout, stderr = client.exec_command('cat /home/scoredCrypto/ledger.cryp')
        file_output = next(stdout).rstrip()  # strip trailing new line
        if abs(int(time.time()) - int(file_output)) > 150:
            check.add_output(
                'ERROR: unexpected result (expected {!r}, got {!r}).',
                "time within 150 seconds of: {}".format(str(int(time.time()))),
                file_output,
            )
            return False
        check.add_output('... command ran successfully!')

    return True