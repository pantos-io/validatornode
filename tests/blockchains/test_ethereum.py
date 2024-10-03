import atexit
import pathlib
import tempfile
import unittest.mock
import uuid

import eth_account.account
import eth_account.messages
import hexbytes
import pytest
import semantic_version  # type: ignore
import web3
import web3.exceptions
from pantos.common.blockchains.base import NodeConnections
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.base import TransactionNonceTooLowError
from pantos.common.blockchains.base import TransactionUnderpricedError
from pantos.common.blockchains.base import VersionedContractAbi
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi
from pantos.common.types import BlockchainAddress

from pantos.validatornode.blockchains.base import BlockchainClient
from pantos.validatornode.blockchains.base import NonMatchingForwarderError
from pantos.validatornode.blockchains.base import \
    SourceTransferIdAlreadyUsedError
from pantos.validatornode.blockchains.ethereum import _EIP712_DOMAIN_NAME
from pantos.validatornode.blockchains.ethereum import _EIP712_DOMAIN_SALT
from pantos.validatornode.blockchains.ethereum import \
    _TRANSFER_TO_MESSAGE_TYPES
from pantos.validatornode.blockchains.ethereum import EthereumClient
from pantos.validatornode.blockchains.ethereum import EthereumClientError
from pantos.validatornode.entities import CrossChainTransfer

_CHAIN_ID = 1638

_DESTINATION_BLOCK_NUMBER = 20842624

_DESTINATION_TRANSACTION_HASH = hexbytes.HexBytes(
    '0x5792e26d11cdf54155de59de5ddcca3f9d084ce89f4b5d4f9e50ec30c726be70')

_SOURCE_BLOCK_NUMBER = 51065469

_SOURCE_TRANSACTION_HASH = hexbytes.HexBytes(
    '0x79a6ae275eae47bbb9c63dcf18e5d14a647d4d39a3463f06d25a581853d8bdc3')

_INCOMING_TRANSFER = CrossChainTransfer(
    source_blockchain=Blockchain.FANTOM,
    destination_blockchain=Blockchain.ETHEREUM,
    source_hub_address=BlockchainAddress(
        '0xC892F1D09a7BEF98d65e7f9bD4642d36BC506441'),
    source_transfer_id=24926,
    source_transaction_id='0x7dad1b0c2fd7904ef92acb6bea4b156434db36ea60acf'
    '0abe1974d79efe958a6', source_block_number=15827532,
    source_block_hash='0x00004ad700002e0ef34532486b441d24508db3a477193c32f'
    '44abe8299cb5bb5', sender_address=BlockchainAddress(
        '0x1368229bF4D073Ce3DD3c4EBDC34082Aab82bbc3'),
    recipient_address=BlockchainAddress(
        '0x1368229bF4D073Ce3DD3c4EBDC34082Aab82bbc3'),
    source_token_address=BlockchainAddress(
        '0x5538e600dc919f72858dd4D4F5E4327ec6f2af60'),
    destination_token_address=BlockchainAddress(
        '0xC892F1D09a7BEF98d65e7f9bD4642d36BC506441'), amount=18372630000,
    fee=50000000, service_node_address=BlockchainAddress(
        '0x726265A9e352F2e9f15F255957840992803cED7d'))

_OUTGOING_TRANSFER_LOGS = [
    web3.datastructures.AttributeDict({
        'address': '0x0F911887da88500a364Fa925f72A8F24709EE3aC',
        'topics': [
            hexbytes.HexBytes(
                '0xe2d69d9df6c1e740c72aecc4a0cd85eca27cbc5273ec079de974008f492'
                'a9f8b')
        ],
        'data': hexbytes.HexBytes(
            '0x000000000000000000000000000000000000000000000000000000000000000'
            '40000000000000000000000000000000000000000000000000000000000000001'
            '00000000000000000000000096f4b54091f223e1343352ae932ff385f025e3010'
            '00000000000000000000000000000000000000000000000000000000000012000'
            '00000000000000000000007eade9ae29c756d77a370353dc2ef5482d6b5219000'
            '00000000000000000000000000000000000000000000000000000000001800000'
            '0000000000000000000000000000000000000000000000000000127a398000000'
            '000000000000000000000000000000000000000000000000001faa3b500000000'
            '000000000000000000aae34ec313a97265635b8496468928549cdd4ab70000000'
            '00000000000000000000000000000000000000000000000000000002a30784137'
            '36393430306534653564374533376165314241304330456643466130434644356'
            '33136356234000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000002a30783863323'
            '44439624561356231393230303946423037383631613746633233456139664532'
            '3233656300000000000000000000000000000000000000000000'),
        'blockNumber': 9480704,
        'transactionHash': hexbytes.HexBytes(
            '0xb3b517e400f3eba3804126d2072cdfc8e13eba03402efb17f5beabb8abd8141'
            'e'),
        'transactionIndex': 15,
        'blockHash': hexbytes.HexBytes(
            '0x29b78d019efc8a3edb4043426deef8c837aac793d7cc2f10f288df57c1e6b29'
            '8'),
        'logIndex': 34,
        'removed': False
    }),
    web3.datastructures.AttributeDict({
        'address': '0x0F911887da88500a364Fa925f72A8F24709EE3aC',
        'topics': [
            hexbytes.HexBytes(
                '0xe2d69d9df6c1e740c72aecc4a0cd85eca27cbc5273ec079de974008f492'
                'a9f8b')
        ],
        'data': hexbytes.HexBytes(
            '0x000000000000000000000000000000000000000000000000000000000000000'
            '30000000000000000000000000000000000000000000000000000000000000003'
            '00000000000000000000000096f4b54091f223e1343352ae932ff385f025e3010'
            '00000000000000000000000000000000000000000000000000000000000012000'
            '00000000000000000000007eade9ae29c756d77a370353dc2ef5482d6b5219000'
            '00000000000000000000000000000000000000000000000000000000001800000'
            '00000000000000000000000000000000000000000000000000000ae85bc000000'
            '000000000000000000000000000000000000000000000000001faa3b500000000'
            '000000000000000000aae34ec313a97265635b8496468928549cdd4ab70000000'
            '00000000000000000000000000000000000000000000000000000002a30786141'
            '45333445633331334139373236353633354238343936343638393238353439636'
            '46434414237000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000002a30784337383'
            '93537383463613034613431393135443931363034366533303445323563323636'
            '3836646400000000000000000000000000000000000000000000'),
        'blockNumber': 9480697,
        'transactionHash': hexbytes.HexBytes(
            '0x7db79ac657e81d2a255cd39013a709b2710be4b1a0d5bc1967be6c10c0feb93'
            '7'),
        'transactionIndex': 2,
        'blockHash': hexbytes.HexBytes(
            '0x95f48bfd5f6b71da3f321c063ba0d4c700781d1ddc4cb92fe6dcefc0b88edfe'
            '8'),
        'logIndex': 5,
        'removed': False
    }),
    web3.datastructures.AttributeDict({
        'address': '0x0F911887da88500a364Fa925f72A8F24709EE3aC',
        'topics': [
            hexbytes.HexBytes(
                '0xe2d69d9df6c1e740c72aecc4a0cd85eca27cbc5273ec079de974008f492'
                'a9f8b')
        ],
        'data': hexbytes.HexBytes(
            '0x000000000000000000000000000000000000000000000000000000000000000'
            '20000000000000000000000000000000000000000000000000000000000000005'
            '00000000000000000000000096f4b54091f223e1343352ae932ff385f025e3010'
            '00000000000000000000000000000000000000000000000000000000000012000'
            '00000000000000000000007eade9ae29c756d77a370353dc2ef5482d6b5219000'
            '00000000000000000000000000000000000000000000000000000000001800000'
            '0000000000000000000000000000000000000000000000000000232aaf8000000'
            '000000000000000000000000000000000000000000000000001faa3b500000000'
            '000000000000000000aae34ec313a97265635b8496468928549cdd4ab70000000'
            '00000000000000000000000000000000000000000000000000000002a30786141'
            '45333445633331334139373236353633354238343936343638393238353439636'
            '46434414237000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000002a30783644376'
            '64338353637314445394162376366343432363639363031303231664345373332'
            '4634396400000000000000000000000000000000000000000000'),
        'blockNumber': 9480697,
        'transactionHash': hexbytes.HexBytes(
            '0x42e8586384d49e9c67eb2b7dae4668dd430e1d29792106ae04e60cf7048a4f3'
            '5'),
        'transactionIndex': 1,
        'blockHash': hexbytes.HexBytes(
            '0x95f48bfd5f6b71da3f321c063ba0d4c700781d1ddc4cb92fe6dcefc0b88edfe'
            '8'),
        'logIndex': 2,
        'removed': False
    })
]

