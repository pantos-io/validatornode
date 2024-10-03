"""Module for creating, reading, updating, and deleting database
records.

"""
import dataclasses
import datetime
import logging
import typing
import uuid

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm
from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import BlockchainAddress

from pantos.validatornode.database import get_session
from pantos.validatornode.database import get_session_maker
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.exceptions import DatabaseError
from pantos.validatornode.database.exceptions import \
    ValidatorNonceNotUniqueError
from pantos.validatornode.database.models import \
    UNIQUE_VALIDATOR_NONCE_CONSTRAINT
from pantos.validatornode.database.models import Base
from pantos.validatornode.database.models import Blockchain as Blockchain_
from pantos.validatornode.database.models import ForwarderContract
from pantos.validatornode.database.models import HubContract
from pantos.validatornode.database.models import TokenContract
from pantos.validatornode.database.models import Transfer
from pantos.validatornode.database.models import ValidatorNode
from pantos.validatornode.database.models import ValidatorNodeSignature

_logger = logging.getLogger(__name__)

B = typing.TypeVar('B', bound=Base)


@dataclasses.dataclass
class TransferCreationRequest:
    """Request data for creating a new transfer record.

    Attributes
    ----------
    source_blockchain : Blockchain
        The transfer's source blockchain.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    sender_address : BlockchainAddress
        The address of the sender on the source blockchain.
    recipient_address : BlockchainAddress
        The address of the recipient on the destination blockchain.
    source_token_address : BlockchainAddress
        The contract address of the transferred PANDAS token on the
        source blockchain.
    destination_token_address : BlockchainAddress
        The contract address of the transferred PANDAS token on the
        destination blockchain.
    amount : int
        The transferred PANDAS token amount.
    validator_nonce : int
        The validator nonce initially assigned to the transfer.
    source_hub_address : BlockchainAddress
        The address of the Pantos Hub contract on the source blockchain.
    source_transfer_id : int
        The Pantos transfer ID on the source blockchain.
    source_transaction_id : str
        The transfer's transaction ID/hash on the source blockchain.
    source_block_number : int
        The number of the transfer transaction's block on the source
        blockchain.

    """
    source_blockchain: Blockchain
    destination_blockchain: Blockchain
    sender_address: BlockchainAddress
    recipient_address: BlockchainAddress
    source_token_address: BlockchainAddress
    destination_token_address: BlockchainAddress
    amount: int
    validator_nonce: int
    source_hub_address: BlockchainAddress
    source_transfer_id: int
    source_transaction_id: str
    source_block_number: int


def create_transfer(request: TransferCreationRequest) -> int:
    """Create a new transfer record.

    Parameters
    ----------
    request : TransferCreationRequest
        The request data.

    Returns
    -------
    int
        The unique internal ID of the created transfer record.

    Raises
    ------
    ValidatorNonceNotUniqueError
        If the validator nonce is not unique on the destination
        blockchain.

    """
    transfer_status = TransferStatus.SOURCE_TRANSACTION_DETECTED
    try:
        with get_session_maker().begin() as session:
            source_token_contract_id = _read_token_contract_id(
                session, request.source_blockchain,
                request.source_token_address)
            if source_token_contract_id is None:
                source_token_contract_id = _create_token_contract(
                    session, request.source_blockchain,
                    request.source_token_address)
            destination_token_contract_id = _read_token_contract_id(
                session, request.destination_blockchain,
                request.destination_token_address)
            if destination_token_contract_id is None:
                destination_token_contract_id = _create_token_contract(
                    session, request.destination_blockchain,
                    request.destination_token_address)
            source_hub_contract_id = _read_hub_contract_id(
                session, request.source_blockchain, request.source_hub_address)
            if source_hub_contract_id is None:
                source_hub_contract_id = _create_hub_contract(
                    session, request.source_blockchain,
                    request.source_hub_address)
            statement = sqlalchemy.insert(Transfer).values(
                source_blockchain_id=request.source_blockchain.value,
                destination_blockchain_id=request.destination_blockchain.value,
                sender_address=request.sender_address,
                recipient_address=request.recipient_address,
                source_token_contract_id=source_token_contract_id,
                destination_token_contract_id=destination_token_contract_id,
                amount=request.amount, validator_nonce=request.validator_nonce,
                source_hub_contract_id=source_hub_contract_id,
                source_transfer_id=request.source_transfer_id,
                source_transaction_id=request.source_transaction_id,
                source_block_number=request.source_block_number,
                status_id=transfer_status.value).returning(Transfer.id)
            return session.execute(statement).scalar_one()
    except sqlalchemy.exc.IntegrityError as error:
        if UNIQUE_VALIDATOR_NONCE_CONSTRAINT in str(error):
            raise ValidatorNonceNotUniqueError(request.destination_blockchain,
                                               request.validator_nonce)
        raise


