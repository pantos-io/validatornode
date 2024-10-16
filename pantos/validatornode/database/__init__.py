"""Package for managing and accessing the database.

"""
import logging
import typing

import alembic
import alembic.config
import sqlalchemy
import sqlalchemy.orm
from pantos.common.blockchains.enums import Blockchain

from pantos.validatornode.configuration import config
from pantos.validatornode.database.enums import TransferStatus
from pantos.validatornode.database.exceptions import DatabaseError
from pantos.validatornode.database.models import Blockchain as Blockchain_
from pantos.validatornode.database.models import \
    TransferStatus as TransferStatus_

_session_maker: typing.Optional[sqlalchemy.orm.sessionmaker] = None
_sql_engine: typing.Optional[sqlalchemy.engine.base.Engine] = None
_logger = logging.getLogger(__name__)


def get_engine() -> sqlalchemy.engine.base.Engine:
    """Get the session engine for interacting with the
    connection object, used to clean up connections.

    Returns
    -------
    sqlalchemy.engine.base.Engine
        The session engine.

    Raises
    ------
    DatabaseError
        If the database package has not been initialized.

    """
    if _sql_engine is None:
        raise DatabaseError('database package not yet initialized')
    return _sql_engine


def get_session_maker() -> sqlalchemy.orm.sessionmaker:
    """Get the session maker for making sessions for managing
    persistence operations for ORM-mapped objects.

    Returns
    -------
    sqlalchemy.orm.sessionmaker
        The session maker.

    Raises
    ------
    DatabaseError
        If the database package has not been initialized.

    """
    if _session_maker is None:
        raise DatabaseError('database package not yet initialized')
    return _session_maker


def get_session() -> sqlalchemy.orm.Session:
    """Get a session for managing persistence operations for ORM-mapped
    objects.

    Returns
    -------
    sqlalchemy.orm.Session
        The session.

    Raises
    ------
    DatabaseError
        If the database package has not been initialized.

    """
    return get_session_maker()()


def run_migrations(config_path: str, data_source_url: str) -> None:
    _logger.info(f'running database migrations using {config_path}')
    alembic_config = alembic.config.Config(config_path)
    alembic_config.set_main_option('sqlalchemy.url', data_source_url)
    alembic.command.upgrade(alembic_config, 'head')
    _logger.info('database migrations done')


def initialize_package(is_flask_app: bool = False) -> None:
    # Before connecting, run alembic to ensure
    # the database schema is up to date
    if is_flask_app and config['database']['apply_migrations']:
        run_migrations(config['database']['alembic_config'],
                       config['database']['url'])

    global _sql_engine
    _sql_engine = sqlalchemy.create_engine(
        config['database']['url'], pool_size=config['database']['pool_size'],
        max_overflow=config['database']['max_overflow'], pool_pre_ping=True,
        echo=config['database']['echo'])
    global _session_maker
    _session_maker = sqlalchemy.orm.sessionmaker(bind=_sql_engine)
    # Initialize the tables
    if is_flask_app:
        with _session_maker.begin() as session:
            # Blockchain table
            blockchain_ids = session.execute(sqlalchemy.select(
                Blockchain_.id)).scalars().all()
            for blockchain in sorted(Blockchain):
                if blockchain.value not in blockchain_ids:
                    session.execute(
                        sqlalchemy.insert(Blockchain_).values(
                            id=blockchain.value, name=blockchain.name))
            # Transfer status table
            transfer_status_ids = session.execute(
                sqlalchemy.select(TransferStatus_.id)).scalars().all()
            for transfer_status in sorted(TransferStatus):
                if transfer_status.value not in transfer_status_ids:
                    session.execute(
                        sqlalchemy.insert(TransferStatus_).values(
                            id=transfer_status.value,
                            name=transfer_status.name))
