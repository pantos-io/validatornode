import contextlib
import pathlib
import tempfile
import unittest.mock

import pytest
from pantos.common.blockchains.enums import Blockchain
from pantos.common.configuration import Config
from pantos.common.configuration import ConfigError

from pantos.validatornode.configuration import get_blockchain_config
from pantos.validatornode.configuration import get_blockchains_rpc_nodes
from pantos.validatornode.configuration import load_config

_CONFIGURATION_LOG = '''
    log:
        format: human_readable
        console:
            enabled: false
        file:
            enabled: true
            name: /path/to/log/file
            max_bytes: 104857600
            backup_count: 10
'''

_CONFIGURATION_APPLICATION = '''
application:
    debug: false
    host: 0.0.0.0
    port: 8081
    mode: primary
    primary_url: http://127.0.0.1:8081/
''' + _CONFIGURATION_LOG

_CONFIGURATION_DATABASE = '''
database:
    url: postgresql://user:password@host/database
    pool_size: 20
    max_overflow: 50
    echo: false
    alembic_config: /path/to/alembic.ini
    apply_migrations: false
'''

_CONFIGURATION_CELERY = '''
celery:
    broker: amqp://user:password@host:5672/vhost
    backend: db+postgresql://user:password@host/database
''' + _CONFIGURATION_LOG

_CONFIGURATION_MONITOR = '''
monitor:
    interval: 30
    number_threads: 4
'''

_CONFIGURATION_TASKS = '''
tasks:
    confirm_transfer:
        retry_interval_in_seconds: 60
        retry_interval_after_error_in_seconds: 300
    submit_transfer_onchain:
        retry_interval_in_seconds: 60
        retry_interval_after_error_in_seconds: 300
    submit_transfer_to_primary_node:
        retry_interval_in_seconds: 60
        retry_interval_after_error_in_seconds: 300
    validate_transfer:
        retry_interval_in_seconds: 60
        retry_interval_after_error_in_seconds: 300
'''

_CONFIGURATION_BLOCKCHAIN = '''
        active: true
        private_key: /path/to/keystore
        private_key_password: password
        providers:
            - https://some.provider
        average_block_time: 14
        provider_timeout: 10
        chain_id: 1
        hub: ''
        forwarder: ''
        pan_token: ''
        from_block: 0
        outgoing_transfers_number_blocks: 2000
        confirmations: 12
        min_adaptable_fee_per_gas: 1000000000
        max_total_fee_per_gas: 50000000000
        adaptable_fee_increase_factor: 1.101
        blocks_until_resubmission: 10
'''

_CONFIGURATION_BLOCKCHAINS = '''
blockchains:
''' + ''.join('    ' + blockchain_name + ':' + _CONFIGURATION_BLOCKCHAIN
              for blockchain_name in sorted(
                  [blockchain.name.lower() for blockchain in Blockchain]))

_CONFIGURATION_SECTIONS = [
    _CONFIGURATION_APPLICATION, _CONFIGURATION_DATABASE, _CONFIGURATION_CELERY,
    _CONFIGURATION_MONITOR, _CONFIGURATION_TASKS, _CONFIGURATION_BLOCKCHAINS
]

_CONFIGURATION = ''.join(_CONFIGURATION_SECTIONS)


@pytest.mark.parametrize('blockchain',
                         [blockchain for blockchain in Blockchain])
def test_get_blockchain_config_correct(blockchain):
    mocked_config = Config('')
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             mocked_config):
        with _prepare_config_file(_CONFIGURATION) as config_file_path:
            load_config(file_path=config_file_path, reload=False)
        blockchain_name = blockchain.name.lower()
        mocked_config['blockchains'][blockchain_name][
            'private_key_password'] = blockchain_name
        blockchain_config = get_blockchain_config(blockchain)
        assert blockchain_config['private_key_password'] == blockchain_name
        assert blockchain_config['provider_timeout'] == 10


@pytest.mark.parametrize('reload_config', [True, False])
def test_load_config_correct(reload_config):
    mocked_config = Config('')
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             mocked_config):
        with _prepare_config_file(_CONFIGURATION) as config_file_path:
            assert not mocked_config.is_loaded()
            load_config(file_path=config_file_path, reload=reload_config)
            assert mocked_config.is_loaded()


@pytest.mark.parametrize('removed_config_section',
                         range(len(_CONFIGURATION_SECTIONS)))
def test_load_config_error(removed_config_section):
    config_sections = _CONFIGURATION_SECTIONS.copy()
    del config_sections[removed_config_section]
    config = ''.join(config_sections)
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             Config('')):
        with _prepare_config_file(config) as config_file_path:
            with pytest.raises(ConfigError):
                load_config(file_path=config_file_path, reload=False)


def test_get_blockchain_rpc_nodes_no_active_blockchains_correct():
    mocked_config = Config('')
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             mocked_config):
        with _prepare_config_file(_CONFIGURATION) as config_file_path:
            load_config(file_path=config_file_path, reload=False)
        for blockchain in Blockchain:
            blockchain_name = blockchain.name.lower()
            mocked_config['blockchains'][blockchain_name]['active'] = False
        assert {} == get_blockchains_rpc_nodes()


def test_get_blockchain_rpc_nodes_correct():
    expected_rpc_nodes = {
        blockchain: (['https://some.provider'], 10.0)
        for blockchain in Blockchain
    }
    mocked_config = Config('')
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             mocked_config):
        with _prepare_config_file(_CONFIGURATION) as config_file_path:
            load_config(file_path=config_file_path, reload=False)
        assert expected_rpc_nodes == get_blockchains_rpc_nodes()


def test_get_blockchain_rpc_nodes_with_fallback_providers_correct():
    expected_rpc_nodes = {
        blockchain: (['https://some.provider',
                      'https://fallback.provider'], 10.0)
        for blockchain in Blockchain
    }
    mocked_config = Config('')
    with unittest.mock.patch('pantos.validatornode.configuration.config',
                             mocked_config):
        with _prepare_config_file(_CONFIGURATION) as config_file_path:
            load_config(file_path=config_file_path, reload=False)
        for blockchain in Blockchain:
            blockchain_name = blockchain.name.lower()
            mocked_config['blockchains'][blockchain_name][
                'fallback_providers'] = ['https://fallback.provider']
        assert expected_rpc_nodes == get_blockchains_rpc_nodes()


@contextlib.contextmanager
def _prepare_config_file(configuration):
    config_file_path = pathlib.Path(tempfile.mkstemp()[1])
    with config_file_path.open('w') as config_file:
        print(configuration, file=config_file)
    try:
        yield str(config_file_path)
    finally:
        config_file_path.unlink()
