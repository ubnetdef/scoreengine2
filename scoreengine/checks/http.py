# TODO: test check_wordpress

import re

from fake_useragent import UserAgent
import requests

from . import config, check_function


# DEFAULTS
http_config = {
    'timeout': 15,

    'wordpress_login': 'wp-login.php',
    'wordpress_cookie': 'wordpress_logged_in_',

    'gitlab_login': 'users/sign_in',
    'gitlab_cookie': '_gitlab_session',
}
# /DEFAULTS

# CONFIG
if 'http' in config['checks']:
    http_config.update(config['checks']['http'])

FAKE_UA = UserAgent(fallback='Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)')

http_headers = {
    'Connection': 'close',
    'User-Agent': FAKE_UA.random,
}
# /CONFIG


@check_function('Website is online')
def check_http(check):
    # Connect to the website
    check.add_output('Connecting to http://{HOST}:{PORT}', **check.config)
    session = requests.Session()
    req = session.get('http://{HOST}:{PORT}'.format(**check.config),
                      timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return False

    return True


@check_function('Ability to use the Wordpress website')
def check_wordpress(check):
    # Connect to the website
    check.add_output('Connecting to http://{HOST}:{PORT}', **check.config)
    session = requests.Session()
    req = session.get('http://{HOST}:{PORT}'.format(**check.config),
                      timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return False

    check.add_output('Connected!')

    # Load the login page
    login_url = 'http://{HOST}:{PORT}/{login}'.format(
        login=http_config['wordpress_login'], **check.config)
    login_payload = {
        'log': check.config['USER'],
        'pwd': check.config['PASS']
    }

    check.add_output('Loading login page')
    req = session.get(login_url, timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return

    check.add_output('Loaded!')

    # Attempt to login
    check.add_output('Attempting to login')
    req = session.post(login_url, data=login_payload, timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return

    # Check the cookies
    has_login_cookie = False
    for c in session.cookies:
        if http_config['wordpress_cookie'] in c.name:
            has_login_cookie = True

    if not has_login_cookie:
        check.add_output('ERROR: Logged in cookie not set.')
        return

    check.add_output('Logged in!')

    # It passed all our check
    return True


@check_function('Ability to use the gitlab website')
def check_gitlab(check):
    # Connect to the website
    check.add_output('Connecting to http://{HOST}:{PORT}', **check.config)
    session = requests.Session()
    req = session.get('http://{HOST}:{PORT}'.format(**check.config),
                      timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return False

    check.add_output('Connected!')

    # Load the login page
    check.add_output('Loading login page')
    login_url = 'http://{HOST}:{PORT}/{login}'.format(
        login=http_config['gitlab_login'], **check.config)
    req = session.get(login_url, timeout=http_config['timeout'], headers=http_headers)
    matches = re.search('name="authenticity_token" value="([^"]+)"', req.content.decode())

    if not matches:
        check.add_output('ERROR: Login page did not contain needed information')
        return False

    # Attempt a login
    # login_payload = {
    #     'user[login]': check.config['USER'],
    #     'user[password]': check.config['PASS'],
    #     'authenticity_token': matches.group(1)
    # }

    check.add_output('Attempting login')
    req = session.get(login_url, timeout=http_config['timeout'], headers=http_headers)

    if req.status_code != 200:
        check.add_output('ERROR: Page returned status code {}', req.status_code)
        return False

    check.add_output('Loaded!')

    # Check the cookies
    has_login_cookie = False
    for c in session.cookies:
        if http_config['gitlab_cookie'] in c.name:
            has_login_cookie = True

    if not has_login_cookie:
        check.add_output('ERROR: Logged in cookie not set.')
        return False

    check.add_output('Logged in!')

    # It passed all our checks
    return True
