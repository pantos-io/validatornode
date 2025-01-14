"""Main Pantos Validator Node application module.

"""
import logging
import pathlib
import sys

import flask
import semantic_version  # type: ignore
from pantos.common.blockchains.enums import Blockchain
from pantos.common.health import initialize_blockchain_nodes
from pantos.common.logging import LogFile
from pantos.common.logging import LogFormat
from pantos.common.logging import initialize_logger

from pantos.validatornode.blockchains.factory import get_blockchain_client
from pantos.validatornode.blockchains.factory import \
    initialize_blockchain_clients
from pantos.validatornode.configuration import config
from pantos.validatornode.configuration import get_blockchain_config
from pantos.validatornode.configuration import get_blockchains_rpc_nodes
from pantos.validatornode.configuration import load_config
from pantos.validatornode.database import \
    initialize_package as initialize_database_package

_logger = logging.getLogger(__name__)


def create_application() -> flask.Flask:
    """Create the Validator Node application.

    Returns
    -------
    flask.Flask
        Flask application object.

    """
    initialize_application(True)
    from pantos.validatornode.monitor import run_monitor
    run_monitor()
    from pantos.validatornode.restapi import flask_app
    return flask_app


def initialize_application(is_flask_app: bool = False) -> None:
    """Initialize the Validator Node service application by loading the
    configuration, configuring logging and initializing the database.

    """
    # Logging for loading the configuration
    logging.basicConfig(level=logging.INFO)
    try:
        load_config(reload=False)
    except Exception:
        _logger.critical('unable to load the configuration', exc_info=True)
        sys.exit(1)
    # Reconfigure logging based on the loaded configuration
    root_logger = logging.getLogger()
    log_format = LogFormat.from_name(config['application']['log']['format'])
    standard_output = config['application']['log']['console']['enabled']
    if not config['application']['log']['file']['enabled']:
        log_file = None
    else:
        file_path = pathlib.Path(config['application']['log']['file']['name'])
        max_bytes = config['application']['log']['file']['max_bytes']
        backup_count = config['application']['log']['file']['backup_count']
        log_file = LogFile(file_path, max_bytes, backup_count)
    debug = config['application']['debug']
    try:
        initialize_logger(root_logger, log_format, standard_output, log_file,
                          debug)
    except Exception:
        _logger.critical('unable to initialize logging', exc_info=True)
        sys.exit(1)
    # Package-specific initialization
    try:
        initialize_database_package(is_flask_app)
    except Exception:
        _logger.critical('unable to initialize the database', exc_info=True)
        sys.exit(1)
    try:
        initialize_blockchain_clients()
    except Exception:
        _logger.critical('unable to initialize the blockchain clients',
                         exc_info=True)
        sys.exit(1)
    check_protocol_version_compatibility()
    blockchain_rpc_nodes = get_blockchains_rpc_nodes()
    initialize_blockchain_nodes(blockchain_rpc_nodes)


def check_protocol_version_compatibility() -> None:
    try:
        check_hub_contract = (semantic_version.Version(config['protocol'])
                              >= semantic_version.Version('0.2.0'))
        active_blockchains = [
            blockchain for blockchain in Blockchain
            if get_blockchain_config(blockchain)['active']
        ]
        for blockchain in active_blockchains:
            blockchain_client = get_blockchain_client(blockchain)
            if not blockchain_client.\
                    is_protocol_version_supported_by_forwarder_contract():
                _logger.critical(
                    f'incompatible Forwarder contract on {blockchain.name}')
                sys.exit(1)
            if check_hub_contract and not blockchain_client.\
                    is_protocol_version_supported_by_hub_contract():
                _logger.critical(
                    f'incompatible Hub contract on {blockchain.name}')
                sys.exit(1)
    except Exception:
        _logger.critical('unable to check the protocol version compatibility',
                         exc_info=True)
        sys.exit(1)