def create_validator_node_signature(
        internal_transfer_id: int, destination_blockchain: Blockchain,
        destination_forwarder_address: BlockchainAddress,
        validator_node_address: BlockchainAddress, signature: str) -> None:
    """Create a new validator node signature record.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the signed transfer.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    destination_forwarder_address : BlockchainAddress
        The address of the Forwarder contract on the destination
        blockchain.
    validator_node_address : BlockchainAddress
        The address of the signing validator node on the destination
        blockchain.
    signature : str
        The validator node's signature.

    """
    with get_session_maker().begin() as session:
        destination_forwarder_contract_id = _read_forwarder_contract_id(
            session, destination_blockchain, destination_forwarder_address)
        if destination_forwarder_contract_id is None:
            destination_forwarder_contract_id = _create_forwarder_contract(
                session, destination_blockchain, destination_forwarder_address)
        validator_node_id = _read_validator_node_id(
            session, destination_forwarder_contract_id, validator_node_address)
        if validator_node_id is None:
            validator_node_id = _create_validator_node(
                session, destination_forwarder_contract_id,
                validator_node_address)
        statement = sqlalchemy.insert(ValidatorNodeSignature).values(
            transfer_id=internal_transfer_id,
            validator_node_id=validator_node_id, signature=signature)
        session.execute(statement)


def read_blockchain_last_block_number(blockchain: Blockchain) -> int:
    """Read the number of the last block monitored for new Pantos
    TransferFromSucceeded events on the given blockchain.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain to read the number of the last monitored block
        for.

    Returns
    -------
    int
        The non-negative number of the last monitored block, or -1 if no
        block has been monitored for the given blockchain.

    """
    with get_session() as session:
        blockchain_ = session.get(Blockchain_, blockchain.value)
        assert blockchain_ is not None
        last_block_number = blockchain_.last_block_number
        return int(last_block_number)


def read_transfer_id(source_blockchain: Blockchain,
                     source_transaction_id: str) -> typing.Optional[int]:
    """Read the unique internal ID of the transfer with a given source
    blockchain and source transaction ID/hash.

    Parameters
    ----------
    source_blockchain : Blockchain
        The transfer's source blockchain.
    source_transaction_id : str
        The transfer's transaction ID/hash on the source blockchain.

    Returns
    -------
    int or None
        The unique internal ID of the transfer, or None if there is no
        transfer with the given source blockchain and source transaction
        ID/hash.

    """
    statement = sqlalchemy.select(Transfer.id).filter_by(
        source_blockchain_id=source_blockchain.value,
        source_transaction_id=source_transaction_id)
    with get_session() as session:
        return session.execute(statement).scalar_one_or_none()


def read_transfer_nonce(internal_transfer_id: int) -> int | None:
    """Read the nonce for a transfer transaction submitted to the
    destination blockchain.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.

    Returns
    -------
    int or None
        The nonce for the transfer transaction on the destination
        blockchain, or None if no blockchain nonce has been assigned to
        the transfer.

    """
    statement = sqlalchemy.select(
        Transfer.nonce).filter(Transfer.id == internal_transfer_id)
    with get_session() as session:
        return session.execute(statement).scalar_one_or_none()


