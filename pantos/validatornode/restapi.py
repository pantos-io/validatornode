"""Module that implements the primary validator node's REST API.

"""
import logging
import typing

import flask
import flask_restful  # type: ignore
import marshmallow
import marshmallow.fields
from pantos.common.blockchains.enums import Blockchain
from pantos.common.restapi import Live
from pantos.common.restapi import NodesHealthResource
from pantos.common.restapi import bad_request
from pantos.common.restapi import conflict
from pantos.common.restapi import forbidden
from pantos.common.restapi import internal_server_error
from pantos.common.restapi import no_content_response
from pantos.common.restapi import ok_response
from pantos.common.restapi import resource_not_found

from pantos.validatornode.blockchains.factory import get_blockchain_client
from pantos.validatornode.business.base import DuplicateSignatureError
from pantos.validatornode.business.base import InvalidSignatureError
from pantos.validatornode.business.base import InvalidSignerError
from pantos.validatornode.business.base import UnknownTransferError
from pantos.validatornode.business.signatures import SignatureInteractor
from pantos.validatornode.business.transfers import TransferInteractor
from pantos.validatornode.configuration import get_blockchain_config

flask_app = flask.Flask(__name__)

_logger = logging.getLogger(__name__)


class _Schema(marshmallow.Schema):
    """Base validation schema.

    """
    def _validate_blockchain_id(self, field_name: str,
                                blockchain_id: int) -> None:
        active_blockchain_ids = [
            blockchain.value for blockchain in Blockchain
            if get_blockchain_config(blockchain)['active']
        ]
        if blockchain_id not in active_blockchain_ids:
            raise marshmallow.ValidationError(
                f'Blockchain ID must be one of {active_blockchain_ids}.',
                field_name=field_name)

    def _validate_transaction_id(self, field_name: str, blockchain: Blockchain,
                                 transaction_id: str) -> None:
        blockchain_client = get_blockchain_client(blockchain)
        if not blockchain_client.is_valid_transaction_id(transaction_id):
            raise marshmallow.ValidationError('Invalid transaction ID.',
                                              field_name=field_name)


class _TransferSignatureSchema(_Schema):
    """Validation schema for adding a secondary node signature for a
    cross-chain token transfer.

    """
    source_blockchain_id = marshmallow.fields.Integer(required=True)
    source_transaction_id = marshmallow.fields.String(required=True)
    signature = marshmallow.fields.String(required=True)

    @marshmallow.validates('source_blockchain_id')
    def __validate_source_blockchain_id(self,
                                        source_blockchain_id: int) -> None:
        self._validate_blockchain_id('source_blockchain_id',
                                     source_blockchain_id)

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def __validate_schema(self, data: dict[str, typing.Any],
                          **kwargs: typing.Any) -> None:
        source_blockchain = Blockchain(data['source_blockchain_id'])
        self._validate_transaction_id('source_transaction_id',
                                      source_blockchain,
                                      data['source_transaction_id'])


class _ValidatorNonceSchema(_Schema):
    """Validation schema for getting the validator nonce for a
    cross-chain token transfer.

    """
    source_blockchain_id = marshmallow.fields.Integer(required=True)
    source_transaction_id = marshmallow.fields.String(required=True)

    @marshmallow.validates('source_blockchain_id')
    def __validate_source_blockchain_id(self,
                                        source_blockchain_id: int) -> None:
        self._validate_blockchain_id('source_blockchain_id',
                                     source_blockchain_id)

    @marshmallow.validates_schema(skip_on_field_errors=True)
    def __validate_schema(self, data: dict[str, typing.Any],
                          **kwargs: typing.Any) -> None:
        source_blockchain = Blockchain(data['source_blockchain_id'])
        self._validate_transaction_id('source_transaction_id',
                                      source_blockchain,
                                      data['source_transaction_id'])


class _TransferSignature(flask_restful.Resource):
    """RESTful resource for adding a secondary node signature for a
    cross-chain token transfer.

    """
    def post(self) -> flask.Response:
        arguments = flask_restful.request.json
        _logger.info('new transfer signature request', extra=arguments)
        try:
            validated_arguments = _TransferSignatureSchema().load(arguments)
            source_blockchain = Blockchain(
                validated_arguments['source_blockchain_id'])
            source_transaction_id = validated_arguments[
                'source_transaction_id']
            signature = validated_arguments['signature']
            signature_add_request = \
                SignatureInteractor.SecondaryNodeSignatureAddRequest(
                    source_blockchain, source_transaction_id, signature)
            SignatureInteractor().add_secondary_node_signature(
                signature_add_request)
        except marshmallow.ValidationError as error:
            bad_request(error.messages)
        except DuplicateSignatureError:
            conflict('Duplicate signature.')
        except InvalidSignatureError:
            bad_request('Invalid signature.')
        except InvalidSignerError:
            forbidden('Invalid signer.')
        except UnknownTransferError:
            resource_not_found('Unknown transfer.')
        except Exception:
            _logger.critical('unable to process a transfer signature request',
                             exc_info=True)
            internal_server_error()
        return no_content_response()


class _ValidatorNonce(flask_restful.Resource):
    """RESTful resource for getting the validator nonce for a
    cross-chain token transfer.

    """
    def get(self) -> flask.Response:
        arguments = flask_restful.request.args
        _logger.info('new validator nonce request', extra=arguments)
        try:
            validated_arguments = _ValidatorNonceSchema().load(arguments)
            source_blockchain = Blockchain(
                validated_arguments['source_blockchain_id'])
            source_transaction_id = validated_arguments[
                'source_transaction_id']
            validator_nonce = TransferInteractor().get_validator_nonce(
                source_blockchain, source_transaction_id)
        except marshmallow.ValidationError as error:
            bad_request(error.messages)
        except UnknownTransferError:
            resource_not_found('Unknown transfer.')
        except Exception:
            _logger.critical('unable to process a validator nonce request',
                             exc_info=True)
            internal_server_error()
        return ok_response({'validator_nonce': validator_nonce})


# Register the RESTful resources
_restful_api = flask_restful.Api(flask_app)
_restful_api.add_resource(Live, '/health/live')
_restful_api.add_resource(NodesHealthResource, '/health/nodes')
_restful_api.add_resource(_TransferSignature, '/transfersignature')
_restful_api.add_resource(_ValidatorNonce, '/validatornonce')
