import itertools

import pytest
import sqlalchemy
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.models import Blockchain as Blockchain_
from pantos.validatornode.database.models import ForwarderContract
from pantos.validatornode.database.models import HubContract
from pantos.validatornode.database.models import TokenContract
from pantos.validatornode.database.models import Transfer
from pantos.validatornode.database.models import \
    TransferStatus as TransferStatus_
from pantos.validatornode.database.models import ValidatorNode
from pantos.validatornode.database.models import ValidatorNodeSignature

_HUB_CONTRACT_ADDRESSES = [
    '0x266323B9bdE14d2A4Af543A51394AC3c727136CD',
    '0xACe38ade7dec7b4E9f1387A32BD7adc846bD0e3f',
    '28dNo45FSuPjbyQ9LtBAcrvP3MoaWMZGZVvp7z35ybVR'
]

_FORWARDER_CONTRACT_ADDRESSES = [
    '0x57062ea8C7B0ab735D0d3F45a365E8E428F2122C',
    '0x8d2d39856e521B88640a2Ac7feF9126faeDF073a',
    '2fyaAJf1XNoPYjZonuQg4k4HZa3vD4dtFSbXN64knfUZ'
]

_TOKEN_CONTRACT_ADDRESSES = [
    '0x06346C770Cab3A220a1B66fdDAB1eE83B3B6F192',
    '0xA19DF2B7a9B5EBbBF10C9CC05321205bb7f6389a',
    'Cc9SpdtnXmX8MNXo9KrE3LSVuaBrpsmDky1C5Qx4VYdQ'
]

_VALIDATOR_NODE_ADDRESSES = [
    '0x6f935bB33A480269798fF0F26C42859F6b29AF25',
    '0xC01897DEb578DbBb9FD0b79D52228043E6e1Aa3b',
    '0x6B0AaEfc099e2Ec754A39557a3222e1C0B92185f'
]

_SIGNATURES = [
    '0xecf92cfabe6d64c775f18f9b39e5aca5178865a94af31b14760e5e24f630b5c347bab65'
    '1493f6fa31445e6da955c5e4fb903326751a918f33e567369188288201c',
    '0x89f4bb92379a5f1ab97a8dcf01c73d1eb6d25e173fa17286fa5ed2416e36967a3e68f63'
    '4f808e74c1f018cfd55264c9ce961772fcbda4bba627603f7c1961aa11b',
    '0xd21f653198c7a1ea115e29b84f160595a40d5d3e3532e99f22812d866ea076e21755ec7'
    'ac7da2a6aab60906921141d14d4e3b55d094915261df0d134dfa745681c'
]

_TRANSFER_SENDER_ADDRESSES = [
    '0x7Fbe8Bd3F73B923B7E811a12f18AA6519e28288B',
    'EiPdMdudSgNX69pzpNNaQSPo2sZq4tKEQB7hVTziV73w'
]

_TRANSFER_RECIPIENT_ADDRESSES = [
    '0xf76f7A1329b03FBAcf636D0e75aFcB2eCD32EBBE',
    '4KY2xwBBBwrf4zXgwoUhCVo7LdgHp4RvuEG3LunnWf7n'
]

_TRANSFER_AMOUNTS = [117 * 10**18, 53 * 10**16]

_TRANSFER_VALIDATOR_NONCES = [53263935840, 85753781173]

_TRANSFER_TASK_IDS = [
    'b8dfafc1-2420-42c9-b08c-c5987c91aa21',
    '80a3416d-e671-4d77-aff6-f4696ed6749e'
]

_TRANSFER_SOURCE_TRANSFER_IDS = [956111, 610853]

_TRANSFER_DESTINATION_TRANSFER_IDS = [471465, 235249]

_TRANSFER_SOURCE_TRANSACTION_IDS = [
    '0xc13d7905be5c989378a945387cd2a1193627ae606109e28e296d48ddaec66162',
    ('5epeugPjC8PoQuKi39QKNaGe7XCfR27p5fj6Ey1zaZeVmnbECTD7yP1juxH6EbardsoiZvET'
     '5tPT2QhpL4ehqwiB')
]