_OUTGOING_TRANSFERS = [
    CrossChainTransfer(
        source_blockchain=Blockchain.ETHEREUM,
        destination_blockchain=Blockchain.BNB_CHAIN,
        source_hub_address=BlockchainAddress(
            '0x0F911887da88500a364Fa925f72A8F24709EE3aC'),
        source_transfer_id=4,
        source_transaction_id=_SOURCE_TRANSACTION_HASH.to_0x_hex(),
        source_block_number=_SOURCE_BLOCK_NUMBER,
        source_block_hash='0x29b78d019efc8a3edb4043426deef8c837aac793d7cc2f10f'
        '288df57c1e6b298', sender_address=BlockchainAddress(
            '0x96f4B54091f223e1343352AE932fF385f025E301'),
        recipient_address=BlockchainAddress(
            '0xA769400e4e5d7E37ae1BA0C0EfCFa0CFD5c165b4'),
        source_token_address=BlockchainAddress(
            '0x7eade9AE29C756d77a370353dC2eF5482d6b5219'),
        destination_token_address=BlockchainAddress(
            '0x8c24D9bEa5b192009FB07861a7Fc23Ea9fE223ec'), amount=310000000,
        fee=8500000000, service_node_address=BlockchainAddress(
            '0xaAE34Ec313A97265635B8496468928549cdd4AB7'),
        is_reversal_transfer=False),
    CrossChainTransfer(
        source_blockchain=Blockchain.ETHEREUM,
        destination_blockchain=Blockchain.AVALANCHE,
        source_hub_address=BlockchainAddress(
            '0x0F911887da88500a364Fa925f72A8F24709EE3aC'),
        source_transfer_id=3,
        source_transaction_id='0x7db79ac657e81d2a255cd39013a709b2710be4b1a0d5b'
        'c1967be6c10c0feb937', source_block_number=9480697,
        source_block_hash='0x95f48bfd5f6b71da3f321c063ba0d4c700781d1ddc4cb92fe'
        '6dcefc0b88edfe8', sender_address=BlockchainAddress(
            '0x96f4B54091f223e1343352AE932fF385f025E301'),
        recipient_address=BlockchainAddress(
            '0xaAE34Ec313A97265635B8496468928549cdd4AB7'),
        source_token_address=BlockchainAddress(
            '0x7eade9AE29C756d77a370353dC2eF5482d6b5219'),
        destination_token_address=BlockchainAddress(
            '0xC7895784ca04a41915D916046e304E25c26686dd'), amount=183000000,
        fee=8500000000, service_node_address=BlockchainAddress(
            '0xaAE34Ec313A97265635B8496468928549cdd4AB7'),
        is_reversal_transfer=False),
    CrossChainTransfer(
        source_blockchain=Blockchain.ETHEREUM,
        destination_blockchain=Blockchain.POLYGON,
        source_hub_address=BlockchainAddress(
            '0x0F911887da88500a364Fa925f72A8F24709EE3aC'),
        source_transfer_id=2,
        source_transaction_id='0x42e8586384d49e9c67eb2b7dae4668dd430e1d2979210'
        '6ae04e60cf7048a4f35', source_block_number=9480697,
        source_block_hash='0x95f48bfd5f6b71da3f321c063ba0d4c700781d1ddc4cb92fe'
        '6dcefc0b88edfe8', sender_address=BlockchainAddress(
            '0x96f4B54091f223e1343352AE932fF385f025E301'),
        recipient_address=BlockchainAddress(
            '0xaAE34Ec313A97265635B8496468928549cdd4AB7'),
        source_token_address=BlockchainAddress(
            '0x7eade9AE29C756d77a370353dC2eF5482d6b5219'),
        destination_token_address=BlockchainAddress(
            '0x6D7fC85671DE9Ab7cf442669601021fCE732F49d'), amount=590000000,
        fee=8500000000, service_node_address=BlockchainAddress(
            '0xaAE34Ec313A97265635B8496468928549cdd4AB7'),
        is_reversal_transfer=False)
]

