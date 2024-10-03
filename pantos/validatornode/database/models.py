"""Module that defines the database models.

"""
import datetime
import typing

import sqlalchemy
import sqlalchemy.orm

UNIQUE_BLOCKCHAIN_NONCE_CONSTRAINT = 'unique_blockchain_nonce'
UNIQUE_VALIDATOR_NONCE_CONSTRAINT = 'unique_validator_nonce'

Base: typing.Any = sqlalchemy.orm.declarative_base()
"""SQLAlchemy base class for declarative class definitions."""


class Blockchain(Base):
    """Model class for the "blockchains" database table. Each instance
    represents a blockchain supported by Pantos.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique blockchain ID (primary key, equal to the
        pantos.common.blockchains.Blockchain enum value).
    name : sqlalchemy.Column
        The blockchain's name (equal to the
        pantos.common.blockchains.Blockchain enum name).
    last_block_number : sqlalchemy.Column
        The last block monitored for new Pantos TransferFromSucceeded
        events on the blockchain (-1 if no block has been monitored).

    """
    __tablename__ = 'blockchains'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    last_block_number = sqlalchemy.Column(sqlalchemy.BigInteger,
                                          nullable=False, default=-1)
    hub_contracts = sqlalchemy.orm.relationship('HubContract',
                                                back_populates='blockchain')
    forwarder_contracts = sqlalchemy.orm.relationship(
        'ForwarderContract', back_populates='blockchain')
    token_contracts = sqlalchemy.orm.relationship('TokenContract',
                                                  back_populates='blockchain')


class HubContract(Base):
    """Model class for the "hub_contracts" database table. Each
    instance represents a Pantos Hub contract deployed on a blockchain.
    It can be either the current or an old version of the Pantos Hub
    contract on its blockchain.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique hub contract ID (primary key).
    blockchain_id : sqlalchemy.Column
        The unique blockchain ID (foreign key).
    address : sqlalchemy.Column
        The unique address of the contract on its blockchain.

    """
    __tablename__ = 'hub_contracts'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    blockchain_id = sqlalchemy.Column(sqlalchemy.Integer,
                                      sqlalchemy.ForeignKey('blockchains.id'),
                                      nullable=False)
    address = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    blockchain = sqlalchemy.orm.relationship('Blockchain',
                                             back_populates='hub_contracts')
    __table_args__ = (sqlalchemy.UniqueConstraint(blockchain_id, address), )


class ForwarderContract(Base):
    """Model class for the "forwarder_contracts" database table. Each
    instance represents a Pantos Forwarder contract deployed on a
    blockchain. It can be either the current or an old version of the
    Pantos Forwarder contract on its blockchain.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique forwarder contract ID (primary key).
    blockchain_id : sqlalchemy.Column
        The unique blockchain ID (foreign key).
    address : sqlalchemy.Column
        The unique address of the contract on its blockchain.

    """
    __tablename__ = 'forwarder_contracts'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    blockchain_id = sqlalchemy.Column(sqlalchemy.Integer,
                                      sqlalchemy.ForeignKey('blockchains.id'),
                                      nullable=False)
    address = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    blockchain = sqlalchemy.orm.relationship(
        'Blockchain', back_populates='forwarder_contracts')
    validator_nodes = sqlalchemy.orm.relationship(
        'ValidatorNode', back_populates='forwarder_contract')
    __table_args__ = (sqlalchemy.UniqueConstraint(blockchain_id, address), )


class TokenContract(Base):
    """Model class for the "token_contracts" database table. Each
    instance represents a token contract deployed on a supported
    blockchain and registered at the Pantos Hub.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique token contract ID (primary key).
    blockchain_id : sqlalchemy.Column
        The unique blockchain ID (foreign key).
    address : sqlalchemy.Column
        The unique address of the contract on its blockchain.

    """
    __tablename__ = 'token_contracts'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    blockchain_id = sqlalchemy.Column(sqlalchemy.Integer,
                                      sqlalchemy.ForeignKey('blockchains.id'),
                                      nullable=False)
    address = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    blockchain = sqlalchemy.orm.relationship('Blockchain',
                                             back_populates='token_contracts')
    __table_args__ = (sqlalchemy.UniqueConstraint(blockchain_id, address), )


