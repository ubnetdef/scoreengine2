import pymysql

from . import config, check_function


# DEFAULTS
mysql_config = {
    'timeout': 15,
    'min_tables_count': 0,
    'max_tables_count': -1,
}
# /DEFAULTS

# CONFIG
if 'database' in config['checks']:
    mysql_config.update(config['checks']['database'])
# /CONFIG


@check_function('Login and query against a Wordpress database')
def check_wordpress_mysql(check):
    # Connect to the db
    check.add_output('Connecting to {HOST}:{PORT}', **check.config)
    db = pymysql.connect(
        host=check.config['HOST'],
        port=int(check.config['PORT']),
        user=check.config['USER'],
        passwd=check.config['PASS'],
        db=check.config['DB_LOOKUP'],
        connect_timeout=mysql_config['timeout'])
    check.add_output('Connected!')

    cur = db.cursor()

    # Select the wordpress database
    check.add_output('Querying for some data from the database...')
    cur.execute("SELECT option_value FROM wp_options WHERE option_name = 'blogname';")

    # Verify
    check.add_output('Verifying the data...')
    if cur.rowcount != 1:
        check.add_output('ERROR: Invalid data returned.')
        return

    db_data = cur.fetchone()
    if db_data[0] != check.config['BLOG_NAME']:
        check.add_output('ERROR: Invalid data returned.')
        return

    # We're done
    return True


@check_function('Successful login on the MySQL Database')
def check_query_mysql(check):
    # Connect to the db
    check.add_output('Connecting to {HOST}:{PORT}', **check.config)
    db = pymysql.connect(
        host=check.config['HOST'],
        port=int(check.config['PORT']),
        user=check.config['USER'],
        passwd=check.config['PASS'],
        db=check.config['DB_LOOKUP'],
        connect_timeout=mysql_config['timeout'])
    check.add_output('Connected!')

    cur = db.cursor()

    # Attempt a show tables
    check.add_output('Attempting to describe all tables...')
    cur.execute('SHOW tables;')

    # Verify tables
    if cur.rowcount < mysql_config['min_tables_count']:
        check.add_output('ERROR: The table count returned is incorrect.')
        return False

    if mysql_config['max_tables_count'] > 0:
        if cur.rowcount > mysql_config['max_tables_count']:
            check.add_output('ERROR: The table count returned is incorrect.')
            return False

    # We're done
    return True