_PRIVATE_KEY = \
    'edfb7c4593d4cc9f8a28768662a848ea1ef92bb2926ed6740a6f554e06a6e045'

_KEYSTORE = (
    '{"address":"ce3bbb8b5f7e568acff039369ee01c2c17585b00","crypto":{"cipher":'
    '"aes-128-ctr","ciphertext":"a80a2d44d92ac4067b77c4437d1d2dd580a6de21a64a6'
    '390eaccccb20b335588","cipherparams":{"iv":"681597fff887664a5fd038970070c9'
    'b8"},"kdf":"scrypt","kdfparams":{"dklen":32,"n":262144,"p":1,"r":8,"salt"'
    ':"1b25f90dc55e98261615173afd831808542ac81fdf550432ba9fc9358d06a17d"},"mac'
    '":"4fdd812f7dd1d8d1bc98f76b735765500d52341d4151beb687042ecef54a84db"},"id'
    '":"e978de5f-e645-4377-a3e7-993eeb82ad4e","version":3}')

_KEYSTORE_PASSWORD = '0@/V4\\Uxz%OW'

_TOKEN_ADDRESS = '0x5Acfa9f0CEADd177825c67226B4Eb4f09293b756'

_VALIDATOR_NONCE = 51187229043241446622

_HUB_ADDRESS = '0x7A9D071aD683B583BfB4cc91c2A21D9bB712Cd32'

_FORWARDER_ADDRESS = '0x7F029687e25D506645030788a54df4B99d837545'

_PAN_TOKEN_ADDRESS = '0x28C768862A63ee0501B10FEC97B2351DD6FaC8C2'

_MINIMUM_VALIDATOR_NODE_SIGNATURES = 3

_VALIDATOR_NODE_ADDRESSES = [
    '0x20B50a828a042B3F01aCB022e0C8A07e817bc9f5',
    '0xC433E88Aa983b552D99Cc98982768f787dE11f18',
    '0x1BE63cf4226F24d5e5C7B64B3bCBf4ceB25aAE31',
    '0x65333C563e7ee024cfe8D171EEBa654D685E90E3'
]

_VALIDATOR_NODE_SIGNATURES = [
    '0xedc95ed3d9eae50b63b104d09b09e7f1c5dafac94cd4922d37123a2a24a09b7736e8088'
    '8e7db95cff4f091989769fc2c52bd918fa1d451cfd38b2b9d4fab977f1b',
    '0x707481611b0d814d762d9d2f13fb320a7e38207c2fac24cd6a196b1260f9880e1ed94f5'
    '02c3bbaf25878c720956b66aa76d6a1e3088aedd144c429d730f17ee81c',
    '0x0ebedff2ee7a275898337345a502c729acc5fe13dc859215f19a57b29c8b20476887e3a'
    '65595014e2d1510434bc80c66992d724acd87075ad6a46b462a0b596a1c',
    '0xb7eb2a9e1906cfbf24a824ec5ced0ad5672ac9824884555ca99fe35641c13d78441c3da'
    '6aacc8ec52bf40a8bf5ef07c68ea15f191be0d98dfcbe4cfb5cc22b401c'
]


@pytest.fixture(scope='module')
def chain_id():
    return _CHAIN_ID


@pytest.fixture(scope='module')
def destination_block_number():
    return _DESTINATION_BLOCK_NUMBER


@pytest.fixture(scope='module')
def destination_transaction_hash():
    return _DESTINATION_TRANSACTION_HASH


@pytest.fixture(scope='module')
def destination_transaction_hash_str(destination_transaction_hash):
    return destination_transaction_hash.to_0x_hex()


@pytest.fixture(scope='module')
def destination_transaction_receipt(destination_block_number,
                                    destination_transaction_hash):
    return {
        'blockNumber': destination_block_number,
        'transactionHash': destination_transaction_hash
    }


@pytest.fixture(scope='module')
def source_block_number():
    return _SOURCE_BLOCK_NUMBER


@pytest.fixture(scope='module')
def source_transaction_hash():
    return _SOURCE_TRANSACTION_HASH


@pytest.fixture(scope='module')
def source_transaction_hash_str(source_transaction_hash):
    return source_transaction_hash.to_0x_hex()


@pytest.fixture(scope='module')
def source_transaction_receipt(source_block_number, source_transaction_hash):
    return {
        'blockNumber': source_block_number,
        'transactionHash': source_transaction_hash
    }


@pytest.fixture(scope='module')
def source_transaction_event_logs(source_block_number,
                                  source_transaction_hash):
    return [{
        'event': 'TransferFromSucceeded',
        'args': {
            'sourceTransferId': _OUTGOING_TRANSFERS[0].source_transfer_id,
            'request': {
                'destinationBlockchainId': _OUTGOING_TRANSFERS[0].
                destination_blockchain.value,
                'sender': _OUTGOING_TRANSFERS[0].sender_address,
                'recipient': _OUTGOING_TRANSFERS[0].recipient_address,
                'sourceToken': _OUTGOING_TRANSFERS[0].source_token_address,
                'destinationToken': _OUTGOING_TRANSFERS[0].
                destination_token_address,
                'amount': _OUTGOING_TRANSFERS[0].amount,
                'serviceNode': _OUTGOING_TRANSFERS[0].service_node_address,
                'fee': _OUTGOING_TRANSFERS[0].fee,
                'nonce': None,
                'validUntil': None
            },
            'signature': None
        },
        'transactionHash': source_transaction_hash,
        'blockNumber': source_block_number,
        'blockHash': hexbytes.HexBytes(
            _OUTGOING_TRANSFERS[0].source_block_hash)
    }]


@pytest.fixture(scope='module')
def eip712_domain_data(protocol_version, chain_id):
    return {
        'name': _EIP712_DOMAIN_NAME,
        'version': str(protocol_version.major),
        'chainId': chain_id,
        'verifyingContract': _FORWARDER_ADDRESS,
        'salt': _EIP712_DOMAIN_SALT
    }


