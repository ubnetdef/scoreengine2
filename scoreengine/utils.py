import collections
from contextlib import contextmanager
import random
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from . import models, Session


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
