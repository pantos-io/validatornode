"""Module for loading, validating, and accessing the Validator Node's
configuration.

"""
import itertools
import typing

from pantos.common.blockchains.base import MIN_ADAPTABLE_FEE_INCREASE_FACTOR
from pantos.common.blockchains.enums import Blockchain
from pantos.common.configuration import Config
from pantos.common.logging import LogFormat

from pantos.validatornode.protocol import get_supported_protocol_versions

_DEFAULT_FILE_NAME: typing.Final[str] = 'validator-node-config.yml'
"""Default configuration file name."""

config = Config(_DEFAULT_FILE_NAME)
"""Singleton object holding the configuration values."""

_VALIDATION_SCHEMA_BLOCKCHAIN = {
    'type': 'dict',
    'required': True,
    'schema': {
        'active': {
            'type': 'boolean',
            'default': True
        },
        'private_key': {
            'type': 'string',
            'required': True,
            'empty': False,
            'coerce': 'load_if_file'
        },
        'private_key_password': {
            'type': 'string',
            'required': True
        },
        'providers': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'string',
            }
        },
        'fallback_providers': {
            'type': 'list',
            'required': False,
            'schema': {
                'type': 'string',
            }
        },
        'provider_timeout': {
            'type': 'integer',
            'nullable': True,
            'default': None
        },
        'average_block_time': {
            'type': 'integer',
            'required': True
        },
        'chain_id': {
            'type': 'integer',
            'required': True
        },
        'hub': {
            'type': 'string',
            'required': True
        },
        'forwarder': {
            'type': 'string',
            'required': True
        },
        'pan_token': {
            'type': 'string',
            'required': True
        },
        'from_block': {
            'type': 'integer',
            'required': True
        },
        'outgoing_transfers_number_blocks': {
            'type': 'integer',
            'required': True
        },
        'confirmations': {
            'type': 'integer',
            'required': True
        },
        'min_adaptable_fee_per_gas': {
            'type': 'integer',
            'required': True
        },
        'max_total_fee_per_gas': {
            'type': 'integer'
        },
        'adaptable_fee_increase_factor': {
            'type': 'float',
            'min': MIN_ADAPTABLE_FEE_INCREASE_FACTOR,
            'required': True
        },
        'blocks_until_resubmission': {
            'type': 'integer',
            'required': True
        }
    }
}
"""Schema for validating a blockchain entry in the configuration file."""

_VALIDATION_SCHEMA_LOG = {
    'type': 'dict',
    'required': True,
    'schema': {
        'format': {
            'type': 'string',
            'required': True,
            'allowed': [log_format.name.lower() for log_format in LogFormat]
        },
        'console': {
            'type': 'dict',
            'required': True,
            'schema': {
                'enabled': {
                    'type': 'boolean',
                    'required': True
                }
            }
        },
        'file': {
            'type': 'dict',
            'required': True,
            'schema': {
                'enabled': {
                    'type': 'boolean',
                    'required': True
                },
                'name': {
                    'type': 'string',
                    'required': True,
                    'empty': False
                },
                'max_bytes': {
                    'type': 'integer',
                    'required': True
                },
                'backup_count': {
                    'type': 'integer',
                    'required': True
                }
            }
        }
    }
}
"""Schema for validating a log entry in the configuration file."""

_VALIDATION_SCHEMA_TASK = {
    'type': 'dict',
    'required': True,
    'schema': {
        'retry_interval_in_seconds': {
            'type': 'integer',
            'required': True
        },
        'retry_interval_after_error_in_seconds': {
            'type': 'integer',
            'required': True
        }
    }
}
"""Schema for validating a task entry in the configuration file."""

