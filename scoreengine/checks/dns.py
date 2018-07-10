from dns.resolver import Resolver

from . import config, check_function


# DEFAULTS
dns_config = {
    'timeout': 15,
    'lifetime': 15,
}
# /DEFAULTS

# CONFIG
if 'dns' in config['checks']:
    dns_config.update(config['checks']['dns'])
# /CONFIG


@check_function('Successful and correct query against the DNS server')
def check_dns(check):
    # Setup the resolver
    resolver = Resolver()
    resolver.nameservers = [check.config['HOST']]
    resolver.timeout = dns_config['timeout']
    resolver.lifetime = dns_config['lifetime']
    
    # Query resolver
    check.add_output('Querying {HOST} for "{LOOKUP}"...', **check.config)
    lookup = resolver.query(check.config['LOOKUP'], check.config['TYPE'])

    found = False
    for ans in lookup:
        if str(ans) == check.config['EXPECTED']:
            found = True
        else:
            check.addOutput('NOTICE: DNS Server returned {}', ans)

    if not found:
        check.addOutput('ERROR: DNS Server did not respond with the correct IP')
        return False

    # We're good!
    return True
