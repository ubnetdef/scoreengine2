import logging

import click
from sqlalchemy.sql import func

from scoreengine import (
    celery_app,
    config,
    models,
    runner,
    utils,
)


cli = click.Group()


@cli.group()
def db():
    """Database queries (including initialization)."""


@db.command()
def init():
    """Initialize the database."""
    logging.getLogger('scoreengine').setLevel(config['logging']['level'])
    utils.init_db_from_config()


@db.command()
def list_services():
    """List configured services."""
    with utils.session_scope() as session:
        services = session.query(models.Service).all()
        for service in services:
            click.echo(service)


@db.command()
def list_teams():
    """List configured teams."""
    with utils.session_scope() as session:
        teams = session.query(models.Team).all()
        for team in teams:
            click.echo(team)


@cli.command()
@click.option('--use-task-queue/--no-task-queue',
              help='Whether or not a task queue (Celery) should be used.')
@click.option('--reset', is_flag=True,
              help='Discard all previous rounds and checks.')
@click.option('--resume', is_flag=True,
              help='Continue where the last round stopped.')
@click.option('--start-round', default=1, type=click.IntRange(min=1),
              help='Round number to start checks at.')
def run(use_task_queue, reset, resume, start_round):
    """Perform scheduling of round checks for scoring."""
    logging.getLogger('scoreengine').setLevel(config['logging']['level'])

    if reset:
        with utils.session_scope() as session:
            session.query(models.Round).delete()

    if resume:
        with utils.session_scope() as session:
            max_round = session.query(func.max(models.Round.number)).first()[0]
        if max_round is not None:
            start_round = max_round + 1

    runner.Runner(start_round).run(use_task_queue=use_task_queue)


@cli.command()
def worker():
    """Process checks on the Celery task queue."""
    celery_app.autodiscover_tasks(['scoreengine.tasks'])
    worker(app=celery_app).run(**config['celery']['worker'])


@cli.command()
@click.option('--service', '-s', 'services', type=int, multiple=True,
              help='ID of service to be checked.')
@click.option('--team', '-t', 'teams', type=int, multiple=True,
              help='ID of team to be checked.')
def check(services, teams):
    """Perform one-time checks as a dry-run (without the task queue)."""
    results = runner.perform_round_checks(
        current_round=None,
        use_task_queue=False,
        only_enabled=False,
        service_ids=services,
        team_ids=teams,
    )
    for result in results:
        passed = result['passed']
        click.secho(
            '{result}:\t{team:15} | {service:20} | {check}'.format(
                check='{}.{}'.format(
                    result['check']['file_name'],
                    result['check']['function_name']
                ),
                result='Pass' if passed else 'Fail',
                service='[#{}] {}'.format(
                    result['service_id'],
                    result['service_name'],
                ),
                team='[#{}] {}'.format(
                    result['team_id'],
                    result['team_name'],
                ),
            ),
            fg='green' if passed else 'red'
        )
        if not passed:
            click.echo('\n'.join(result['output']))
