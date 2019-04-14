from setuptools import find_packages, setup


setup(
    name='scoreengine2',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'celery',
        'click',
        'dnspython',
        'fake-useragent',
        'paramiko',
        'pymysql',
        'python-ldap',
        'pyyaml',
        'requests',
        'sqlalchemy',
    ],
    entry_points='''
        [console_scripts]
        scoreengine2=scoreengine.cli:cli
    ''',
)
