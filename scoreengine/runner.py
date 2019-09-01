from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import random
import signal
import sys
import threading
import time
import typing

import celery
import requests

from . import config, models, tasks, utils


SleepRange = namedtuple('SleepRange', ['minimum', 'maximum'])

logger = logging.getLogger(__name__)


class Runner:

    def __init__(self, start_round: int = 1):
        self.current_round = start_round
        self.start_time = datetime.utcnow()
        self.sleep_range = SleepRange(
            config['round']['duration'] - config['round']['jitter'],
            config['round']['duration'] + config['round']['jitter'],
        )

        # Gracefully handle Ctrl+C
        self.no_more_rounds = False
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, signal_number, frame):
        if self.no_more_rounds:
            # Already asked to stop
            logging.warning('Cold shutdown')
            sys.exit(1)
        else:
            # First request to stop
            logging.warning('Warm shutdown')
            self.no_more_rounds = True

    def run(self, use_task_queue):
        traffic_generator = threading.Thread(
            target=self.generate_traffic,
            args=(use_task_queue,),
        )
        traffic_generator.start()

        self.perform_scoring(use_task_queue)

    def generate_traffic(self, use_task_queue):
        while not self.no_more_rounds:
            logger.debug('Starting traffic generation cycle')

            round_thread = threading.Thread(
                target=perform_round_checks,
                args=(None, use_task_queue, config['trafficgen']['number']),
            )
            round_thread.start()

            logger.debug('Traffic generation cycle complete')
            time.sleep(config['trafficgen']['sleep'])

    def perform_scoring(self, use_task_queue):
        while not self.no_more_rounds:
            logger.debug('Preparing to start round %d', self.current_round)

            round_thread = threading.Thread(
                target=perform_round_checks,
                args=(self.current_round, use_task_queue),
            )
            round_thread.start()

            sleep_duration = random.randint(
                self.sleep_range.minimum, self.sleep_range.maximum)
            logger.debug('Sleeping for %d seconds until the next round', sleep_duration)
            time.sleep(sleep_duration)

            self.current_round += 1


def _get_check_services(session, service_ids, only_enabled=True):
    query = session.query(models.Service)
    if service_ids:
        query = query.filter(models.Service.id.in_(service_ids))
    if only_enabled:
        query = query.filter_by(enabled=True)
    return query.all()


def _get_check_teams(session, team_ids, only_enabled=True):
    query = session.query(models.Team)
    if team_ids:
        query = query.filter(models.Team.id.in_(team_ids))
    if only_enabled:
        query = query.filter_by(enabled=True)
    return query.all()


def perform_round_checks(
    current_round: typing.Optional[int],
    use_task_queue: bool,
    max_checks: typing.Optional[int] = None,
    only_enabled: bool = True,
    service_ids: typing.Optional[typing.Tuple] = None,
    team_ids: typing.Optional[typing.Tuple] = None,
):
    """Schedule checks for the specified round.

    :param current_round: Round number being checked.
    :param use_task_queue: Whether we should use Celery.
    :param max_checks: Maximum number of checks to be performed (if specified).
    :param only_enabled: Only consider enabled services and enabled teams.
    :param service_ids: If specified, limit checks to only the specified services.
    :param team_ids: If specified, limit checks to only the specified teams.
    :return: The result of the performed checks.
    """
    is_official_round = current_round is not None

    logger.info('Starting round %s', current_round if is_official_round else '\b')

    with utils.session_scope() as session:
        if is_official_round:
            session.add(models.Round(current_round))
            session.commit()

        services = _get_check_services(session, service_ids, only_enabled=only_enabled)
        teams = _get_check_teams(session, team_ids, only_enabled=only_enabled)
        check_tasks = [
            tasks.check_task.s(
                utils.serialize_check(session, team, service, current_round)
            )
            for team in teams
            for service in services
        ]

    random.shuffle(check_tasks)
    if max_checks is not None:
        check_tasks = check_tasks[:max_checks]

    if use_task_queue:
        round_group = celery.group(check_tasks)
        promise = round_group.apply_async()
        results = promise.get()
    else:
        with ThreadPoolExecutor(max_workers=config['celery']['worker']['concurrency']) as executor:
            futures = [
                executor.submit(check_task.apply)
                for check_task in check_tasks
            ]
            results = [
                future.result().get()
                for future in futures
            ]

    for result in results:
        # TODO: get team and service names instead of IDs
        logger.debug(
            'Check %(status)s: round %(round)s, team ID %(team)d, service ID %(service)d',
            {
                'status': 'passed' if result['passed'] else 'failed',
                'round': result['round_number'],
                'team': result['team_id'],
                'service': result['service_id'],
            },
        )

    if is_official_round:
        with utils.session_scope() as session:
            for result in results:
                if not result['official']:
                    continue
                session.add(
                    models.Check(
                        team_id=result['team_id'],
                        service_id=result['service_id'],
                        round=result['round_number'],
                        passed=result['passed'],
                        output='\n'.join(result['output']),
                    )
                )

            round_obj = (session.query(models.Round)
                .filter_by(number=current_round)
                .first()
            )
            round_obj.completed = True
            round_obj.finish = datetime.utcnow()

            session.commit()

        if config['bank']['enabled']:
            for result in results:
                if result['passed']:
                    requests.post(
                        config['bank']['url'],
                        data={
                            'username': config['bank']['username'],
                            'password': config['bank']['password'],
                            'team': result['team_id'],
                        },
                    )

    logger.info('Completed round %s', current_round if is_official_round else '\b')

    return results
