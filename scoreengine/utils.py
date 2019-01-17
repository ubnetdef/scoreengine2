import collections
from contextlib import contextmanager
import logging
import random
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from scoreengine import (
    Session,
    config,
    db_engine,
    models,
)


logger = logging.getLogger(__name__)


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def serialize_check(session, team: models.Team, service: models.Service,
                    round_number: Optional[int]=-1):
    team_service_data = (session
        .query(models.TeamService.key, models.TeamService.value)
        .filter_by(team=team)
        .filter_by(service=service)
        .all()
    )

    # Collect the config into a key:list-of-values dictionary
    check_config = collections.defaultdict(list)
    for key, value in team_service_data:
        check_config[key].append(value)

    # Reduce the config to key:value
    for key in check_config:
        check_config[key] = random.choice(check_config[key])

    # Split USERPASS into separate USER and PASS k/v pairs
    if 'USERPASS' in check_config and '||' in check_config['USERPASS']:
        check_config['USER'], check_config['PASS'] = (
            check_config['USERPASS'].split('||', 1))

    task_description = dict(
        check=dict(
            file_name=service.group,
            function_name=service.check,
        ),
        config=check_config,
        official=round_number > 0,
        output=[],
        passed=False,
        round_number=round_number,
        service_id=service.id,
        service_name=service.name,
        team_id=team.id,
    )
    return task_description


def init_db_from_config():
    """Initialize the database with teams (including a check team) and services."""
    with session_scope() as session:
        logger.debug('Re-creating database tables')
        models.Base.metadata.drop_all(db_engine)
        models.Base.metadata.create_all(db_engine)

        teams = {}
        assert config['teams']['minimum'] < config['teams']['maximum']

        for team in range(config['teams']['minimum'], config['teams']['maximum'] + 1):
            is_check_team = team == config['teams']['maximum']
            logger.debug('Creating team %s%s', team, ' (check team)' if is_check_team else '')

            teams[team] = models.Team('Team {}'.format(team), check_team=is_check_team)
            session.add(teams[team])

        for cfg in config['services']:
            logger.debug('Adding service %r for all teams', cfg['name'])

            check_group, check_function = cfg['check'].split('.', 1)
            service = models.Service(cfg['name'], check_group, check_function)
            session.add(service)

            session.add_all(
                models.TeamService(
                    team,
                    service,
                    datum['key'],
                    str(datum['value']).format(team=team_num),
                    datum.get('edit'),
                    datum.get('hidden'),
                    order,
                )
                for team_num, team in teams.items()
                for order, datum in enumerate(cfg['data'])
            )
