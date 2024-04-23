from pantos.validatornode.business.signatures import SignatureInteractor
from pantos.validatornode.business.signatures import SignatureInteractorError
from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.business.transfers import TransferInteractorError


def test_signature_interactor_get_error_class_correct():
    assert SignatureInteractor().get_error_class() is SignatureInteractorError
    assert SignatureInteractor.get_error_class() is SignatureInteractorError


def test_transfer_interactor_get_error_class_correct():
    assert TransferInteractor().get_error_class() is TransferInteractorError
    assert TransferInteractor.get_error_class() is TransferInteractorError
