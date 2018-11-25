import subprocess

from . import config, check_function


# DEFAULTS
icmp_config = {
    'timeout': 10,
    'command': 'ping',
}
# /DEFAULTS

# CONFIG
if 'icmp' in config['checks']:
    icmp_config.update(config['checks']['icmp'])
# /CONFIG


@check_function('1 packet received')
def check_icmp(check):
    command = [
        icmp_config['command'],
        '-c', '1',
        '-t', str(icmp_config['timeout']),
        str(check.config['HOST'])
    ]

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, stderr = proc.communicate()

    check.add_output(output)

    return proc.returncode == 0
