import unittest.mock

with unittest.mock.patch('pantos.validatornode.configuration.config'):
    import pantos.validatornode.celery  # noqa: F401
