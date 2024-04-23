import contextlib
import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.monitor import run_monitor

_INACTIVE_BLOCKCHAINS = [Blockchain.FANTOM, Blockchain.SOLANA]

_INTERVAL = 10

_NUMBER_THREADS = 4


class _Break(Exception):
    pass


class _MockThread:
    def __init__(self, target):
        self.__target = target

    def start(self):
        self.__target()


class _MockFuture:
    def __init__(self, function, *args):
        try:
            self.__result = function(*args)
        except Exception as error:
            self.__result = error

    def result(self):
        if isinstance(self.__result, Exception):
            raise self.__result
        return self.__result


class _MockThreadPoolExecutor(contextlib.AbstractContextManager):
    def __init__(self, max_workers):
        assert max_workers == max(1, _NUMBER_THREADS - 1)

    def __exit__(self, *args):
        pass

    def submit(self, function, *args):
        return _MockFuture(function, *args)


def _mock_as_completed(dictionary):
    return dictionary.keys()


def _mock_get_blockchain_config(blockchain):
    return {'active': blockchain not in _INACTIVE_BLOCKCHAINS}


@pytest.mark.parametrize('detect_new_transfers_error', [True, False])
@unittest.mock.patch.object(TransferInteractor, 'detect_new_transfers')
@unittest.mock.patch('time.sleep', side_effect=_Break)
@unittest.mock.patch('pantos.validatornode.monitor.get_blockchain_config',
                     _mock_get_blockchain_config)
@unittest.mock.patch(
    'pantos.validatornode.monitor.config',
    {'monitor': {
        'interval': _INTERVAL,
        'number_threads': _NUMBER_THREADS
    }})
@unittest.mock.patch('concurrent.futures.as_completed', _mock_as_completed)
@unittest.mock.patch('concurrent.futures.ThreadPoolExecutor',
                     _MockThreadPoolExecutor)
@unittest.mock.patch('threading.Thread', _MockThread)
def test_run_monitor(mock_time_sleep, mock_detect_new_transfers,
                     detect_new_transfers_error):
    if detect_new_transfers_error:
        mock_detect_new_transfers.side_effect = Exception
    with pytest.raises(_Break):
        run_monitor()
    mock_time_sleep.assert_called_once_with(_INTERVAL)
    assert (mock_detect_new_transfers.call_count == len(Blockchain) -
            len(_INACTIVE_BLOCKCHAINS))
    mock_detect_new_transfers.assert_has_calls([
        unittest.mock.call(blockchain)
        for blockchain in Blockchain if blockchain not in _INACTIVE_BLOCKCHAINS
    ], any_order=True)
