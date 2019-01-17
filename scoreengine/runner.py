from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import random
import signal
import sys
import threading
import time

import celery

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
                target=self.schedule_round_checks,
                args=(-1, use_task_queue, config['trafficgen']['number']),
            )
            round_thread.start()

            logger.debug('Traffic generation cycle complete')
            time.sleep(config['trafficgen']['sleep'])

    def perform_scoring(self, use_task_queue):
        while not self.no_more_rounds:
            logger.debug('Preparing to start round %d', self.current_round)

            round_thread = threading.Thread(
                target=self.schedule_round_checks,
                args=(self.current_round, use_task_queue),
            )
            round_thread.start()

            sleep_duration = random.randint(
                self.sleep_range.minimum, self.sleep_range.maximum)
            logger.debug('Sleeping for %d seconds until the next round', sleep_duration)
            time.sleep(sleep_duration)

            self.current_round += 1

    @staticmethod
    def schedule_round_checks(current_round, use_task_queue, max_checks=None):
        is_official_round = current_round > 0

        logger.info('Starting round %d', current_round)

        with utils.session_scope() as session:
            if is_official_round:
                session.add(models.Round(current_round))
                session.commit()

            services = session.query(models.Service).filter_by(enabled=True).all()
            teams = session.query(models.Team).filter_by(enabled=True).all()
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
                    logger.info(
                        'Check %(status)s: round %(round)d, team ID %(team)d, service ID %(service)d',
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

        logger.info('Completed round %d', current_round)


def perform_checks(service_ids, team_ids):
    """Synchronously perform a one-time set of checks of service(s) for team(s)."""
    from pprint import pprint

    with utils.session_scope() as session:
        services = (
            session.query(models.Service)
                .filter(models.Service.id.in_(service_ids))
                .all()
            if service_ids else
            session.query(models.Service).all()
        )

        teams = (
            session.query(models.Team)
                .filter(models.Team.id.in_(team_ids))
                .all()
            if team_ids else
            session.query(models.Team).all()
        )

        for team in teams:
            for service in services:
                result = tasks.check_task(utils.serialize_check(session, team, service))
                pprint(result)
