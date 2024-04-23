import pytest
import sqlalchemy
import sqlalchemy.orm

from pantos.validatornode.database.models import Base


@pytest.fixture(scope='session')
def database_engine():
    database_engine = sqlalchemy.create_engine('sqlite:///')  # in memory
    with database_engine.connect() as connection:
        connection.execute(sqlalchemy.text("PRAGMA foreign_keys=ON;"))
    return database_engine


@pytest.fixture(scope='session')
def database_session_maker(database_engine):
    Base.metadata.create_all(bind=database_engine)
    yield sqlalchemy.orm.sessionmaker(bind=database_engine)
    Base.metadata.drop_all(bind=database_engine)