@dataclasses.dataclass
class TransferToDataResponse:
    """Response data from reading the transferTo data for a cross-chain
    transfer.

    Attributes
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    source_transfer_id : int
        The Pantos transfer ID on the source blockchain.
    sender_address : BlockchainAddress
        The address of the sender on the source blockchain.
    recipient_address : BlockchainAddress
        The address of the recipient on the destination blockchain.
    source_token_address : BlockchainAddress
        The contract address of the transferred PANDAS token on the
        source blockchain.
    destination_token_address : BlockchainAddress
        The contract address of the transferred PANDAS token on the
        destination blockchain.
    amount : int
        The transferred PANDAS token amount.
    validator_nonce : int
        The validator nonce assigned to the transfer.

    """
    internal_transfer_id: int
    destination_blockchain: Blockchain
    source_transfer_id: int
    sender_address: BlockchainAddress
    recipient_address: BlockchainAddress
    source_token_address: BlockchainAddress
    destination_token_address: BlockchainAddress
    amount: int
    validator_nonce: int


def read_transfer_to_data(
        source_blockchain: Blockchain,
        source_transaction_id: str) -> typing.Optional[TransferToDataResponse]:
    """Read the transferTo data for a cross-chain transfer.

    Parameters
    ----------
    source_blockchain : Blockchain
        The transfer's source blockchain.
    source_transaction_id : str
        The transfer's transaction ID/hash on the source blockchain.

    Returns
    -------
    TransferToDataResponse or None
        The response data, or None if there is no transfer with the
        given source blockchain and source transaction ID/hash.

    """
    source_token_contract_alias = sqlalchemy.orm.aliased(
        TokenContract, name='source_token_contract')
    destination_token_contract_alias = sqlalchemy.orm.aliased(
        TokenContract, name='destination_token_contract')
    statement = sqlalchemy.select(
        Transfer.id, Transfer.destination_blockchain_id,
        Transfer.source_transfer_id, Transfer.sender_address,
        Transfer.recipient_address, source_token_contract_alias.address,
        destination_token_contract_alias.address, Transfer.amount,
        Transfer.validator_nonce
    ).join(source_token_contract_alias, Transfer.source_token_contract).join(
        destination_token_contract_alias,
        Transfer.destination_token_contract).where(
            Transfer.source_blockchain_id == source_blockchain.value).where(
                Transfer.source_transaction_id == source_transaction_id)
    with get_session() as session:
        result = session.execute(statement).one_or_none()
    if result is None:
        return None
    internal_transfer_id = result[0]
    destination_blockchain = Blockchain(result[1])
    source_transfer_id = result[2].as_integer_ratio()[0]  # type: ignore
    sender_address = BlockchainAddress(result[3])
    recipient_address = BlockchainAddress(result[4])
    source_token_address = BlockchainAddress(result[5])
    destination_token_address = BlockchainAddress(result[6])
    amount = result[7].as_integer_ratio()[0]  # type: ignore
    validator_nonce = result[8].as_integer_ratio()[0]  # type: ignore
    return TransferToDataResponse(
        internal_transfer_id=internal_transfer_id,  # type: ignore
        destination_blockchain=destination_blockchain,
        source_transfer_id=source_transfer_id,
        sender_address=sender_address,
        recipient_address=recipient_address,
        source_token_address=source_token_address,
        destination_token_address=destination_token_address,
        amount=amount,
        validator_nonce=validator_nonce)


def read_validator_node_signature(
        internal_transfer_id: int, destination_blockchain: Blockchain,
        destination_forwarder_address: BlockchainAddress,
        validator_node_address: BlockchainAddress) -> typing.Optional[str]:
    """Read the signature of a validator node for a cross-chain
    transfer.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the signed transfer.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    destination_forwarder_address : BlockchainAddress
        The address of the Forwarder contract on the destination
        blockchain.
    validator_node_address : BlockchainAddress
        The address of the signing validator node on the destination
        blockchain.

    Returns
    -------
    str or None
        The validator node's signature for the transfer, or None if
        there is no signature matching the given criteria.

    """
    statement = sqlalchemy.select(ValidatorNodeSignature.signature).join_from(
        ValidatorNodeSignature,
        ValidatorNode).join_from(ValidatorNode, ForwarderContract).where(
            ValidatorNodeSignature.transfer_id == internal_transfer_id).where(
                ForwarderContract.blockchain_id == destination_blockchain.value
            ).where(ForwarderContract.address == destination_forwarder_address
                    ).where(ValidatorNode.address == validator_node_address)
    with get_session() as session:
        return session.execute(statement).scalar_one_or_none()


