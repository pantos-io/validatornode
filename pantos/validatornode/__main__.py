"""Entry point for running the Pantos Validator Node application in
Flask's built-in web server.

"""
from pantos.validatornode.application import create_application
from pantos.validatornode.configuration import config

if __name__ == '__main__':
    application = create_application()
    host = config['application']['host']
    port = config['application']['port']
    debug = config['application']['debug']
    application.run(host=host, port=port, debug=debug, use_reloader=False)
