<img src="https://raw.githubusercontent.com/pantos-io/validatornode/img/pantos-logo-full.svg" alt="Pantos logo" align="right" width="120" />

[![CI](https://github.com/pantos-io/validatornode/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pantos-io/validatornode/actions/workflows/ci.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=pantos-io_validatornode&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=pantos-io_validatornode)



# Pantos Validator Node (reference implementation)

## 1. Introduction

### 1.1 Overview

Welcome to the documentation for Pantos Validator Node. 

The Pantos Validator Node is responsible for validating cross-chain transfers on behalf of the users. To initiate a cross-chain token transfer, a client has to send a signed request to a service node. To find an appropriate service node, the client can query the PantosHub contract of the source blockchain. To enable this, each service node registers itself at the PantosHub contract of each source blockchain supported by the service node.

### 1.2 Features

The Pantos Validator Node is split into two applications:

#### Web server application

The web server application is responsible for the following:

1. Serving signed (by the service node) bids.
2. Accepting signed (by the user) transfer requests.

#### Celery application

The celery application is responsible for the following:

1. Updating the bids later served to the user through the web application.
2. Submitting the signed transfer requests to the source blockchain.

## 2. Installation

### IMPORTANT ###

We provide two ways to modify the app configuration, either through `validator-node-config.env` or `validator-node-config.yml`. We recommend using the `.env` file, as the `.conf` file is overwritten on every install.

While using the `.env` file you need to be aware that any fields containing certain special characters need to be wrapped around single quotes (e.g. `ETHEREUM_PRIVATE_KEY_PASSWORD='12$$#%R^'`).

The application will complain on startup should the configuration be incorrect.

### 2.1 System requirements

The exact system requirements depend on the operating system, other software installed, and the expected load of the Pantos Validator Node (which determines the concurrency and number of Celery workers). Here we assume a virtual machine (VM) with a minimal Debian or Ubuntu installation. The Pantos Validator Node's web server and Celery workers, as well as PostgreSQL and RabbitMQ are assumed to run on the same VM.

The minimum system requirements then are
- 2 vCPUs,
- 2 GiB memory (including one Celery worker),
- 0.25 GiB memory per additional Celery worker (for scaling), and
- 16 GiB storage.

### 2.2 Pre-built packages

There are two ways to install the apps using pre-built packages:

#### Debian package distribution

We provide Debian packages alongside every release, you can find them in the [releases tab](https://github.com/pantos-io/validatornode/releases). Further information on how to use the service node packages can be found [here](https://pantos.gitbook.io/technical-documentation/general/validator-node).

We have a PPA hosted on GitHub, which can be accessed as follows:

```bash
curl -s --compressed "https://pantos-io.github.io/validatornode/KEY.gpg" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/validatornode.gpg >/dev/null
sudo curl -s --compressed -o /etc/apt/sources.list.d/pantos-validatornode.list "https://pantos-io.github.io/validatornode/pantos-validatornode.list"
sudo apt update
sudo apt install pantos-validator-node
```

#### Docker images

We also distribute docker images in DockerHub with each release. These are made available under the pantosio project as either [**app**](https://hub.docker.com/r/pantosio/validator-node-app) or [**worker**](https://hub.docker.com/r/pantosio/validator-node-worker).

You can run a local setup with docker by doing the following steps:

- Enable swarm mode with `docker swarm init`. This is required because we're using the `overlay` network driver.
- The variables `DB_URL`, `CELERY_BACKEND` and `CELERY_BROKER` are already defined in the `docker-compose.yml`
- Modify the `.env` file to match your current setup
- Ensure you have a `keystore` file located in the same directory
- Run `docker compose up`

Please note that you may need to add a load balancer or another webserver in front of this setup should you want to host this setup under a specific domain.

If you're hosting this on a cloud provider (AWS, GCP, Azure or alike), these are normally provided. You just need to point the load balancer to the port exposed by the app, `8080`, and configure the rest accordingly.

##### Local development with Docker

You can do local development with Docker by enabling dev mode (Docker watch mode). To do so, set the environment variable `DEV_MODE` to true, like this:

`DEV_MODE=true make docker`

#### Multiple local deployments

We support multiple local deployments, for example for testing purposes, you can run the stacks like this:

`make docker INSTANCE_COUNT=<number of instances>`

To remove all the stacks, run the following:

`make docker-remove`

Please note that this mode uses an incremental amount of resources and that Docker Desktop doesn't fully support displaying it, but it should be good enough to test multi-sig locally.

#### Python package

We distribute the package in test-pypi and pypi under the following projects: https://test.pypi.org/project/pantos-validator-node/ and https://pypi.org/project/pantos-validator-node/. You can install it to your project by using `pip install pantos-validator-node`.

### 2.3  Prerequisites

Please make sure that your environment meets the following requirements:

#### Python Version

The Pantos Service Node supports **Python 3.10** or higher. Ensure that you have the correct Python version installed before the installation steps. You can download the latest version of Python from the official [Python website](https://www.python.org/downloads/).

#### Library Versions

The Pantos Service Node has been tested with the library versions specified in **poetry.lock**.

#### Poetry

Poetry is our tool of choice for dependency management and packaging.

Installing: 
https://python-poetry.org/docs/#installing-with-the-official-installer
or
https://python-poetry.org/docs/#installing-with-pipx

By default poetry creates the venv directory under under ```{cache-dir}/virtualenvs```. If you opt for creating the virtualenv inside the project’s root directory, execute the following command:
```bash
poetry config virtualenvs.in-project true
```

### 2.4  Installation steps

#### Libraries

Create the virtual environment and install the dependencies:

```bash
$ poetry install --no-root
```

#### Pre-commit

In order to run pre-commit before a commit is done, you have to install it:

```bash
pre-commit install --hook-type commit-msg -f && pre-commit install
```

Whenever you try to make a commit, the pre-commit steps are executed.

## 3. Usage

### 3.1 Format, lint and test

Run the following command from the repository's root directory:

```bash
make code
```

### 3.2 Local development environment

#### PostgreSQL

Launch the PostgreSQL interactive terminal:

```bash
sudo -u postgres psql
```

Create a Service Node user and three databases:

```
CREATE ROLE "pantos-validator-node" WITH LOGIN PASSWORD '<PASSWORD>';
CREATE DATABASE "pantos-validator-node" WITH OWNER "pantos-validator-node";
CREATE DATABASE "pantos-validator-node-celery" WITH OWNER "pantos-validator-node";
CREATE DATABASE "pantos-validator-node-test" WITH OWNER "pantos-validator-node";
```

#### RabbitMQ

Create a Service Node user and virtual host:

```
sudo rabbitmqctl add_user pantos-validator-node <PASSWORD>
sudo rabbitmqctl add_vhost pantos-validator-node
sudo rabbitmqctl set_permissions -p pantos-validator-node pantos-validator-node ".*" ".*" ".*"
```

## 4. Contributing

For contributions take a look at our [code of conduct](CODE_OF_CONDUCT.md).
