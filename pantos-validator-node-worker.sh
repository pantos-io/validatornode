#! /bin/sh

celery -A pantos.validatornode worker -l INFO -n pantos.validatornode -Q pantos.validatornode