class ValidatorNode(Base):
    """Model class for the "validator_nodes" database table. Each
    instance represents a (primary or secondary) validator node
    registered at the Pantos Forwarder contract of a supported
    blockchain.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique internal validator node ID (primary key).
    forwarder_contract_id : sqlalchemy.Column
        The unique internal Forwarder contract ID (foreign key).
    address : sqlalchemy.Column
        The unique address of the validator node on the Forwarder
        contract's blockchain.
    created : sqlalchemy.Column
        The timestamp when the validator node was added.

    """
    __tablename__ = 'validator_nodes'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    forwarder_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('forwarder_contracts.id'),
        nullable=False)
    address = sqlalchemy.Column(sqlalchemy.String(42), nullable=False)
    created = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False,
                                default=datetime.datetime.utcnow)
    forwarder_contract = sqlalchemy.orm.relationship(
        'ForwarderContract', back_populates='validator_nodes')
    signatures = sqlalchemy.orm.relationship('ValidatorNodeSignature',
                                             back_populates='validator_node')
    __table_args__ = (sqlalchemy.UniqueConstraint(forwarder_contract_id,
                                                  address), )


class ValidatorNodeSignature(Base):
    """Model class for the "validator_node_signatures" database table.
    Each instance represents a signature of a validator node for a
    cross-chain token transfer.

    Attributes
    ----------
    transfer_id : sqlalchemy.Column
        The unique internal transfer ID (part of the composite primary
        key).
    validator_node_id : sqlalchemy.Column
        The unique internal validator node ID (part of the composite
        primary key).
    signature : sqlalchemy.Column
        The signature of the validator node for the cross-chain token
        transfer.
    created : sqlalchemy.Column
        The timestamp when the signature was added.

    """
    __tablename__ = 'validator_node_signatures'
    transfer_id = sqlalchemy.Column(sqlalchemy.Integer,
                                    sqlalchemy.ForeignKey('transfers.id'),
                                    primary_key=True)
    validator_node_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('validator_nodes.id'),
        primary_key=True)
    signature = sqlalchemy.Column(sqlalchemy.String(132), unique=True,
                                  nullable=False)
    created = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False,
                                default=datetime.datetime.utcnow)
    transfer = sqlalchemy.orm.relationship(
        'Transfer', back_populates='validator_node_signatures')
    validator_node = sqlalchemy.orm.relationship('ValidatorNode',
                                                 back_populates='signatures')


class TransferStatus(Base):
    """Model class for the "transfer_status" database table. Each
    instance represents a possible status of Pantos transfers.

    Attributes
    ----------
    id : sqlalchemy.Column
        The unique transfer status ID (primary key, equal to the
        pantos.validatornode.database.enums.TransferStatus enum
        value).
    name : sqlalchemy.Column
        The transfer status's name (equal to the
        pantos.validatornode.database.enums.TransferStatus enum
        name).

    """
    __tablename__ = 'transfer_status'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Text, nullable=False)


