"""Provides the Pantos Validator Node application for deployments on
WSGI-compliant web servers.

"""
from pantos.validatornode.application import create_application

application = create_application()