_VALIDATION_SCHEMA = {
    'protocol': {
        'type': 'string',
        'required': True,
        'allowed': [
            str(protocol_version)
            for protocol_version in get_supported_protocol_versions()
        ]
    },
    'application': {
        'type': 'dict',
        'required': True,
        'schema': {
            'debug': {
                'type': 'boolean',
                'default': False
            },
            'host': {
                'type': 'string',
                'empty': False,
                'required': True
            },
            'port': {
                'type': 'integer',
                'min': 0,
                'required': True
            },
            'ssl_certificate': {
                'type': 'string',
                'dependencies': 'ssl_private_key',
                'empty': False
            },
            'ssl_private_key': {
                'type': 'string',
                'dependencies': 'ssl_certificate',
                'empty': False
            },
            'mode': {
                'type': 'string',
                'required': True,
                'allowed': ['primary', 'secondary']
            },
            'primary_url': {
                'type': 'string',
                'required': True,
                'empty': False
            },
            'log': _VALIDATION_SCHEMA_LOG
        }
    },
    'database': {
        'type': 'dict',
        'required': True,
        'schema': {
            'url': {
                'type': 'string',
                'required': True
            },
            'pool_size': {
                'type': 'integer',
                'required': True
            },
            'max_overflow': {
                'type': 'integer',
                'required': True
            },
            'echo': {
                'type': 'boolean',
                'default': False
            },
            'alembic_config': {
                'type': 'string',
                'required': True,
                'empty': False
            },
            'apply_migrations': {
                'type': 'boolean',
                'default': False,
            }
        }
    },
    'celery': {
        'type': 'dict',
        'required': True,
        'schema': {
            'broker': {
                'type': 'string',
                'required': True
            },
            'backend': {
                'type': 'string',
                'required': True
            },
            'log': _VALIDATION_SCHEMA_LOG
        }
    },
    'monitor': {
        'type': 'dict',
        'required': True,
        'schema': {
            'interval': {
                'type': 'integer',
                'required': True
            },
            'number_threads': {
                'type': 'integer',
                'required': True
            }
        }
    },
    'tasks': {
        'type': 'dict',
        'required': True,
        'schema': {
            'confirm_transfer': _VALIDATION_SCHEMA_TASK,
            'submit_transfer_onchain': _VALIDATION_SCHEMA_TASK,
            'submit_transfer_to_primary_node': _VALIDATION_SCHEMA_TASK,
            'validate_transfer': _VALIDATION_SCHEMA_TASK
        }
    },
    'blockchains': {
        'type': 'dict',
        'required': True,
        'schema': dict(
            zip([b.name.lower() for b in Blockchain],
                itertools.repeat(_VALIDATION_SCHEMA_BLOCKCHAIN)))
    }
}
"""Schema for validating the configuration file."""


def get_blockchain_config(
        blockchain: Blockchain) -> typing.Dict[str, typing.Any]:
    """Get a blockchain-specific configuration dictionary.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain to get the configuration for.

    Returns
    -------
    dict
        The blockchain-specific configuration.

    """
    return config['blockchains'][blockchain.name.lower()]


def get_blockchains_rpc_nodes() \
        -> dict[Blockchain, tuple[list[str], float | None]]:
    """Get the RPC nodes for the active blockchains.

    Returns
    -------
    dict[Blockchain, tuple[list[str], int]]
        The RPC nodes for the blockchains.

    """
    rpc_nodes = {}
    for blockchain in Blockchain:
        blockchain_config = get_blockchain_config(blockchain)
        if blockchain_config['active']:
            timeout = float(
                blockchain_config.get('provider_timeout')  # type: ignore
            ) if blockchain_config.get('provider_timeout') else None
            rpc_nodes[blockchain] = (
                blockchain_config['providers'] +
                blockchain_config.get('fallback_providers', []), timeout)
    return rpc_nodes


def load_config(file_path: typing.Optional[str] = None,
                reload: bool = True) -> None:
    """Load the configuration from a configuration file.

    Parameters
    ----------
    file_path : str or None
        The path to the configuration file (typical configuration file
        locations are searched if none is specified).
    reload : bool
        If True, the configuration is also loaded if it was already
        loaded before.

    Raises
    ------
    ConfigError
        If the configuration cannot be loaded (e.g. due to an invalid
        configuration file).

    See Also
    --------
    Config.load

    """
    if reload or not config.is_loaded():
        config.load(_VALIDATION_SCHEMA, file_path)
