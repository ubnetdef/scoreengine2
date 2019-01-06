#!/usr/bin/env python

import argparse

from celery.bin.worker import worker
from sqlalchemy.sql import func

from scoreengine import celery_app, config, models, master, setup, tasks, utils


def _validate_check_args(args):
        if args.check_all and any((args.check_services, args.check_teams)):
            parser.error('-ca/--check-all cannot be used with '
                         '-cs/--check-service or -ct/--check-team')
        if not any((args.check_all, args.check_services, args.check_teams)):
            parser.error('-c/--check requires either -ca/--check-all OR one or '
                         'both of -cs/--check-service and -ct/--check-team)')


def main(args):
    if args.reset:
        setup.init_from_config()

    if args.setup:
        setup.init_from_config()
    elif args.check:
        _validate_check_args(args)
        master.perform_checks(args.check_services, args.check_teams)
    elif args.stand_alone or args.master:
        start_round = 1
        if args.resume:
            with utils.session_scope() as session:
                max_round = session.query(func.max(models.Round.number)).first()[0]
            if isinstance(max_round, int):
                start_round = max_round + 1
        elif args.start_round:
            start_round = args.start_round

        master.Master(start_round).run(use_task_queue=args.master)
    elif args.worker:
        celery_app.autodiscover_tasks(['scoreengine.tasks'])
        worker(app=celery_app).run(**config['celery']['worker'])
    else:
        raise NotImplementedError('Unsupported mode')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Score Engine v2')

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--setup', action='store_true', help='initialize the database')
    mode_group.add_argument(
        '-m', '--master', action='store_true', help='only schedule checks to the task queue')
    mode_group.add_argument(
        '-w', '--worker', action='store_true', help='only perform checks from the task queue')
    mode_group.add_argument(
        '--stand-alone', action='store_true', help='schedule and perform checks directly')
    mode_group.add_argument(
        '-c', '--check', action='store_true', help='perform one-time dry-run checks')
    parser.add_argument('-ca', '--check-all', action='store_true',
                        help='check all services for all teams')
    parser.add_argument('-cs', '--check-services', type=int, nargs='+',
                        help='IDs of services to be checked')
    parser.add_argument('-ct', '--check-teams', type=int, nargs='+',
                        help='IDs of teams to be checked')

    round_group = parser.add_mutually_exclusive_group()
    round_group.add_argument(
        '--reset', action='store_true', help='discard all previous rounds and checks')
    round_group.add_argument(
        '--resume', action='store_true', help='resume from the last round checked')
    round_group.add_argument(
        '--start-round', type=int, help='round to start checking from')

    main(parser.parse_args())