_TRANSFER_DESTINATION_TRANSACTION_IDS = [
    '0x9b36c54a46c08979a5d348fb630c208c33e024a8df300598a09c6764e321d566',
    ('2N4aj3akx34Si2eeTBTHEMMgJZJXDWYvivGiu8ZBRssjz3w1negoTrM9Sxhcf1MZBKRqkqr6'
     'qyGc6egBsVRdBecH')
]

_TRANSFER_SOURCE_BLOCK_NUMBERS = [17370973, 119764930]

_TRANSFER_DESTINATION_BLOCK_NUMBERS = [9244759, 33624921]

_TRANSFER_NONCES = [75594, 557502]


@pytest.fixture
def database_session(database_session_maker):
    with database_session_maker() as database_session:
        yield database_session
    _delete_database_records(database_session_maker())


@pytest.fixture
def initialized_database_session(database_session_maker):
    _create_database_records(database_session_maker())
    with database_session_maker() as database_session:
        yield database_session
    _delete_database_records(database_session_maker())


@pytest.fixture
def initialized_database_session_maker(database_session_maker):
    _create_database_records(database_session_maker())
    yield database_session_maker
    _delete_database_records(database_session_maker())


@pytest.fixture(params=Blockchain)
def blockchain(request):
    return Blockchain_(id=request.param.value, name=request.param.name)


@pytest.fixture(params=itertools.islice(Blockchain, 2))
def source_blockchain(request):
    return Blockchain_(id=request.param.value, name=request.param.name)


@pytest.fixture(params=itertools.islice(Blockchain, 2, 4))
def other_source_blockchain(request):
    return Blockchain_(id=request.param.value, name=request.param.name)


@pytest.fixture(params=itertools.islice(Blockchain,
                                        len(Blockchain) - 2, len(Blockchain)))
def destination_blockchain(request):
    return Blockchain_(id=request.param.value, name=request.param.name)


@pytest.fixture(params=itertools.islice(Blockchain,
                                        len(Blockchain) - 4,
                                        len(Blockchain) - 2))
def other_destination_blockchain(request):
    return Blockchain_(id=request.param.value, name=request.param.name)


@pytest.fixture
def other_recipient_address():
    return _TRANSFER_RECIPIENT_ADDRESSES[1]


@pytest.fixture(params=_HUB_CONTRACT_ADDRESSES)
def hub_contract(request, blockchain):
    return HubContract(blockchain_id=blockchain.id, address=request.param)


@pytest.fixture
def source_hub_contract(source_blockchain):
    return HubContract(blockchain_id=source_blockchain.id,
                       address=_HUB_CONTRACT_ADDRESSES[0])


@pytest.fixture
def other_source_hub_contract(other_source_blockchain):
    return HubContract(blockchain_id=other_source_blockchain.id,
                       address=_HUB_CONTRACT_ADDRESSES[1])


@pytest.fixture
def destination_hub_contract(destination_blockchain):
    return HubContract(blockchain_id=destination_blockchain.id,
                       address=_HUB_CONTRACT_ADDRESSES[-1])


@pytest.fixture
def other_destination_hub_contract(other_destination_blockchain):
    return HubContract(blockchain_id=other_destination_blockchain.id,
                       address=_HUB_CONTRACT_ADDRESSES[-2])


@pytest.fixture(params=_FORWARDER_CONTRACT_ADDRESSES)
def forwarder_contract(request, blockchain):
    return ForwarderContract(blockchain_id=blockchain.id,
                             address=request.param)


@pytest.fixture
def destination_forwarder_contract(destination_blockchain):
    return ForwarderContract(blockchain_id=destination_blockchain.id,
                             address=_FORWARDER_CONTRACT_ADDRESSES[-1])


@pytest.fixture
def other_destination_forwarder_contract(other_destination_blockchain):
    return ForwarderContract(blockchain_id=other_destination_blockchain.id,
                             address=_FORWARDER_CONTRACT_ADDRESSES[-2])