def read_validator_node_signatures(
        internal_transfer_id: int) -> dict[BlockchainAddress, str]:
    """Read the validator node signatures for a cross-chain transfer.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the signed transfer.

    Returns
    -------
    dict
        The validator node addresses as keys and their corresponding
        signatures as values.

    """
    statement = sqlalchemy.select(
        ValidatorNode.address, ValidatorNodeSignature.signature).join_from(
            ValidatorNodeSignature, ValidatorNode).where(
                ValidatorNodeSignature.transfer_id == internal_transfer_id)
    with get_session() as session:
        results = session.execute(statement).all()
    return {
        BlockchainAddress(result[0]): result[1]  # type: ignore
        for result in results
    }


def read_validator_nonce_by_internal_transfer_id(
        internal_transfer_id: int) -> int | None:
    """Read the validator nonce assigned to a transfer with a given ID.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.

    Returns
    -------
    int or None
        The validator nonce assigned to the transfer, or None if there
        is no transfer with the given ID.

    """
    statement = sqlalchemy.select(
        Transfer.validator_nonce).where(Transfer.id == internal_transfer_id)
    with get_session() as session:
        validator_nonce = session.execute(statement).scalar_one_or_none()
    if validator_nonce is None:
        return None
    return validator_nonce.as_integer_ratio()[0]


def read_validator_nonce_by_source_transaction_id(
        source_blockchain: Blockchain,
        source_transaction_id: str) -> int | None:
    """Read the validator nonce assigned to a transfer with a given
    source blockchain and source transaction ID/hash.

    Parameters
    ----------
    source_blockchain : Blockchain
        The transfer's source blockchain.
    source_transaction_id : str
        The transfer's transaction ID/hash on the source blockchain.

    Returns
    -------
    int or None
        The validator nonce assigned to the transfer, or None if there
        is no transfer with the given source blockchain and source
        transaction ID/hash.

    """
    statement = sqlalchemy.select(Transfer.validator_nonce).filter_by(
        source_blockchain_id=source_blockchain.value,
        source_transaction_id=source_transaction_id)
    with get_session() as session:
        validator_nonce = session.execute(statement).scalar_one_or_none()
    if validator_nonce is None:
        return None
    return validator_nonce.as_integer_ratio()[0]


def update_blockchain_last_block_number(blockchain: Blockchain,
                                        last_block_number: int) -> None:
    """Update the number of the last block monitored for new Pantos
    TransferFromSucceeded events on the given blockchain.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain to update the number of the last monitored block
        for.
    last_block_number : int
        The number of the last monitored block on the blockchain.

    """
    with get_session_maker().begin() as session:
        blockchain_ = session.get(Blockchain_, blockchain.value)
        assert blockchain_ is not None
        if blockchain_.last_block_number > last_block_number:
            raise DatabaseError(
                f'stored last block number {blockchain_.last_block_number} '
                f'of {blockchain.name} is greater than given block number '
                f'{last_block_number}')
        elif blockchain_.last_block_number != last_block_number:
            blockchain_.last_block_number = typing.cast(
                sqlalchemy.Column, last_block_number)


def update_reversal_transfer(
        internal_transfer_id: int, destination_blockchain: Blockchain,
        recipient_address: BlockchainAddress,
        destination_token_address: BlockchainAddress) -> None:
    """Update a reversal transfer's destination blockchain attributes.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    destination_blockchain : Blockchain
        The transfer's destination blockchain.
    recipient_address : BlockchainAddress
        The transfer's recipient address.
    destination_token_address : BlockchainAddress
        The address of the transferred token on the destination
        blockchain.

    """
    with get_session_maker().begin() as session:
        destination_token_contract_id = _read_token_contract_id(
            session, destination_blockchain, destination_token_address)
        if destination_token_contract_id is None:
            destination_token_contract_id = _create_token_contract(
                session, destination_blockchain, destination_token_address)
        statement = sqlalchemy.update(Transfer).where(
            Transfer.id == internal_transfer_id).values(
                destination_blockchain_id=destination_blockchain.value,
                recipient_address=recipient_address,
                destination_token_contract_id=destination_token_contract_id,
                updated=datetime.datetime.now(datetime.timezone.utc))
        session.execute(statement)


