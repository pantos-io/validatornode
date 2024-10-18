import sys

import pytest
import sqlalchemy
import sqlalchemy.exc
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.models import Base
from tests.database.utilities import modify_model_instance

_UNKNOWN_BLOCKCHAIN_ID = max(Blockchain).value + 1

_UNKNOWN_FORWARDER_CONTRACT_ID = sys.maxsize

_UNKNOWN_TRANSFER_ID = sys.maxsize - 1

_UNKNOWN_TRANSFER_STATUS_ID = max(TransferStatus).value + 1

_UNKNOWN_VALIDATOR_NODE_ID = sys.maxsize - 2


def test_blockchain_correct(database_session, blockchain):
    database_session.add(blockchain)
    database_session.commit()


def test_blockchain_name_not_null_constraint(database_session, blockchain):
    _test_not_null_constraint(database_session, blockchain, 'name')


def test_blockchain_last_block_number_not_null_constraint(
        database_session, blockchain):
    _test_not_null_constraint(database_session, blockchain,
                              'last_block_number')


def test_hub_contract_correct(initialized_database_session, hub_contract):
    initialized_database_session.add(hub_contract)
    initialized_database_session.commit()


def test_hub_contract_blockchain_id_foreign_key_constraint(
        initialized_database_session, hub_contract):
    _test_foreign_key_constraint(initialized_database_session, hub_contract,
                                 blockchain_id=_UNKNOWN_BLOCKCHAIN_ID)


def test_hub_contract_blockchain_id_not_null_constraint(
        initialized_database_session, hub_contract):
    _test_not_null_constraint(initialized_database_session, hub_contract,
                              'blockchain_id')


def test_hub_contract_address_not_null_constraint(initialized_database_session,
                                                  hub_contract):
    _test_not_null_constraint(initialized_database_session, hub_contract,
                              'address')


def test_hub_contract_blockchain_id_address_unique_constraint(
        initialized_database_session, hub_contract):
    _test_unique_constraint(initialized_database_session, hub_contract,
                            hub_contract, 'blockchain_id', 'address')


def test_forwarder_contract_correct(initialized_database_session,
                                    forwarder_contract):
    initialized_database_session.add(forwarder_contract)
    initialized_database_session.commit()


def test_forwarder_contract_blockchain_id_foreign_key_constraint(
        initialized_database_session, forwarder_contract):
    _test_foreign_key_constraint(initialized_database_session,
                                 forwarder_contract,
                                 blockchain_id=_UNKNOWN_BLOCKCHAIN_ID)


def test_forwarder_contract_blockchain_id_not_null_constraint(
        initialized_database_session, forwarder_contract):
    _test_not_null_constraint(initialized_database_session, forwarder_contract,
                              'blockchain_id')


def test_forwarder_contract_address_not_null_constraint(
        initialized_database_session, forwarder_contract):
    _test_not_null_constraint(initialized_database_session, forwarder_contract,
                              'address')


def test_forwarder_contract_blockchain_id_address_unique_constraint(
        initialized_database_session, forwarder_contract):
    _test_unique_constraint(initialized_database_session, forwarder_contract,
                            forwarder_contract, 'blockchain_id', 'address')


def test_token_contract_correct(initialized_database_session, token_contract):
    initialized_database_session.add(token_contract)
    initialized_database_session.commit()


def test_token_contract_blockchain_id_foreign_key_constraint(
        initialized_database_session, token_contract):
    _test_foreign_key_constraint(initialized_database_session, token_contract,
                                 blockchain_id=_UNKNOWN_BLOCKCHAIN_ID)


def test_token_contract_blockchain_id_not_null_constraint(
        initialized_database_session, token_contract):
    _test_not_null_constraint(initialized_database_session, token_contract,
                              'blockchain_id')


def test_token_contract_address_not_null_constraint(
        initialized_database_session, token_contract):
    _test_not_null_constraint(initialized_database_session, token_contract,
                              'address')