@pytest.fixture(scope='module')
def incoming_transfer_message_data():
    return {
        'request': {
            'sourceBlockchainId': _INCOMING_TRANSFER.source_blockchain.value,
            'sourceTransferId': _INCOMING_TRANSFER.source_transfer_id,
            'sourceTransactionId': _INCOMING_TRANSFER.source_transaction_id,
            'sender': _INCOMING_TRANSFER.sender_address,
            'recipient': _INCOMING_TRANSFER.recipient_address,
            'sourceToken': _INCOMING_TRANSFER.source_token_address,
            'destinationToken': _INCOMING_TRANSFER.destination_token_address,
            'amount': _INCOMING_TRANSFER.amount,
            'nonce': _VALIDATOR_NONCE
        },
        'destinationBlockchainId': _INCOMING_TRANSFER.destination_blockchain.
        value,
        'pantosHub': _HUB_ADDRESS,
        'pantosForwarder': _FORWARDER_ADDRESS,
        'pantosToken': _PAN_TOKEN_ADDRESS
    }


@pytest.fixture(scope='module')
def keystore_file_path():
    keystore_file_path = pathlib.Path(tempfile.mkstemp()[1])
    with keystore_file_path.open('w') as keystore_file:
        keystore_file.write(_KEYSTORE)
    atexit.register(keystore_file_path.unlink)
    return keystore_file_path


@pytest.fixture(scope='module')
def w3():
    return web3.Web3(web3.EthereumTesterProvider())


@pytest.fixture(scope='module')
def node_connections(w3):
    node_connections = NodeConnections[web3.Web3]()
    node_connections.add_node_connection(w3)
    return node_connections


@pytest.fixture(scope='module')
@unittest.mock.patch.object(EthereumClient, '_get_config')
def ethereum_client(mock_get_config, config_dict, chain_id, keystore_file_path,
                    node_connections):
    # Load keystore configuration from the keystore file
    # This is typically done by the validator
    with keystore_file_path.open() as keystore_file:
        keystore = keystore_file.read()
    mock_blockchain_config = {
        'providers': [''],
        'fallback_providers': [''],
        'average_block_time': 14,
        'confirmations': 12,
        'chain_id': chain_id,
        'private_key': keystore,
        'private_key_password': _KEYSTORE_PASSWORD
    }
    mock_get_config.return_value = mock_blockchain_config
    mock_create_node_connections = unittest.mock.MagicMock()
    mock_create_node_connections.return_value = node_connections
    with unittest.mock.patch('pantos.validatornode.blockchains.base.config',
                             config_dict):
        ethereum_client = EthereumClient()
    assert ethereum_client.get_utilities()._default_private_key == _PRIVATE_KEY
    ethereum_client._EthereumClient__create_node_connections = \
        mock_create_node_connections
    ethereum_client.get_utilities().create_node_connections = \
        mock_create_node_connections
    return ethereum_client


@unittest.mock.patch.object(EthereumClient, 'get_utilities')
@unittest.mock.patch.object(EthereumClient, '_get_config',
                            return_value={'provider_timeout': None})
@unittest.mock.patch.object(EthereumClient, '__init__', lambda *args: None)
def test_create_node_connections_correct(mock_get_config, mock_get_utilities,
                                         node_connections):
    mock_get_utilities(
    ).create_node_connections.return_value = node_connections
    assert EthereumClient()._EthereumClient__create_node_connections() \
        == node_connections


def test_get_blockchain_correct(ethereum_client):
    assert ethereum_client.get_blockchain() is Blockchain.ETHEREUM
    assert EthereumClient.get_blockchain() is Blockchain.ETHEREUM


def test_get_error_class_correct(ethereum_client):
    assert ethereum_client.get_error_class() is EthereumClientError
    assert EthereumClient.get_error_class() is EthereumClientError


@pytest.mark.parametrize(
    'provider', [(web3.Web3.IPCProvider('/ipc/path'),
                  web3.Web3.WebsocketProvider('ws://127.0.0.1'), ''),
                 (web3.Web3.HTTPProvider('https://127.0.0.1/resource'),
                  web3.Web3.HTTPProvider('https://127.0.0.2/resource'),
                  '127.0.0.1, 127.0.0.2')])
def test_get_blockchain_node_domain_correct(provider, ethereum_client):
    w3_1 = web3.Web3(provider[0])
    w3_2 = web3.Web3(provider[1])
    node_connections = NodeConnections[web3.Web3]()
    node_connections.add_node_connection(w3_1)
    node_connections.add_node_connection(w3_2)
    domains = ethereum_client._EthereumClient__get_blockchain_nodes_domains(
        node_connections)
    assert domains == provider[2]


def test_get_own_address_correct(ethereum_client):
    assert (ethereum_client.get_own_address() == web3.Account.from_key(
        _PRIVATE_KEY).address)


@pytest.mark.parametrize('token_active', [True, False])
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_is_token_active_correct(mock_create_hub_contract, token_active,
                                 ethereum_client):
    mock_hub_contract = unittest.mock.MagicMock()
    mock_get_token_record = unittest.mock.MagicMock()
    mock_token_record = (token_active, )
    mock_get_token_record.call().get.return_value = mock_token_record
    mock_hub_contract.functions.getTokenRecord.return_value = \
        mock_get_token_record
    mock_create_hub_contract.return_value = mock_hub_contract
    assert ethereum_client.is_token_active(_TOKEN_ADDRESS) is token_active


def test_is_token_active_error(ethereum_client):
    with pytest.raises(EthereumClientError):
        ethereum_client.is_token_active(_TOKEN_ADDRESS)


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract',
                            side_effect=ResultsNotMatchingError())
def test_is_token_active_results_not_matching_error(mocked_create_hub_contract,
                                                    ethereum_client):
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.is_token_active(_TOKEN_ADDRESS)


@pytest.mark.parametrize(
    'address_valid', [('', False), ('0x0', False),
                      ('0x0000000000000000000000000000000000000000', False),
                      ('0x0f688208e2396bc18170dfd9b07f5f8d25e6491a', True),
                      ('0x0F688208E2396bC18170dFd9B07f5F8D25e6491a', True),
                      ('0x0F688208E2396bC18170dFd9B07f5F8D25e6491a1', False)])
def test_is_valid_recipient_address_correct(address_valid, ethereum_client):
    assert (ethereum_client.is_valid_recipient_address(address_valid[0])
            is address_valid[1])


