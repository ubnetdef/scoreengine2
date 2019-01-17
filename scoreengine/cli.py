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
    click.echo('Initializing database...')
    utils.init_db_from_config()
    click.echo('... database initialized!')


@db.command()
def list_services():
    """List configured services."""
    click.echo('Services:')
    with utils.session_scope() as session:
        services = session.query(models.Service).all()
        for service in services:
            click.echo('  {}'.format(service))


@db.command()
def list_teams():
    """List configured teams."""
    click.echo('Teams:')
    with utils.session_scope() as session:
        teams = session.query(models.Team).all()
        for team in teams:
            click.echo('  {}'.format(team))


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
    if reset:
        with utils.session_scope() as session:
            session.query(models.Round).delete()

    if resume:
        with utils.session_scope() as session:
            max_round = session.query(func.max(models.Round.number)).first()[0]
        print(max_round)
        if isinstance(max_round, int):
            start_round = max_round + 1

    runner.Runner(start_round).run(use_task_queue=use_task_queue)


@cli.command()
def worker():
    """Process checks on the Celery task queue."""
    celery_app.autodiscover_tasks(['scoreengine.tasks'])
    worker(app=celery_app).run(**config['celery']['worker'])


@cli.command()
@click.option('--service', '-s', 'services', multiple=True, help='ID of service to be checked.')
@click.option('--team', '-t', 'teams', multiple=True, help='ID of team to be checked.')
def check(services, teams):
    """Perform a one-time check as a dry-run."""
    runner.perform_checks(services, teams)


# if __name__ == '__main__':
#     cli()