def test_token_contract_blockchain_id_address_unique_constraint(
        initialized_database_session, token_contract):
    _test_unique_constraint(initialized_database_session, token_contract,
                            token_contract, 'blockchain_id', 'address')


def test_validator_node_correct(initialized_database_session, validator_node):
    initialized_database_session.add(validator_node)
    initialized_database_session.commit()


def test_validator_node_forwarder_contract_foreign_key_constraint(
        initialized_database_session, validator_node):
    _test_foreign_key_constraint(
        initialized_database_session, validator_node, forwarder_contract=None,
        forwarder_contract_id=_UNKNOWN_FORWARDER_CONTRACT_ID)


def test_validator_node_forwarder_contract_not_null_constraint(
        initialized_database_session, validator_node):
    _test_not_null_constraint(initialized_database_session, validator_node,
                              'forwarder_contract')


def test_validator_node_address_not_null_constraint(
        initialized_database_session, validator_node):
    _test_not_null_constraint(initialized_database_session, validator_node,
                              'address')


def test_validator_node_signature_correct(initialized_database_session,
                                          validator_node_signature):
    initialized_database_session.add(validator_node_signature)
    initialized_database_session.commit()


def test_validator_node_signature_transfer_foreign_key_constraint(
        initialized_database_session, validator_node_signature):
    _test_foreign_key_constraint(initialized_database_session,
                                 validator_node_signature, transfer=None,
                                 transfer_id=_UNKNOWN_TRANSFER_ID)


@pytest.mark.filterwarnings('ignore')
def test_validator_node_signature_transfer_not_null_constraint(
        initialized_database_session, validator_node_signature):
    _test_not_null_constraint(initialized_database_session,
                              validator_node_signature, 'transfer')


def test_validator_node_signature_validator_node_foreign_key_constraint(
        initialized_database_session, validator_node_signature):
    _test_foreign_key_constraint(initialized_database_session,
                                 validator_node_signature, validator_node=None,
                                 validator_node_id=_UNKNOWN_VALIDATOR_NODE_ID)


@pytest.mark.filterwarnings('ignore')
def test_validator_node_signature_validator_node_not_null_constraint(
        initialized_database_session, validator_node_signature):
    _test_not_null_constraint(initialized_database_session,
                              validator_node_signature, 'validator_node')


def test_validator_node_signature_signature_unique_constraint(
        initialized_database_session, validator_node_signature):
    _test_unique_constraint(initialized_database_session,
                            validator_node_signature, validator_node_signature,
                            'signature')


def test_validator_node_signature_signature_not_null_constraint(
        initialized_database_session, validator_node_signature):
    _test_not_null_constraint(initialized_database_session,
                              validator_node_signature, 'signature')


def test_transfer_status_correct(database_session, transfer_status):
    database_session.add(transfer_status)
    database_session.commit()


def test_transfer_status_name_not_null_constraint(database_session,
                                                  transfer_status):
    _test_not_null_constraint(database_session, transfer_status, 'name')


def test_transfer_correct(initialized_database_session, transfer):
    initialized_database_session.add(transfer)
    initialized_database_session.commit()


def test_transfer_source_blockchain_id_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 source_blockchain_id=_UNKNOWN_BLOCKCHAIN_ID)


def test_transfer_source_blockchain_id_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_blockchain_id')


def test_transfer_destination_blockchain_id_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(
        initialized_database_session, transfer,
        destination_blockchain_id=_UNKNOWN_BLOCKCHAIN_ID)


def test_transfer_destination_blockchain_id_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'destination_blockchain_id')


def test_transfer_sender_address_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'sender_address')


def test_transfer_recipient_address_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'recipient_address')


def test_transfer_source_token_contract_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 source_token_contract=None,
                                 source_token_contract_id=1000)


def test_transfer_source_token_contract_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_token_contract')


def test_transfer_destination_token_contract_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 destination_token_contract=None,
                                 destination_token_contract_id=1000)


def test_transfer_destination_token_contract_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'destination_token_contract')


def test_transfer_amount_not_null_constraint(initialized_database_session,
                                             transfer):
    _test_not_null_constraint(initialized_database_session, transfer, 'amount')