@pytest.mark.parametrize(
    'transaction_id',
    [('', False), ('0x0', False),
     ('0x0F688208E2396bC18170dFd9B07f5F8D25e6491a', False),
     ('0x6751E8D207C8FF2E42FD73A62DA4A48D50CFB1C800E74BF0B79677BEFB2B1A1E',
      True),
     ('0X6751E8D207C8FF2E42FD73A62DA4A48D50CFB1C800E74BF0B79677BEFB2B1A1E',
      False),
     ('0x6751e8d207c8ff2e42fd73a62da4a48d50cfb1c800e74bf0b79677befb2b1a1e',
      True),
     ('0x6751e8d207c8ff2e42fd73a62da4a48d50cfb1c800e74bf0b79677befb2b1a1',
      False),
     ('0x6751e8d207c8ff2e42fd73a62da4a48d50cfb1c800e74bf0b79677befb2b1a1e1',
      False)])
def test_is_valid_transaction_id_correct(transaction_id, ethereum_client):
    assert (ethereum_client.is_valid_transaction_id(transaction_id[0])
            is transaction_id[1])


@pytest.mark.parametrize('nonce_valid', [True, False])
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_is_valid_validator_nonce_correct(mock_create_hub_contract,
                                          nonce_valid, ethereum_client):
    mock_create_hub_contract().caller().isValidValidatorNodeNonce().get.\
        return_value = nonce_valid

    assert (ethereum_client.is_valid_validator_nonce(_VALIDATOR_NONCE) ==
            nonce_valid)


def test_is_valid_validator_nonce_error(ethereum_client):
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.is_valid_validator_nonce(_VALIDATOR_NONCE)

    assert exception_info.value.details['nonce'] == _VALIDATOR_NONCE


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_is_valid_validator_nonce_results_not_matching_error(
        mock_create_hub_contract, ethereum_client):
    mock_create_hub_contract().caller().isValidValidatorNodeNonce().get.\
        side_effect = ResultsNotMatchingError()

    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.is_valid_validator_nonce(_VALIDATOR_NONCE)


def test_is_equal_address(ethereum_client):
    address = '0x0F688208E2396bC18170dFd9B07f5F8D25e6491a'
    assert ethereum_client.is_equal_address(address, address)
    assert ethereum_client.is_equal_address(address, address.lower())
    assert ethereum_client.is_equal_address(address.lower(), address)
    assert ethereum_client.is_equal_address(address.lower(), address.lower())


@pytest.mark.parametrize('external_token_active',
                         [(Blockchain.ETHEREUM, True),
                          (Blockchain.AVALANCHE, False),
                          (Blockchain.SOLANA, False), (Blockchain.CELO, True)])
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_read_external_token_address_correct(mock_create_hub_contract,
                                             external_token_active,
                                             ethereum_client):
    mock_hub_contract = unittest.mock.MagicMock()
    mock_get_external_token_record = unittest.mock.MagicMock()
    mock_external_token_record = (external_token_active[1],
                                  'some_external_token_address')
    mock_get_external_token_record.call().get.return_value = \
        mock_external_token_record
    mock_hub_contract.functions.getExternalTokenRecord.return_value = \
        mock_get_external_token_record
    mock_create_hub_contract.return_value = mock_hub_contract
    external_token_address = ethereum_client.read_external_token_address(
        _TOKEN_ADDRESS, external_token_active[0])
    if external_token_active[1]:
        assert external_token_address == mock_external_token_record[1]
    else:
        assert external_token_address is None


def test_read_external_token_address_error(ethereum_client):
    with pytest.raises(EthereumClientError):
        ethereum_client.read_external_token_address(_TOKEN_ADDRESS,
                                                    Blockchain.BNB_CHAIN)


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract',
                            side_effect=ResultsNotMatchingError())
def test_read_external_token_address_results_not_matching_error(
        mocked_create_hub_contract, ethereum_client):
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.read_external_token_address(_TOKEN_ADDRESS,
                                                    Blockchain.BNB_CHAIN)


@unittest.mock.patch.object(EthereumClient, '_create_forwarder_contract')
def test_read_minimum_validator_node_signatures_correct(
        mock_create_forwarder_contract, ethereum_client):
    mock_create_forwarder_contract().caller().\
        getMinimumValidatorNodeSignatures().get.return_value = \
        _MINIMUM_VALIDATOR_NODE_SIGNATURES

    minimum_signatures = \
        ethereum_client.read_minimum_validator_node_signatures()

    assert minimum_signatures == _MINIMUM_VALIDATOR_NODE_SIGNATURES


@unittest.mock.patch.object(EthereumClient, '_create_forwarder_contract',
                            side_effect=ResultsNotMatchingError)
def test_read_minimum_validator_node_signatures_results_not_matching_error(
        mock_create_forwarder_contract, ethereum_client):
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.read_minimum_validator_node_signatures()


@unittest.mock.patch.object(EthereumClient, '_get_config',
                            return_value={'forwarder': _FORWARDER_ADDRESS})
def test_read_minimum_validator_node_signatures_other_error(
        mock_get_config, ethereum_client):
    with pytest.raises(EthereumClientError):
        ethereum_client.read_minimum_validator_node_signatures()


@pytest.mark.parametrize('from_block_number', [8608490, 8608492])
@pytest.mark.parametrize(
    'latest_block_number',
    [8608491, 8608492, 8608493, 8608494, 8608495, 8608496])
@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_read_outgoing_transfers_from_block_correct(mock_get_config,
                                                    from_block_number,
                                                    latest_block_number,
                                                    ethereum_client, w3):
    mock_config = {
        'hub': _OUTGOING_TRANSFERS[0].source_hub_address,
        'outgoing_transfers_number_blocks': 2
    }
    mock_get_config.return_value = mock_config

    def mock_get_logs(filter_params):
        return [
            log for log in _OUTGOING_TRANSFER_LOGS
            if log.blockNumber >= filter_params['fromBlock']  # type: ignore
            and log.blockNumber <= filter_params['toBlock']  # type: ignore
        ]

    with unittest.mock.patch.object(w3.eth, 'get_logs', mock_get_logs):
        with unittest.mock.patch.object(w3.eth, 'get_block_number',
                                        return_value=latest_block_number):
            response = ethereum_client.read_outgoing_transfers_from_block(
                from_block_number)
    assert (response.outgoing_transfers == [
        transfer for transfer in _OUTGOING_TRANSFERS
        if transfer.source_block_number >= from_block_number
        and transfer.source_block_number <= latest_block_number
    ])
    assert response.to_block_number == latest_block_number


