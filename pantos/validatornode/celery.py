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


def is_celery_worker_process() -> bool:
    """Determine if the current process is a Celery worker process.

    Returns
    -------
    bool
        True if the current process is a Celery worker process.

    """
    return (len(sys.argv) > 0 and sys.argv[0].endswith('celery')
            and 'worker' in sys.argv)


if is_celery_worker_process():
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