class Transfer(Base):
    """Model class for the "transfers" database table. Each instance
    represents a cross-chain Pantos token transfer.

    Attributes
    ----------
    id : sqlalchemy.Column
        The blockchain-independent unique ID of the transfer (primary
        key).
    source_blockchain_id : sqlalchemy.Column
        The unique ID of the source blockchain (foreign key).
    destination_blockchain_id : sqlalchemy.Column
        The unique ID of the destination blockchain (foreign key).
    sender_address : sqlalchemy.Column
        The address of the sender on the source blockchain.
    recipient_address : sqlalchemy.Column
        The address of the recipient on the destination blockchain.
    source_token_contract_id : sqlalchemy.Column
        The unique token contract ID of the token on the source
        blockchain (foreign key).
    destination_token_contract_id : sqlalchemy.Column
        The unique token contract ID of the token on the destination
        blockchain (foreign key).
    amount : sqlalchemy.Column
        The amount of tokens sent by the sender to the recipient.
    validator_nonce : sqlalchemy.Column
        The nonce of the validator at the Pantos Forwarder contract of
        the destination blockchain.
    source_hub_contract_id : sqlalchemy.Column
        The unique ID of the Pantos Hub contract on the source
        blockchain (foreign key).
    destination_hub_contract_id : sqlalchemy.Column
        The unique ID of the Pantos Hub contract on the destination
        blockchain (foreign key).
    destination_forwarder_contract_id : sqlalchemy.Column
        The unique ID of the Pantos Forwarder contract on the
        destination blockchain (foreign key).
    task_id : sqlalchemy.Column
        The unique ID of the Celery transfer task.
    source_transfer_id : sqlalchemy.Column
        The unique transfer ID assigned by the Pantos Hub contract of
        the source blockchain.
    destination_transfer_id : sqlalchemy.Column
        The unique transfer ID assigned by the Pantos Hub contract of
        the destination blockchain.
    source_transaction_id : sqlalchemy.Column
        The unique transaction ID/hash of the source blockchain for the
        transfer.
    destination_transaction_id : sqlalchemy.Column
        The unique transaction ID/hash of the destination blockchain for
        the transfer.
    source_block_number : sqlalchemy.Column
        The block number of the source blockchain for the transfer.
    destination_block_number : sqlalchemy.Column
        The block number of the destination blockchain for the transfer.
    nonce : sqlalchemy.Column
        The nonce used for the Validator Node's transaction on the
        destination blockchain (NULL if the transaction has not been
        sent yet or if the transaction has failed and the nonce has been
        reused in another transaction).
    status_id : sqlalchemy.Column
        The ID of the transfer status (foreign key).
    created : sqlalchemy.Column
        The timestamp when the transfer request was received.
    updated : sqlalchemy.Column
        The timestamp when the transfer was last updated.

    """
    __tablename__ = 'transfers'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    source_blockchain_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('blockchains.id'),
        nullable=False)
    destination_blockchain_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('blockchains.id'),
        nullable=False)
    sender_address = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    recipient_address = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    source_token_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('token_contracts.id'),
        nullable=False)
    destination_token_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('token_contracts.id'),
        nullable=False)
    amount = sqlalchemy.Column(
        # Large enough for a 256-bit unsigned integer
        sqlalchemy.Numeric(precision=78, scale=0),
        nullable=False)
    validator_nonce = sqlalchemy.Column(
        # Large enough for a 256-bit unsigned integer
        sqlalchemy.Numeric(precision=78, scale=0),
        nullable=False)
    source_hub_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('hub_contracts.id'),
        nullable=False)
    destination_hub_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('hub_contracts.id'))
    destination_forwarder_contract_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey('forwarder_contracts.id'))
    task_id = sqlalchemy.Column(sqlalchemy.Text, unique=True)
    source_transfer_id = sqlalchemy.Column(
        # Large enough for a 256-bit unsigned integer
        sqlalchemy.Numeric(precision=78, scale=0),
        nullable=False)
    destination_transfer_id = sqlalchemy.Column(
        # Large enough for a 256-bit unsigned integer
        sqlalchemy.Numeric(precision=78, scale=0))
    source_transaction_id = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    destination_transaction_id = sqlalchemy.Column(sqlalchemy.Text)
    source_block_number = sqlalchemy.Column(sqlalchemy.BigInteger,
                                            nullable=False)
    destination_block_number = sqlalchemy.Column(sqlalchemy.BigInteger)
    nonce = sqlalchemy.Column(sqlalchemy.BigInteger)
    status_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey('transfer_status.id'),
                                  nullable=False)
    created = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False,
                                default=datetime.datetime.utcnow)
    updated = sqlalchemy.Column(sqlalchemy.DateTime)
    source_blockchain = sqlalchemy.orm.relationship(
        'Blockchain',
        primaryjoin='Transfer.source_blockchain_id==Blockchain.id')
    destination_blockchain = sqlalchemy.orm.relationship(
        'Blockchain',
        primaryjoin='Transfer.destination_blockchain_id==Blockchain.id')
    source_token_contract = sqlalchemy.orm.relationship(
        'TokenContract',
        primaryjoin='Transfer.source_token_contract_id==TokenContract.id',
        lazy='joined')
    destination_token_contract = sqlalchemy.orm.relationship(
        'TokenContract',
        primaryjoin='Transfer.destination_token_contract_id==TokenContract.id',
        lazy='joined')
    source_hub_contract = sqlalchemy.orm.relationship(
        'HubContract',
        primaryjoin='Transfer.source_hub_contract_id==HubContract.id')
    destination_hub_contract = sqlalchemy.orm.relationship(
        'HubContract',
        primaryjoin='Transfer.destination_hub_contract_id==HubContract.id')
    destination_forwarder_contract = sqlalchemy.orm.relationship(
        'ForwarderContract')
    validator_node_signatures = sqlalchemy.orm.relationship(
        'ValidatorNodeSignature', back_populates='transfer')
    status = sqlalchemy.orm.relationship('TransferStatus')
    __table_args__ = (sqlalchemy.UniqueConstraint(
        destination_forwarder_contract_id, validator_nonce,
        name=UNIQUE_VALIDATOR_NONCE_CONSTRAINT),
                      sqlalchemy.UniqueConstraint(
                          destination_blockchain_id, nonce, deferrable=True,
                          name=UNIQUE_BLOCKCHAIN_NONCE_CONSTRAINT),
                      sqlalchemy.UniqueConstraint(source_blockchain_id,
                                                  source_transfer_id),
                      sqlalchemy.UniqueConstraint(destination_blockchain_id,
                                                  destination_transfer_id),
                      sqlalchemy.UniqueConstraint(source_blockchain_id,
                                                  source_transaction_id),
                      sqlalchemy.UniqueConstraint(destination_blockchain_id,
                                                  destination_transaction_id))
