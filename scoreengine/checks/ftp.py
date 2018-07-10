# TODO: fix and test this module

from binascii import hexlify
from ftplib import FTP
from os.path import basename
from os import urandom
from os.path import getsize
from random import choice
from tempfile import NamedTemporaryFile

from . import config, check_function


# DEFAULTS
ftp_config = {
    'timeout': 15,
    'prefix': 'scoreengine_',
    # 'bufsize': 0,
    'directory': '',
}
# /DEFAULTS

# CONFIG
if 'ftp' in config['checks']:
    ftp_config.update(config['checks']['ftp'])
# /CONFIG


@check_function('Successful connect, upload, and deletion of a file')
def check_upload_download(check):
    # Create a temp file
    check_file = NamedTemporaryFile(prefix=ftp_config['prefix'])

    # Write random amount of bytes to the check_file
    # Size should be 2x random_bytes due to hexlify
    random_bytes = choice(range(1000, 9000))
    check_file.write(hexlify(urandom(random_bytes)))
    check_file.seek(0)

    check_file_name = ftp_config['directory'] + basename(check_file.name)
    check_file_size = getsize(check_file.name)
    ftp = None

    check.add_output('Starting check...')

    try:
        # Start the connection
        check.add_output('Connecting to {HOST}...', **check.config)
        ftp = FTP(check.config['HOST'], timeout=ftp_config['timeout'])
        check.add_output('Connected!')

        # Login
        check.add_output('Attempting to login as {USER}', **check.config)
        ftp.login(check.config['USER'], check.config['PASS'])
        check.add_output('Authentication successful!')

        # Attempt to upload a file
        ftp.cwd(ftp_config['directory'])
        check.add_output('Uploading file {} with {} bytes...', check_file_name, check_file_size)
        ftp.storbinary('STOR ' + check_file_name, check_file)
        check.add_output('Uploaded!')

        # Get the size of the file
        check.add_output('Getting size of {}....'.format(check_file_name))
        actual_size = ftp.size(check_file_name)
        if actual_size != check_file_size:
            check.add_output('File size is {}, not the same as source ({})! Failure!'.format(actual_size, check_file_size))

            ftp.close()
            return
        check.add_output('File size check passed!')

        # Delete it
        check.add_output('Deleting file {}...', check_file_name)
        ftp.delete(check_file_name)
        check.add_output('Deleted!')

        # Passed!
        ftp.close()

        check.setPassed()
        check.add_output('Check successful!')
    except Exception as e:
        check.add_output('ERROR: {}: {}'.format(type(e).__name__, e))

        if ftp is not None:
            ftp.close()

        return