def test_transfer_source_hub_contract_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 source_hub_contract=None,
                                 source_hub_contract_id=1000)


def test_transfer_source_hub_contract_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_hub_contract')


def test_transfer_destination_hub_contract_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 destination_hub_contract=None,
                                 destination_hub_contract_id=1000)


def test_transfer_destination_forwarder_contract_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 destination_forwarder_contract=None,
                                 destination_forwarder_contract_id=1000)


def test_transfer_task_id_unique_constraint(initialized_database_session,
                                            transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'task_id')


def test_transfer_source_transfer_id_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_transfer_id')


def test_transfer_source_transaction_id_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_transaction_id')


def test_transfer_source_block_number_not_null_constraint(
        initialized_database_session, transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'source_block_number')


def test_transfer_status_id_foreign_key_constraint(
        initialized_database_session, transfer):
    _test_foreign_key_constraint(initialized_database_session, transfer,
                                 status_id=_UNKNOWN_TRANSFER_STATUS_ID)


def test_transfer_status_id_not_null_constraint(initialized_database_session,
                                                transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'status_id')


def test_transfer_created_not_null_constraint(initialized_database_session,
                                              transfer):
    _test_not_null_constraint(initialized_database_session, transfer,
                              'created')


def test_transfer_destination_forwarder_validator_nonce_unique_constraint(
        initialized_database_session, transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'destination_forwarder_contract',
                            'validator_nonce')


def test_transfer_source_blockchain_transfer_id_unique_constraint(
        initialized_database_session, transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'source_blockchain_id',
                            'source_transfer_id')


def test_transfer_destination_blockchain_transfer_id_unique_constraint(
        initialized_database_session, transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'destination_blockchain_id',
                            'destination_transfer_id')


def test_transfer_source_blockchain_transaction_id_unique_constraint(
        initialized_database_session, transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'source_blockchain_id',
                            'source_transaction_id')


def test_transfer_destination_blockchain_transaction_id_unique_constraint(
        initialized_database_session, transfer, other_transfer):
    _test_unique_constraint(initialized_database_session, transfer,
                            other_transfer, 'destination_blockchain_id',
                            'destination_transaction_id')


def _test_constraint(database_session, model_instances, *message_parts):
    for model_instance in model_instances:
        database_session.add(model_instance)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as exception_info:
        database_session.commit()
    assert exception_info.value.orig is not None
    sqlite_message = exception_info.value.orig.args[0]
    for message_part in message_parts:
        assert message_part in sqlite_message


def _test_foreign_key_constraint(database_session, model_instance,
                                 **modified_attributes):
    model_instance = modify_model_instance(model_instance,
                                           **modified_attributes)
    _test_constraint(database_session, [model_instance],
                     'FOREIGN KEY constraint failed')


def _test_not_null_constraint(database_session, model_instance,
                              attribute_name):
    if isinstance(getattr(model_instance, attribute_name), Base):
        setattr(model_instance, attribute_name, None)
    else:
        setattr(model_instance, attribute_name, sqlalchemy.null())
    _test_constraint(database_session, [model_instance],
                     'NOT NULL constraint failed',
                     f'{model_instance.__tablename__}.{attribute_name}')


def _test_unique_constraint(database_session, model_instance,
                            other_model_instance, *attribute_names):
    assert model_instance.__tablename__ == other_model_instance.__tablename__
    modified_attributes = {}
    message_parts = ['UNIQUE constraint failed']
    for attribute_name in attribute_names:
        attribute_value = getattr(model_instance, attribute_name)
        if attribute_value is None:
            pytest.skip('UNIQUE constraint does not fail for NULL values')
        modified_attributes[attribute_name] = attribute_value
        message_parts.append(
            f'{model_instance.__tablename__}.{attribute_name}')
    other_model_instance = modify_model_instance(other_model_instance,
                                                 **modified_attributes)
    _test_constraint(database_session, [model_instance, other_model_instance],
                     *message_parts)