@pytest.fixture(params=_TOKEN_CONTRACT_ADDRESSES)
def token_contract(request, blockchain):
    return TokenContract(blockchain_id=blockchain.id, address=request.param)


@pytest.fixture
def source_token_contract(source_blockchain):
    return TokenContract(blockchain_id=source_blockchain.id,
                         address=_TOKEN_CONTRACT_ADDRESSES[0])


@pytest.fixture
def other_source_token_contract(other_source_blockchain):
    return TokenContract(blockchain_id=other_source_blockchain.id,
                         address=_TOKEN_CONTRACT_ADDRESSES[1])


@pytest.fixture
def destination_token_contract(destination_blockchain):
    return TokenContract(blockchain_id=destination_blockchain.id,
                         address=_TOKEN_CONTRACT_ADDRESSES[-1])


@pytest.fixture
def other_destination_token_contract(other_destination_blockchain):
    return TokenContract(blockchain_id=other_destination_blockchain.id,
                         address=_TOKEN_CONTRACT_ADDRESSES[-2])


@pytest.fixture
def validator_node_addresses():
    return _VALIDATOR_NODE_ADDRESSES


@pytest.fixture(params=_VALIDATOR_NODE_ADDRESSES)
def validator_node(request, destination_forwarder_contract):
    return ValidatorNode(forwarder_contract=destination_forwarder_contract,
                         address=request.param)


@pytest.fixture
def signatures():
    return _SIGNATURES


@pytest.fixture(params=_SIGNATURES)
def validator_node_signature(request, transfer, validator_node):
    return ValidatorNodeSignature(transfer=transfer,
                                  validator_node=validator_node,
                                  signature=request.param)


@pytest.fixture
def other_validator_nonce():
    return _TRANSFER_VALIDATOR_NONCES[1]


@pytest.fixture
def other_destination_transfer_id():
    return _TRANSFER_DESTINATION_TRANSFER_IDS[1]


@pytest.fixture
def other_destination_transaction_id():
    return _TRANSFER_DESTINATION_TRANSACTION_IDS[1]


@pytest.fixture
def other_destination_block_number():
    return _TRANSFER_DESTINATION_BLOCK_NUMBERS[1]


@pytest.fixture(params=TransferStatus)
def transfer_status(request):
    return TransferStatus_(id=request.param.value, name=request.param.name)


@pytest.fixture(params=[True, False])
def transfer(request, source_blockchain, destination_blockchain,
             source_token_contract, destination_token_contract,
             source_hub_contract, destination_hub_contract,
             destination_forwarder_contract):
    destination_hub_contract = (None
                                if request.param else destination_hub_contract)
    destination_forwarder_contract = (None if request.param else
                                      destination_forwarder_contract)
    task_id = None if request.param else _TRANSFER_TASK_IDS[0]
    destination_transfer_id = (None if request.param else
                               _TRANSFER_DESTINATION_TRANSFER_IDS[0])
    destination_transaction_id = (None if request.param else
                                  _TRANSFER_DESTINATION_TRANSACTION_IDS[0])
    destination_block_number = (None if request.param else
                                _TRANSFER_DESTINATION_BLOCK_NUMBERS[0])
    nonce = None if request.param else _TRANSFER_NONCES[0]
    status_id = (TransferStatus.SOURCE_TRANSACTION_DETECTED.value
                 if request.param else
                 TransferStatus.DESTINATION_TRANSACTION_CONFIRMED.value)
    return Transfer(
        source_blockchain_id=source_blockchain.id,
        destination_blockchain_id=destination_blockchain.id,
        sender_address=_TRANSFER_SENDER_ADDRESSES[0],
        recipient_address=_TRANSFER_RECIPIENT_ADDRESSES[0],
        source_token_contract=source_token_contract,
        destination_token_contract=destination_token_contract,
        amount=_TRANSFER_AMOUNTS[0],
        validator_nonce=_TRANSFER_VALIDATOR_NONCES[0],
        source_hub_contract=source_hub_contract,
        destination_hub_contract=destination_hub_contract,
        destination_forwarder_contract=destination_forwarder_contract,
        task_id=task_id, source_transfer_id=_TRANSFER_SOURCE_TRANSFER_IDS[0],
        destination_transfer_id=destination_transfer_id,
        source_transaction_id=_TRANSFER_SOURCE_TRANSACTION_IDS[0],
        destination_transaction_id=destination_transaction_id,
        source_block_number=_TRANSFER_SOURCE_BLOCK_NUMBERS[0],
        destination_block_number=destination_block_number, nonce=nonce,
        status_id=status_id)


