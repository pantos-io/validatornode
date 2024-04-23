import pytest

from pantos.validatornode.business.signatures import SignatureInteractor

_SIGNATURE = ('0x89f4bb92379a5f1ab97a8dcf01c73d1eb6d25e173fa17286fa5ed2416e369'
              '67a3e68f634f808e74c1f018cfd55264c9ce961772fcbda4bba627603f7c196'
              '1aa11b')


@pytest.fixture
def signature():
    return _SIGNATURE


@pytest.fixture
def signature_interactor():
    return SignatureInteractor()
