"""Module for creating and initializing a Celery instance.

"""
import logging
import pathlib
import sys

import celery  # type: ignore
from pantos.common.logging import LogFile
from pantos.common.logging import LogFormat
from pantos.common.logging import initialize_logger

from pantos.validatornode.application import initialize_application
from pantos.validatornode.configuration import config
from pantos.validatornode.database import get_engine

_logger = logging.getLogger(__name__)
"""Logger for this module."""


def is_main_module() -> bool:
    """Determine if the current process is a Celery worker process.

    Returns
    -------
    bool
        True if the current process is a Celery worker process.

    """
    return __name__ == '__main__' or any('celery' in arg for arg in sys.argv)


if is_main_module():
    _logger.info('Initializing the Celery application...')
    initialize_application()  # pragma: no cover

celery_app = celery.Celery(
    'pantos.validatornode', broker=config['celery']['broker'],
    backend=config['celery']['backend'], include=[
        'pantos.common.blockchains.tasks',
        'pantos.validatornode.business.transfers'
    ])
"""Celery application instance."""


@celery.signals.after_setup_task_logger.connect  # Celery task logger
@celery.signals.after_setup_logger.connect  # Celery logger
def setup_logger(logger: logging.Logger, *args, **kwargs):
    """Sent after the setup of every single task and Celery logger.
    Used to augment logging configuration.

    Parameters
    ----------
    logger: logging.Logger
        Logger object to be augmented.

    """
    log_format = LogFormat.from_name(config['celery']['log']['format'])
    standard_output = config['celery']['log']['console']['enabled']
    if not config['celery']['log']['file']['enabled']:
        log_file = None
    else:
        file_path = pathlib.Path(config['celery']['log']['file']['name'])
        max_bytes = config['celery']['log']['file']['max_bytes']
        backup_count = config['celery']['log']['file']['backup_count']
        log_file = LogFile(file_path, max_bytes, backup_count)
    debug = config['application']['debug']
    try:
        initialize_logger(logger, log_format, standard_output, log_file, debug)
    except Exception:
        logger.critical('unable to initialize logging', exc_info=True)
        sys.exit(1)


# Additional Celery configuration
celery_app.conf.update(result_expires=None,
                       task_default_exchange='pantos.validatornode',
                       task_default_queue='pantos.validatornode',
                       task_default_routing_key='pantos.validatornode',
                       task_track_started=True,
                       worker_enable_remote_control=False)


# Source: https://stackoverflow.com/questions/43944787/sqlalchemy-celery-with-scoped-session-error/54751019#54751019 # noqa
@celery.signals.worker_process_init.connect
def prep_db_pool(**kwargs):
    """
    When Celery forks the parent process, it includes the db engine & connection
    pool. However, db connections should not be shared across processes. Thus,
    we instruct the engine to dispose of all existing connections, prompting the
    opening of new ones in child processes as needed.
    More info:
    https://docs.sqlalchemy.org/en/latest/core/pooling.html#using-connection-pools-with-multiprocessing
    """ # noqa
    get_engine().dispose()  # pragma: no cover
