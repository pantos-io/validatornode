#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE "pantos-validator-node" WITH LOGIN PASSWORD 'pantos';
    CREATE DATABASE "pantos-validator-node" WITH OWNER "pantos-validator-node";
    CREATE DATABASE "pantos-validator-node-celery" WITH OWNER "pantos-validator-node";
    CREATE DATABASE "pantos-validator-node-test" WITH OWNER "pantos-validator-node";
EOSQL