def update_transfer_confirmed_destination_transaction(
        internal_transfer_id: int, destination_transfer_id: int,
        destination_transaction_id: str,
        destination_block_number: int) -> None:
    """Update a transfer's attributes for its confirmed destination
    blockchain transaction.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    destination_transfer_id : int
        The Pantos transfer ID on the destination blockchain.
    destination_transaction_id : str
        The transaction ID/hash on the destination blockchain.
    destination_block_number : int
        The block number on the destination blockchain.

    """
    statement = sqlalchemy.update(Transfer).where(
        Transfer.id == internal_transfer_id).values(
            destination_transfer_id=destination_transfer_id,
            destination_transaction_id=destination_transaction_id,
            destination_block_number=destination_block_number,
            updated=datetime.datetime.now(datetime.timezone.utc))
    with get_session_maker().begin() as session:
        session.execute(statement)


def update_transfer_submitted_destination_transaction(
        internal_transfer_id: int, destination_hub_address: BlockchainAddress,
        destination_forwarder_address: BlockchainAddress) -> None:
    """Update a transfer's attributes for its submitted destination
    blockchain transaction.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    destination_hub_address : BlockchainAddress
        The address of the hub contract on the destination blockchain.
    destination_forwarder_address : BlockchainAddress
        The address of the Forwarder contract on the destination
        blockchain.

    """
    with get_session_maker().begin() as session:
        select_statement = sqlalchemy.select(
            Transfer.destination_blockchain_id).where(
                Transfer.id == internal_transfer_id)
        destination_blockchain_id = session.execute(
            select_statement).scalar_one()
        destination_blockchain = Blockchain(destination_blockchain_id)
        destination_hub_contract_id = _read_hub_contract_id(
            session, destination_blockchain, destination_hub_address)
        if destination_hub_contract_id is None:
            destination_hub_contract_id = _create_hub_contract(
                session, destination_blockchain, destination_hub_address)
        destination_forwarder_contract_id = _read_forwarder_contract_id(
            session, destination_blockchain, destination_forwarder_address)
        if destination_forwarder_contract_id is None:
            destination_forwarder_contract_id = _create_forwarder_contract(
                session, destination_blockchain, destination_forwarder_address)
        update_statement = sqlalchemy.update(Transfer).where(
            Transfer.id == internal_transfer_id).values(
                destination_hub_contract_id=destination_hub_contract_id,
                destination_forwarder_contract_id=  # noqa: E251
                destination_forwarder_contract_id,
                updated=datetime.datetime.now(datetime.timezone.utc))
        session.execute(update_statement)