def test_read_outgoing_transfers_from_block_error(ethereum_client, w3):
    from_block_number = 1000
    with unittest.mock.patch.object(w3.eth, 'get_block_number',
                                    side_effect=Exception):
        with pytest.raises(EthereumClientError) as exception_info:
            ethereum_client.read_outgoing_transfers_from_block(
                from_block_number)
    assert (
        exception_info.value.details['from_block_number'] == from_block_number)


def test_read_outgoing_transfers_from_block_results_not_matching_error(
        ethereum_client, w3):
    from_block_number = 1000
    with unittest.mock.patch.object(w3.eth, 'get_block_number',
                                    side_effect=ResultsNotMatchingError):
        with pytest.raises(ResultsNotMatchingError):
            ethereum_client.read_outgoing_transfers_from_block(
                from_block_number)


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_read_outgoing_transfers_in_transaction_correct(
        mock_create_hub_contract, source_transaction_receipt,
        source_transaction_event_logs, ethereum_client, w3):
    mock_hub_contract = mock_create_hub_contract()
    event = mock_hub_contract.events.TransferFromSucceeded()
    event.process_receipt().get.return_value = source_transaction_event_logs
    transaction_id = source_transaction_receipt['transactionHash'].to_0x_hex()
    hub_address = _OUTGOING_TRANSFERS[0].source_hub_address

    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    return_value=source_transaction_receipt):
        assert (ethereum_client.read_outgoing_transfers_in_transaction(
            transaction_id, hub_address) == [_OUTGOING_TRANSFERS[0]])


def test_read_outgoing_transfers_in_transaction_error(
        ethereum_client, source_transaction_hash_str):
    hub_address = _OUTGOING_TRANSFERS[0].source_hub_address
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.read_outgoing_transfers_in_transaction(
            source_transaction_hash_str, hub_address)
    assert (exception_info.value.details['transaction_id'] ==
            source_transaction_hash_str)
    assert exception_info.value.details['hub_address'] == hub_address


def test_read_outgoing_transfers_in_transaction_results_not_matching_error(
        source_transaction_hash_str, ethereum_client, w3):
    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    side_effect=ResultsNotMatchingError):
        hub_address = _OUTGOING_TRANSFERS[0].source_hub_address
        with pytest.raises(ResultsNotMatchingError):
            ethereum_client.read_outgoing_transfers_in_transaction(
                source_transaction_hash_str, hub_address)


@pytest.mark.parametrize('token_decimals', [8, 18])
@unittest.mock.patch.object(EthereumClient, '_create_token_contract')
def test_read_token_decimals_correct(mock_create_token_contract,
                                     token_decimals, ethereum_client):
    mock_token_contract = unittest.mock.MagicMock()
    mock_decimals = unittest.mock.MagicMock()
    mock_decimals.call().get.return_value = token_decimals
    mock_token_contract.functions.decimals.return_value = mock_decimals
    mock_create_token_contract.return_value = mock_token_contract
    assert (
        ethereum_client.read_token_decimals(_TOKEN_ADDRESS) == token_decimals)


def test_read_token_decimals_error(ethereum_client):
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.read_token_decimals(_TOKEN_ADDRESS)
    assert exception_info.value.details['token_address'] == _TOKEN_ADDRESS


@unittest.mock.patch.object(EthereumClient, '_create_token_contract',
                            side_effect=ResultsNotMatchingError())
def test_read_token_decimals_results_not_matching_error(
        mocked_create_token_contract, ethereum_client):
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.read_token_decimals(_TOKEN_ADDRESS)


@pytest.mark.parametrize('read_destination_transfer_id', [True, False])
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
def test_read_transfer_to_transaction_data_correct(
        mock_create_hub_contract, read_destination_transfer_id,
        destination_block_number, destination_transaction_hash_str,
        destination_transaction_receipt, ethereum_client, w3):
    destination_transfer_id = 5363
    mock_hub_contract = mock_create_hub_contract()
    event = mock_hub_contract.events.TransferToSucceeded()
    event.process_receipt().__getitem__().get.return_value = {
        'args': {
            'destinationTransferId': destination_transfer_id
        }
    }

    with unittest.mock.patch.object(
            w3.eth, 'get_transaction_receipt',
            return_value=destination_transaction_receipt):
        data_response = ethereum_client._read_transfer_to_transaction_data(
            destination_transaction_hash_str, read_destination_transfer_id)

    assert data_response.block_number == destination_block_number
    if read_destination_transfer_id:
        assert (
            data_response.destination_transfer_id == destination_transfer_id)


@pytest.mark.parametrize('errors',
                         [(ResultsNotMatchingError, ResultsNotMatchingError),
                          (Exception, EthereumClientError)])
def test_read_transfer_to_transaction_data_error(
        errors, destination_transaction_hash_str, ethereum_client, w3):
    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    side_effect=errors[0]):
        with pytest.raises(errors[1]):
            ethereum_client._read_transfer_to_transaction_data(
                destination_transaction_hash_str, True)


@unittest.mock.patch.object(EthereumClient, '_create_forwarder_contract')
def test_read_validator_node_addresses_correct(mock_create_forwarder_contract,
                                               ethereum_client):
    mock_create_forwarder_contract().caller().\
        getValidatorNodes().get.return_value = _VALIDATOR_NODE_ADDRESSES

    read_addresses = ethereum_client.read_validator_node_addresses()

    assert read_addresses == _VALIDATOR_NODE_ADDRESSES


@unittest.mock.patch.object(EthereumClient, '_create_forwarder_contract',
                            side_effect=ResultsNotMatchingError)
def test_read_validator_node_addresses_results_not_matching_error(
        mock_create_forwarder_contract, ethereum_client):
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.read_validator_node_addresses()


@unittest.mock.patch.object(EthereumClient, '_get_config',
                            return_value={'forwarder': _FORWARDER_ADDRESS})
def test_read_validator_node_addresses_other_error(mock_get_config,
                                                   ethereum_client):
    with pytest.raises(EthereumClientError):
        ethereum_client.read_validator_node_addresses()


