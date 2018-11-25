import imaplib
import socket

from . import config, check_function


# DEFAULTS
imap_config = {
    'timeout': 15,
}
# /DEFAULTS

# CONFIG
if 'imap' in config['checks']:
    imap_config.update(config['checks']['imap'])

socket.setdefaulttimeout(imap_config['timeout'])
# /CONFIG


@check_function('Successful authentication against the email server')
def check_imap_login(check):
    check.add_output('Starting check...')

    host = check.config['HOST']
    port = int(check.config['PORT'])

    check.add_output('Connecting to {host}:{port}...', host=host, port=port)

    # TODO: consider making this choice via a separate configuration
    imap_class = imaplib.IMAP4_SSL if port == 993 else imaplib.IMAP4
    imap_obj = imap_class(host, port)

    check.add_output('Logging in as {USER}', **check.config)

    imap_obj.login(check.config['USER'], check.config['PASS'])

    check.add_output('Logged in!')

    return True
