"""Module for monitoring the cross-chain transfers on each supported and
active blockchain.

"""
import concurrent.futures
import logging
import threading
import time

from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.configuration import config
from pantos.validatornode.configuration import get_blockchain_config

_logger = logging.getLogger(__name__)


def run_monitor() -> None:
    """Run the cross-chain transfer monitor for each supported and
    active blockchain.

    """
    threading.Thread(target=_run_monitor_workers).start()


def _run_monitor_workers() -> None:
    active_blockchains = [
        blockchain for blockchain in Blockchain
        if get_blockchain_config(blockchain)['active']
    ]
    interval = config['monitor']['interval']
    max_workers = max(1, config['monitor']['number_threads'] - 1)
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers) as executor:
        while True:
            futures_blockchains = {
                executor.submit(
                    TransferInteractor().detect_new_transfers,  # yapf bug
                    blockchain): blockchain
                for blockchain in active_blockchains
            }
            for future in concurrent.futures.as_completed(futures_blockchains):
                blockchain = futures_blockchains[future]
                try:
                    future.result()
                except Exception:
                    _logger.critical(
                        f'error while monitoring {blockchain.name}',
                        exc_info=True)
            time.sleep(interval)