@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_recover_transfer_to_signer_address_correct(
        mock_get_config, chain_id, eip712_domain_data,
        incoming_transfer_message_data, ethereum_client):
    mock_config = {
        'chain_id': chain_id,
        'hub': _HUB_ADDRESS,
        'forwarder': _FORWARDER_ADDRESS,
        'pan_token': _PAN_TOKEN_ADDRESS
    }
    mock_get_config.return_value = mock_config
    signed_message = web3.Account.sign_typed_data(
        _PRIVATE_KEY, eip712_domain_data, _TRANSFER_TO_MESSAGE_TYPES,
        incoming_transfer_message_data)
    request = BlockchainClient.TransferToSignerAddressRecoveryRequest(
        source_blockchain=_INCOMING_TRANSFER.source_blockchain,
        source_transaction_id=_INCOMING_TRANSFER.source_transaction_id,
        source_transfer_id=_INCOMING_TRANSFER.source_transfer_id,
        sender_address=_INCOMING_TRANSFER.sender_address,
        recipient_address=_INCOMING_TRANSFER.recipient_address,
        source_token_address=_INCOMING_TRANSFER.source_token_address,
        destination_token_address=_INCOMING_TRANSFER.destination_token_address,
        amount=_INCOMING_TRANSFER.amount, validator_nonce=_VALIDATOR_NONCE,
        signature=signed_message.signature.to_0x_hex())

    recovered_signer_address = \
        ethereum_client.recover_transfer_to_signer_address(request)

    expected_signer_address = web3.Account.from_key(_PRIVATE_KEY).address
    assert recovered_signer_address == expected_signer_address


@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_recover_transfer_to_signer_address_error(mock_get_config, chain_id,
                                                  ethereum_client):
    mock_config = {
        'chain_id': chain_id,
        'hub': _HUB_ADDRESS,
        'forwarder': _FORWARDER_ADDRESS,
        'pan_token': _PAN_TOKEN_ADDRESS
    }
    mock_get_config.return_value = mock_config
    request = BlockchainClient.TransferToSignerAddressRecoveryRequest(
        source_blockchain=_INCOMING_TRANSFER.source_blockchain,
        source_transaction_id=_INCOMING_TRANSFER.source_transaction_id,
        source_transfer_id=_INCOMING_TRANSFER.source_transfer_id,
        sender_address=_INCOMING_TRANSFER.sender_address,
        recipient_address=_INCOMING_TRANSFER.recipient_address,
        source_token_address=_INCOMING_TRANSFER.source_token_address,
        destination_token_address=_INCOMING_TRANSFER.destination_token_address,
        amount=_INCOMING_TRANSFER.amount, validator_nonce=_VALIDATOR_NONCE,
        signature='invalid_signature')

    with pytest.raises(EthereumClientError):
        ethereum_client.recover_transfer_to_signer_address(request)


@unittest.mock.patch.object(
    EthereumClient, '_get_config', return_value={
        'chain_id': _CHAIN_ID,
        'hub': _HUB_ADDRESS,
        'forwarder': _FORWARDER_ADDRESS,
        'pan_token': _PAN_TOKEN_ADDRESS
    })
def test_sign_transfer_to_message_correct(mock_get_config, eip712_domain_data,
                                          incoming_transfer_message_data,
                                          ethereum_client):
    request = BlockchainClient.TransferToMessageSignRequest(
        incoming_transfer=_INCOMING_TRANSFER, validator_nonce=_VALIDATOR_NONCE,
        destination_hub_address=_HUB_ADDRESS,
        destination_forwarder_address=_FORWARDER_ADDRESS)
    signature = ethereum_client.sign_transfer_to_message(request)

    signable_message = eth_account.messages.encode_typed_data(
        eip712_domain_data, _TRANSFER_TO_MESSAGE_TYPES,
        incoming_transfer_message_data)
    signer_address = eth_account.account.Account.recover_message(
        signable_message, signature=signature)
    assert signer_address == web3.Account.from_key(_PRIVATE_KEY).address


def test_sign_transfer_to_message_destination_blockchain_error(
        ethereum_client):
    incoming_transfer = _OUTGOING_TRANSFERS[0]
    assert incoming_transfer.destination_blockchain is not Blockchain.ETHEREUM

    request = BlockchainClient.TransferToMessageSignRequest(
        incoming_transfer=incoming_transfer, validator_nonce=_VALIDATOR_NONCE,
        destination_hub_address=_HUB_ADDRESS,
        destination_forwarder_address=_FORWARDER_ADDRESS)
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.sign_transfer_to_message(request)

    assert exception_info.value.details['request'] == request


@unittest.mock.patch('web3.Account.sign_typed_data', side_effect=Exception)
@unittest.mock.patch.object(
    EthereumClient, '_get_config', return_value={
        'chain_id': _CHAIN_ID,
        'hub': _HUB_ADDRESS,
        'forwarder': _FORWARDER_ADDRESS,
        'pan_token': _INCOMING_TRANSFER.destination_token_address
    })
def test_sign_transfer_to_message_sign_message_error(mock_get_config,
                                                     mock_sign_message,
                                                     ethereum_client):
    request = BlockchainClient.TransferToMessageSignRequest(
        incoming_transfer=_INCOMING_TRANSFER, validator_nonce=_VALIDATOR_NONCE,
        destination_hub_address=_HUB_ADDRESS,
        destination_forwarder_address=_FORWARDER_ADDRESS)
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.sign_transfer_to_message(request)

    assert exception_info.value.details['request'] == request


def test_sort_validator_node_signatures_correct(ethereum_client):
    request = dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES))
    sorted_signer_addresses, sorted_signatures = ethereum_client.\
        _EthereumClient__sort_validator_node_signatures(request)

    assert set(sorted_signer_addresses) == set(_VALIDATOR_NODE_ADDRESSES)
    assert set(sorted_signatures) == set(_VALIDATOR_NODE_SIGNATURES)
    assert len(sorted_signer_addresses) == 4
    assert len(sorted_signatures) == 4
    assert sorted_signer_addresses[0] == _VALIDATOR_NODE_ADDRESSES[2]
    assert sorted_signatures[0] == _VALIDATOR_NODE_SIGNATURES[2]
    assert sorted_signer_addresses[1] == _VALIDATOR_NODE_ADDRESSES[0]
    assert sorted_signatures[1] == _VALIDATOR_NODE_SIGNATURES[0]
    assert sorted_signer_addresses[2] == _VALIDATOR_NODE_ADDRESSES[3]
    assert sorted_signatures[2] == _VALIDATOR_NODE_SIGNATURES[3]
    assert sorted_signer_addresses[3] == _VALIDATOR_NODE_ADDRESSES[1]
    assert sorted_signatures[3] == _VALIDATOR_NODE_SIGNATURES[1]


