# TODO: test this module

import ldap

from . import config, check_function


# DEFAULTS
ldap_config = {
    'timeout': 15,
}
# /DEFAULTS

# CONFIG
if 'ldap' in config['checks']:
    ldap_config.update(config['checks']['ldap'])
# /CONFIG


@check_function('Successful and correct query against the AD (LDAP) server')
def check_ldap_lookup(check):
    check.add_output('Starting check...')

    # Setup LDAP
    connection = ldap.initialize('ldap://{HOST}'.format(**check.config))

    # Bind to the user we're using to lookup
    actual_username = '{USER}@{DOMAIN}'.format(**check.config)
    password = check.config['PASS']

    connection.protocol_version = ldap.VERSION3
    connection.set_option(ldap.OPT_NETWORK_TIMEOUT, ldap_config['timeout'])
    connection.simple_bind_s(actual_username, password)

    # We're good!
    return True
