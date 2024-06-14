"""Entry point for running the Pantos Validator Node application in
Flask's built-in web server.

"""
from pantos.validatornode.application import create_application
from pantos.validatornode.configuration import config

if __name__ == '__main__':
    application = create_application()
    host = config['application']['host']
    port = config['application']['port']
    ssl_certificate = config['application'].get('ssl_certificate')
    ssl_private_key = config['application'].get('ssl_private_key')
    ssl_context = (None if ssl_certificate is None else
                   (ssl_certificate, ssl_private_key))
    debug = config['application']['debug']
    application.run(host=host, port=port, debug=debug, ssl_context=ssl_context,
                    use_reloader=False)