def update_transfer_nonce(internal_transfer_id: int,
                          destination_blockchain: Blockchain,
                          latest_blockchain_nonce: int) -> None:
    """Update the nonce for a transfer transaction submitted to the
    destination blockchain.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    destination_blockchain : Blockchain
        The blockchain to which the transfer is submitted.
    latest_blockchain_nonce : int
        The latest nonce on the destination blockchain.

    """
    failed_transactions_expression = sqlalchemy.and_(
        Transfer.destination_blockchain_id == destination_blockchain.value,
        Transfer.nonce.is_not(None),  # noqa: E711
        sqlalchemy.or_(
            Transfer.status_id ==
            TransferStatus.DESTINATION_TRANSACTION_FAILED.value,
            Transfer.status_id ==
            TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED.value))
    count_failed_nonces_subquery = sqlalchemy.select(
        sqlalchemy.func.count()).filter(
            failed_transactions_expression).scalar_subquery()
    minimum_failed_nonce_cte = sqlalchemy.select(
        sqlalchemy.func.min(Transfer.nonce).label('min')).filter(
            failed_transactions_expression).cte('minimum_failed_nonce_cte')
    maximum_transfer_nonce_subquery = sqlalchemy.select(
        sqlalchemy.func.max(Transfer.nonce)).filter(
            Transfer.destination_blockchain_id ==
            destination_blockchain.value).scalar_subquery()
    statement = sqlalchemy.update(Transfer).where(
        sqlalchemy.or_(
            Transfer.id == internal_transfer_id,
            sqlalchemy.and_(
                Transfer.destination_blockchain_id ==
                destination_blockchain.value,
                Transfer.nonce == minimum_failed_nonce_cte.c.min))
    ).values({
        Transfer.nonce: sqlalchemy.case(
            (count_failed_nonces_subquery == 0,
             sqlalchemy.case(
                 (maximum_transfer_nonce_subquery >= latest_blockchain_nonce,
                  maximum_transfer_nonce_subquery + 1),
                 else_=latest_blockchain_nonce)),
            (Transfer.id
             == internal_transfer_id, minimum_failed_nonce_cte.c.min),
            else_=sqlalchemy.null()),
        Transfer.status_id: sqlalchemy.case(
            (Transfer.id == internal_transfer_id,
             sqlalchemy.case(
                 (Transfer.status_id
                  == TransferStatus.SOURCE_TRANSACTION_DETECTED.value,
                  TransferStatus.
                  SOURCE_TRANSACTION_DETECTED_NEW_NONCE_ASSIGNED.value),
                 (Transfer.status_id
                  == TransferStatus.DESTINATION_TRANSACTION_FAILED.value,
                  TransferStatus.
                  DESTINATION_TRANSACTION_FAILED_NEW_NONCE_ASSIGNED.value),
                 else_=TransferStatus.
                 SOURCE_REVERSAL_TRANSACTION_FAILED_NEW_NONCE_ASSIGNED.value)),
            else_=sqlalchemy.case(
                (Transfer.status_id
                 == TransferStatus.DESTINATION_TRANSACTION_FAILED.value,
                 TransferStatus.DESTINATION_TRANSACTION_FAILED.value),
                else_=TransferStatus.SOURCE_REVERSAL_TRANSACTION_FAILED.value))
    })
    with get_session_maker().begin() as session:
        # Execute the transaction
        session.execute(
            statement,
            execution_options=sqlalchemy.util._collections.immutabledict(
                {'synchronize_session': False}))


def reset_transfer_nonce(internal_transfer_id: int) -> None:
    """Update a transfer by setting its destination blockchain
    transaction nonce to NULL.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.

    """
    statement = sqlalchemy.update(Transfer).where(
        Transfer.id == internal_transfer_id).values(nonce=sqlalchemy.null())
    with get_session_maker().begin() as session:
        session.execute(statement)


def update_transfer_source_transaction(internal_transfer_id: int,
                                       source_transfer_id: int,
                                       source_block_number: int) -> None:
    """Update a transfer's attributes related to its source blockchain
    transaction.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    source_transfer_id : int
        The Pantos transfer ID on the source blockchain.
    source_block_number : int
        The number of the transfer transaction's block on the source
        blockchain.

    """
    with get_session_maker().begin() as session:
        transfer = session.get(Transfer, internal_transfer_id)
        assert transfer is not None
        transfer.source_transfer_id = typing.cast(sqlalchemy.Column,
                                                  source_transfer_id)
        transfer.source_block_number = typing.cast(sqlalchemy.Column,
                                                   source_block_number)
        transfer.updated = typing.cast(
            sqlalchemy.Column, datetime.datetime.now(datetime.timezone.utc))


def update_transfer_status(internal_transfer_id: int,
                           status: TransferStatus) -> None:
    """Update the status of a transfer.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    status : TransferStatus
        The new status.

    """
    with get_session_maker().begin() as session:
        transfer = session.get(Transfer, internal_transfer_id)
        assert transfer is not None
        transfer.status_id = typing.cast(sqlalchemy.Column, status.value)
        transfer.updated = typing.cast(
            sqlalchemy.Column, datetime.datetime.now(datetime.timezone.utc))


