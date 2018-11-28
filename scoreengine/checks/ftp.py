import binascii
import ftplib
import os
import random
import tempfile

from . import config, check_function


# DEFAULTS
ftp_config = {
    'timeout': 15,
    'prefix': 'scoreengine_',
    'directory': '',
}
# /DEFAULTS

# CONFIG
if 'ftp' in config['checks']:
    ftp_config.update(config['checks']['ftp'])
# /CONFIG


@check_function('Successful connect, upload, and deletion of a file')
def check_upload_download(check):
    check.add_output('Connecting to {HOST}...', **check.config)
    with ftplib.FTP(check.config['HOST'], timeout=ftp_config['timeout']) as ftp:
        check.add_output('Connected!')

        # Log in
        check.add_output('Attempting to log in as {USER}', **check.config)
        ftp.login(check.config['USER'], check.config['PASS'])
        check.add_output('Authentication successful!')

        # Create a temporary file with random data for uploading
        check_file = tempfile.NamedTemporaryFile(prefix=ftp_config['prefix'])
        number_of_bytes = random.randint(1000, 9000)
        binary_data = os.urandom(number_of_bytes)
        ascii_data = binascii.hexlify(binary_data)  # twice the size of binary_data
        check_file.write(ascii_data)
        check_file.seek(0)
        check_file_name = ftp_config['directory'] + os.path.basename(check_file.name)
        check_file_size = os.path.getsize(check_file.name)

        # Attempt to upload the file
        ftp.cwd(ftp_config['directory'])
        check.add_output('Uploading file {} with {} bytes...', check_file_name, check_file_size)
        ftp.storbinary('STOR ' + check_file_name, check_file)
        check.add_output('Uploaded!')

        # Validate the uploaded file
        check.add_output("Getting size of {}....".format(check_file_name))
        actual_file_size = ftp.size(check_file_name)
        if actual_file_size != check_file_size:
            check.add_output(
                'File size is {}, not the same as source ({})! Failure!',
                actual_file_size,
                check_file_size,
            )
            return False
        check.add_output('File size check passed!')

        # Delete the uploaded file
        check.add_output("Deleting file {}...".format(check_file_name))
        ftp.delete(check_file_name)
        check.add_output("Deleted!")

    return True
