import logging

from celery import Celery
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
import yaml


def _load_config_from_yaml(file_name: str='config.yaml'):
    with open(file_name) as file:
        return yaml.load(file)


config = _load_config_from_yaml()


celery_app = Celery(
    __name__,
    backend=(
        None
        if config['celery']['backend'] is None
        else 'db+{}'.format(config['celery']['backend'])
    ),
    broker=config['celery']['broker'],
)


# TODO: move to config
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.DEBUG,
)
logging.getLogger('celery.app.trace').setLevel(logging.WARNING)


db_engine = engine_from_config(config['database'], prefix='',)
Session = sessionmaker(bind=db_engine)
