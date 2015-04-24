#!/bin/bash

# setup the virtualenv
python2 ./src/bin/venv-update.py ./env/dev ./etc/requirements.txt

# get the precommit system active
pre-commit install
