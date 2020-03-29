# Score Engine 2

This is the software used to perform scoring for UBNetDef's
[Lockdown](https://lockdown.ubnetdef.org/) competition.


## Installation

Score Engine 2 can be "installed" in 3 ways:
1. Pulling the `docker.pkg.github.com/ubnetdef/scoreengine2/scoreengine2` Docker image (requires [Docker Engine](https://docs.docker.com/install/))
   `docker pull docker.pkg.github.com/ubnetdef/scoreengine2/scoreengine2`
2. Building from the `Dockerfile` in the repository (requires [Docker Engine](https://docs.docker.com/install/))
   - `docker build -t scoreengine2 .`
3. Installing the repository as a Python package
   - Clone the repository and change into that directory
   - Optionally activate a virtual environment
   - `pip install .`

In either case, you will need to prepare a config file.


## Configuration

Score Engine 2 expects a configuration file named `config.yml`.
An example, named `config-sample.yml`, is provided.

The configuration file consists of a number of mappings (i.e. `key: value` pairs).
Each key is in described in a sub-section having the same name below, and may
have a value that is another mapping or a sequence (i.e. list of values).

### `bank`

This is a mapping that configures the Score Engine to use the [Bank API](https://github.com/ubnetdef/bank-api)

- `enabled` (boolean): whether or not the Bank API should be used
- `url` (string): the full URL (including the protocol and the path) of the
   Bank API's endpoint for transferring money to the earning team
- `username` (string): the username of the Score Engine's Bank API user
- `password` (string): the password of the Score Engine's Bank API user

**Example:**
```yaml
bank:
  enabled: yes
  url: https://bank.example.com/internalGiveMoney
  username: scoreengine
  password: secret
```

### `celery`

This is a mapping that allows configuring [Celery](http://www.celeryproject.org/).

- `backend` (string): see [Celery docs](https://docs.celeryproject.org/en/latest/userguide/configuration.html#result-backend)
- `broker` (string): see [Celery docs](https://docs.celeryproject.org/en/latest/userguide/configuration.html#broker-settings)
- `worker` (mapping): see [Celery docs](https://docs.celeryproject.org/en/latest/userguide/configuration.html#worker)

**Example:** Use a MySQL database as the results backend, RabbitMQ as a broker, and
workers that concurrently process up to 20 tasks, with log level INFO and tracebacks.
```yaml
celery:
  backend: "mysql+pymysql://username:password@database.example.com:3306/dbname"
  broker: "amqp://username:password@rabbitmq.example.com:5672//"
  worker:
    concurrency: 20
    loglevel: INFO
    traceback: yes
```

### `checks`

This is a mapping that allows overriding default parameters of groups of checks.

**Example:** change the ICMP timeout to 5 seconds and the FTP directory to `/opt/`

### `database`

This is a mapping that will be used by the SQLAlchemy ORM to establish
connections to the database engine.

The simplest mapping will specify the database URL (`url`).

**Example:**
```yaml
database:
  url: "mysql+pymysql://username:password@database.example.com:3306/scoreengine"
```

**See also:**
- [SQLAlchemy database URL format](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls)
- [SQLAlchemy create_engine parameters](https://docs.sqlalchemy.org/en/13/core/engines.html#sqlalchemy.create_engine)

### `logging`

This is a mapping that configures logging.

- `format` (string): see [LogRecord attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes)
- `level` (string): see [Logging Levels](https://docs.python.org/3/library/logging.html#logging-levels)

**Example:**
```yaml
logging:
  format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  level: INFO
```

### `round`

This is a mapping that determines how the Score Engine treats each round.

- `duration` (integer): once we start a round, we wait this many seconds before
   starting the next round; this does not consider how long it takes for a
   round to complete
- `jitter` (integer): each round can start up to this many seconds before or
   after the expected duration (determined at random); can be used to increase
   uncertainty about when a round will start

**Example:** Wait 50 to 70 seconds between the start of each round
```yaml
round:
  duration: 60
  jitter: 10
```

### `services`

This is a sequence of mappings that configures the services that are being scored. _Note that this is
only considered when doing the database setup._

- `name` (string): Custom name used to identify the service (usually unique).
- `check` (string): Module and function names, joined by `.` (full stop or period),
  in the form `<module_name>.<function_name>`, e.g. `database.check_query_mysql`
  or `ftp.check_upload_download`:
    - Module name is the file name in `./scoreengine/checks` without the `.py` extension
    - Function name is from within the module (some modules have mutiple functions)
- `data` (sequence of mappings):
    - `key` (string):
        - Check-specific identifier for an item of data that might be used in checks
        - If multiple mappings are provided with the same key, one of them will
          be randomly selected for use
        - `USERPASS` is "special", in that it will be broken into two mappings
          (`USER` and `PASS`) before being sent to the checks; the value is
          split at `||`
    - `value` (string):
        - Value corresponding to the key specified by `key`
        - `{team}` will be replaced with the team number
    - `editable` (boolean; default: `false`): whether blue teams can edit this 
      mapping in the Inject Engine
    - `hidden` (boolean; default: `false`): whether this mapping should be
      hidden in the Inject Engine

**Example:**
- Check if `dns.example.com` contains an `A` record for `ad.example.com`
  that maps to `192.168.<team_number>.14`
- Check if we can SSH into `192.168.<team_number>.22` with username `demo`
  and password `changeme` (allowing the blue team to change the credentials)

```yaml
services:
  - name: DNS
    check: dns.check_dns
    data:
      - key: HOST
        value: "dns.example.com"
      - key: LOOKUP
        value: "ad.example.com"
      - key: TYPE
        value: A
      - key: EXPECTED
        value: "192.168.{team}.14"
  - name: Client X SSH
    check: ssh.check_connect
    data:
      - key: HOST
        value: "192.168.{team}.22"
      - key: USERPASS
        value: "demo||changeme"
        editable: yes
```

### `teams`

This is a mapping that configures the teams to be checked. _Note that this is
only considered when doing the database setup._

- `minimum` (integer): the smallest team number to be configured (inclusive)
- `maximum` (integer): the largest team number to be configured (inclusive)
- `check_teams` (sequence of integers): the teams that should be marked as
   check teams (and hence are hidden from the Inject Engine's public score board)

**Example:** Configure 15 teams (`{1, 2, 3, ..., 15}`), with `13`, `14` and `15` as check teams
```yaml
teams:
  minimum: 1
  maximum: 15
  check_teams: [13, 14, 15]
```

### `trafficgen`

This is a mapping that is used to simulate additional (unscored) network
traffic that can operate on a different schedule than the scored network
traffic. Checks will be performed in the same way as scored checks, but without
storing the results and calling the Bank API.

- `number` (integer): the maximum number of checks scheduled per traffic round
- `sleep` (integer): the amount of time to wait between traffic generation rounds

**Example:** Generate up to 20 random checks every 15 seconds
```yaml
trafficgen:
  number: 20
  sleep: 15
```


## Usage

> TODO: This section is in need of improvement (more details and examples).
However, the CLI provides documentation about it's commands via `--help`.

1. Create the configuration file `config.yml`
   - If using a container, mount the file to `/opt/scoreengine2/config.yml`
2. Run `scoreengine2` as needed (see `scoreengine2 --help`)