def update_transfer_task_id(internal_transfer_id: int,
                            task_id: uuid.UUID) -> None:
    """Update a transfer by adding the related Celery task ID.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    task_id : uuid.UUID
        The unique ID of the Celery transfer task.

    """
    with get_session_maker().begin() as session:
        transfer = session.get(Transfer, internal_transfer_id)
        assert transfer is not None
        transfer.task_id = typing.cast(sqlalchemy.Column, str(task_id))
        transfer.updated = typing.cast(
            sqlalchemy.Column, datetime.datetime.now(datetime.timezone.utc))


def update_transfer_validator_nonce(internal_transfer_id: int,
                                    validator_nonce: int) -> None:
    """Update a transfer's validator nonce.

    Parameters
    ----------
    internal_transfer_id : int
        The unique internal ID of the transfer.
    validator_nonce : int
        The new validator nonce assigned to the transfer.

    """
    statement = sqlalchemy.update(Transfer).where(
        Transfer.id == internal_transfer_id).values(
            validator_nonce=validator_nonce,
            updated=datetime.datetime.now(datetime.timezone.utc))
    with get_session_maker().begin() as session:
        session.execute(statement)


def _read_id(session: sqlalchemy.orm.Session, model: typing.Type[B],
             **kwargs: typing.Any) -> typing.Optional[int]:
    statement = sqlalchemy.select(model.id).filter_by(**kwargs)
    return session.execute(statement).scalar_one_or_none()


def _read_forwarder_contract_id(
        session: sqlalchemy.orm.Session, blockchain: Blockchain,
        address: BlockchainAddress) -> typing.Optional[int]:
    return _read_id(session, ForwarderContract, blockchain_id=blockchain.value,
                    address=address)


def _read_hub_contract_id(session: sqlalchemy.orm.Session,
                          blockchain: Blockchain,
                          address: BlockchainAddress) -> typing.Optional[int]:
    return _read_id(session, HubContract, blockchain_id=blockchain.value,
                    address=address)


def _read_token_contract_id(
        session: sqlalchemy.orm.Session, blockchain: Blockchain,
        address: BlockchainAddress) -> typing.Optional[int]:
    return _read_id(session, TokenContract, blockchain_id=blockchain.value,
                    address=address)


def _read_validator_node_id(
        session: sqlalchemy.orm.Session, forwarder_contract_id: int,
        address: BlockchainAddress) -> typing.Optional[int]:
    return _read_id(session, ValidatorNode,
                    forwarder_contract_id=forwarder_contract_id,
                    address=address)


def _create_with_id(session: sqlalchemy.orm.Session, model: typing.Type[B],
                    **kwargs: typing.Any) -> int:
    statement = sqlalchemy.insert(model).values(**kwargs).returning(model.id)
    try:
        with session.begin_nested():
            return session.execute(statement).scalar_one()
    except sqlalchemy.exc.IntegrityError:
        # Non-critical error that can happen in a parallel execution
        # environment due to a race condition
        _logger.warning('instance already created', exc_info=True)
        id_ = _read_id(session, model, **kwargs)
        assert id_ is not None
        return id_


def _create_forwarder_contract(session: sqlalchemy.orm.Session,
                               blockchain: Blockchain,
                               address: BlockchainAddress) -> int:
    return _create_with_id(session, ForwarderContract,
                           blockchain_id=blockchain.value, address=address)


def _create_hub_contract(session: sqlalchemy.orm.Session,
                         blockchain: Blockchain,
                         address: BlockchainAddress) -> int:
    return _create_with_id(session, HubContract,
                           blockchain_id=blockchain.value, address=address)


def _create_token_contract(session: sqlalchemy.orm.Session,
                           blockchain: Blockchain,
                           address: BlockchainAddress) -> int:
    return _create_with_id(session, TokenContract,
                           blockchain_id=blockchain.value, address=address)


def _create_validator_node(session: sqlalchemy.orm.Session,
                           forwarder_contract_id: int,
                           address: BlockchainAddress) -> int:
    return _create_with_id(session, ValidatorNode,
                           forwarder_contract_id=forwarder_contract_id,
                           address=address)
