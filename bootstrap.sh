#!/bin/bash

# get the precommit system active
echo "Installing Yelp pre-commit hooks"
pre-commit install


# setup the virtualenv
echo "Creating virtualenv..."
python2 ./bin/venv-update.py ./env/dev ./etc/requirements.txt