@unittest.mock.patch(
    'pantos.validatornode.blockchains.ethereum.database_access')
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_start_transfer_to_submission_correct(mock_get_config,
                                              mock_create_hub_contract,
                                              mock_database_access,
                                              ethereum_client,
                                              node_connections, w3):
    mock_config = {
        'hub': '0xFB37499DC5401Dc39a0734df1fC7924d769721d5',
        'pan_token': _INCOMING_TRANSFER.destination_token_address,
        'min_adaptable_fee_per_gas': 1000000000,
        'max_total_fee_per_gas': 50000000000,
        'adaptable_fee_increase_factor': 1.101,
        'blocks_until_resubmission': 10
    }
    mock_get_config.return_value = mock_config
    internal_transfer_id = 26849
    blockchain_nonce = 4713
    internal_transaction_id = uuid.uuid4()
    mock_database_access.read_transfer_nonce.return_value = blockchain_nonce
    mock_hub_contract = unittest.mock.MagicMock()
    mock_contract_caller = unittest.mock.MagicMock()
    mock_contract_caller.isValidValidatorNodeNonce().get.return_value = True
    mock_hub_contract.caller.return_value = mock_contract_caller
    versioned_hub_contract_abi = VersionedContractAbi(
        ContractAbi.PANTOS_HUB, semantic_version.Version('1.0.0'))
    mock_hub_contract.events = \
        ethereum_client.get_utilities().create_contract(
            mock_config['hub'], versioned_hub_contract_abi,
            node_connections).events
    mock_create_hub_contract.return_value = mock_hub_contract
    mock_start_transaction_submission = unittest.mock.MagicMock()
    mock_start_transaction_submission.return_value = internal_transaction_id

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, _INCOMING_TRANSFER, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with unittest.mock.patch.object(ethereum_client.get_utilities(),
                                    'start_transaction_submission',
                                    mock_start_transaction_submission):
        with unittest.mock.patch.object(w3.eth, 'get_transaction_count',
                                        return_value=blockchain_nonce):
            response = ethereum_client.start_transfer_to_submission(request)

    assert response == internal_transaction_id
    mock_database_access.update_transfer_nonce.assert_called_once_with(
        internal_transfer_id, Blockchain.ETHEREUM, blockchain_nonce)
    mock_start_transaction_submission.assert_called_once()


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_start_transfer_to_submission_node_communication_error(
        mock_get_config, mock_create_hub_contract, ethereum_client, w3):
    internal_transfer_id = 24526
    error_message = 'some blockchain node error message'

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, _INCOMING_TRANSFER, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with unittest.mock.patch.object(w3.eth, 'get_transaction_count',
                                    side_effect=Exception(error_message)):
        with pytest.raises(EthereumClientError) as exception_info:
            ethereum_client.start_transfer_to_submission(request)

    assert str(exception_info.value.__context__) == error_message
    assert exception_info.value.details['request'] == request


def test_start_transfer_to_submission_destination_blockchain_error(
        ethereum_client):
    internal_transfer_id = 38952
    incoming_transfer = _OUTGOING_TRANSFERS[0]
    assert incoming_transfer.destination_blockchain is not Blockchain.ETHEREUM

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, incoming_transfer, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with pytest.raises(EthereumClientError) as exception_info:
        ethereum_client.start_transfer_to_submission(request)

    assert exception_info.value.details['request'] == request


@pytest.mark.parametrize(
    'transaction_error',
    [TransactionNonceTooLowError, TransactionUnderpricedError])
@unittest.mock.patch(
    'pantos.validatornode.blockchains.ethereum.database_access')
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_start_transfer_to_submission_transaction_error(
        mock_get_config, mock_create_hub_contract, mock_database_access,
        transaction_error, ethereum_client):
    internal_transfer_id = 19484

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, _INCOMING_TRANSFER, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with unittest.mock.patch.object(ethereum_client.get_utilities(),
                                    'start_transaction_submission',
                                    side_effect=transaction_error):
        with pytest.raises(EthereumClientError) as exception_info:
            ethereum_client.start_transfer_to_submission(request)

    assert exception_info.value.details['request'] == request
    mock_database_access.reset_transfer_nonce.assert_called_once_with(
        internal_transfer_id)


@pytest.mark.parametrize(
    'verify_transfer_to_error',
    [('PantosHub: source transfer ID already used',
      SourceTransferIdAlreadyUsedError),
     ('PantosHub: Forwarder of Hub and transferred token must match',
      NonMatchingForwarderError),
     ('some unknown error message', EthereumClientError)])
@unittest.mock.patch.object(EthereumClient, '_create_hub_contract')
@unittest.mock.patch.object(EthereumClient, '_get_config')
def test_start_transfer_to_submission_verify_transfer_error(
        mock_get_config, mock_create_hub_contract, verify_transfer_to_error,
        ethereum_client):
    internal_transfer_id = 91734
    mock_hub_contract = unittest.mock.MagicMock()
    mock_verify_transfer_to = unittest.mock.MagicMock()
    mock_verify_transfer_to.call.side_effect = \
        web3.exceptions.ContractLogicError(verify_transfer_to_error[0])
    mock_hub_contract.functions.verifyTransferTo.return_value = \
        mock_verify_transfer_to
    mock_create_hub_contract.return_value = mock_hub_contract

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, _INCOMING_TRANSFER, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with pytest.raises(verify_transfer_to_error[1]):
        ethereum_client.start_transfer_to_submission(request)


@unittest.mock.patch.object(EthereumClient, '_create_hub_contract',
                            side_effect=ResultsNotMatchingError)
def test_start_transfer_to_submission_results_not_matching_error(
        mock_create_hub_contract, ethereum_client):
    internal_transfer_id = 273695

    request = BlockchainClient.TransferToSubmissionStartRequest(
        internal_transfer_id, _INCOMING_TRANSFER, _VALIDATOR_NONCE,
        dict(zip(_VALIDATOR_NODE_ADDRESSES, _VALIDATOR_NODE_SIGNATURES)))
    with pytest.raises(ResultsNotMatchingError):
        ethereum_client.start_transfer_to_submission(request)
