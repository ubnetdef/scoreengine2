from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import random
import signal
import sys
import threading
import time

import celery

from . import config, models, tasks, utils


SleepRange = namedtuple('SleepRange', ['minimum', 'maximum'])


class Master:

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
            print('Cold shutdown')
            sys.exit(1)
        else:
            # First request to stop
            print('Warm shutdown')
            self.no_more_rounds = True

    def run(self, use_task_queue):
        while not self.no_more_rounds:
            print('Preparing to start round {} ...'.format(self.current_round))

            round_thread = threading.Thread(
                target=self.schedule_round_checks,
                args=(self.current_round, use_task_queue))
            round_thread.start()

            print('... round {} started.'.format(self.current_round))

            sleep_duration = random.randint(
                self.sleep_range.minimum, self.sleep_range.maximum)
            print('Sleeping for {} seconds until the next round.'.format(sleep_duration))
            time.sleep(sleep_duration)

            self.current_round += 1

    @staticmethod
    def schedule_round_checks(current_round, use_task_queue):
        print('\tStarting round #{}'.format(current_round))

        with utils.session_scope() as session:
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
                print(results)

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

        print('\tCompleted round #{}'.format(current_round))