@pytest.fixture(params=[True, False])
def other_transfer(request, other_source_blockchain,
                   other_destination_blockchain, other_source_token_contract,
                   other_destination_token_contract, other_source_hub_contract,
                   other_destination_hub_contract,
                   other_destination_forwarder_contract):
    destination_hub_contract = (None if request.param else
                                other_destination_hub_contract)
    destination_forwarder_contract = (None if request.param else
                                      other_destination_forwarder_contract)
    task_id = None if request.param else _TRANSFER_TASK_IDS[1]
    destination_transfer_id = (None if request.param else
                               _TRANSFER_DESTINATION_TRANSFER_IDS[1])
    destination_transaction_id = (None if request.param else
                                  _TRANSFER_DESTINATION_TRANSACTION_IDS[1])
    destination_block_number = (None if request.param else
                                _TRANSFER_DESTINATION_BLOCK_NUMBERS[1])
    nonce = None if request.param else _TRANSFER_NONCES[1]
    status_id = (TransferStatus.SOURCE_TRANSACTION_REVERTED.value
                 if request.param else
                 TransferStatus.DESTINATION_TRANSACTION_SUBMITTED.value)
    return Transfer(
        source_blockchain_id=other_source_blockchain.id,
        destination_blockchain_id=other_destination_blockchain.id,
        sender_address=_TRANSFER_SENDER_ADDRESSES[1],
        recipient_address=_TRANSFER_RECIPIENT_ADDRESSES[1],
        source_token_contract=other_source_token_contract,
        destination_token_contract=other_destination_token_contract,
        amount=_TRANSFER_AMOUNTS[1],
        validator_nonce=_TRANSFER_VALIDATOR_NONCES[1],
        source_hub_contract=other_source_hub_contract,
        destination_hub_contract=destination_hub_contract,
        destination_forwarder_contract=destination_forwarder_contract,
        task_id=task_id, source_transfer_id=_TRANSFER_SOURCE_TRANSFER_IDS[1],
        destination_transfer_id=destination_transfer_id,
        source_transaction_id=_TRANSFER_SOURCE_TRANSACTION_IDS[1],
        destination_transaction_id=destination_transaction_id,
        source_block_number=_TRANSFER_SOURCE_BLOCK_NUMBERS[1],
        destination_block_number=destination_block_number, nonce=nonce,
        status_id=status_id)


def _create_database_records(database_session):
    for blockchain in Blockchain:
        database_session.execute(
            sqlalchemy.insert(Blockchain_).values(id=blockchain.value,
                                                  name=blockchain.name))
    for transfer_status in TransferStatus:
        database_session.execute(
            sqlalchemy.insert(TransferStatus_).values(
                id=transfer_status.value, name=transfer_status.name))
    database_session.commit()


def _delete_database_records(database_session):
    database_session.execute(sqlalchemy.delete(ValidatorNodeSignature))
    database_session.execute(sqlalchemy.delete(ValidatorNode))
    database_session.execute(sqlalchemy.delete(Transfer))
    database_session.execute(sqlalchemy.delete(TransferStatus_))
    database_session.execute(sqlalchemy.delete(TokenContract))
    database_session.execute(sqlalchemy.delete(ForwarderContract))
    database_session.execute(sqlalchemy.delete(HubContract))
    database_session.execute(sqlalchemy.delete(Blockchain_))
    database_session.commit()
