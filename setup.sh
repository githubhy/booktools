#!/usr/bin/env bash

SCRIPT_DIR=$( dirname -- "${BASH_SOURCE[0]}" )

sudo apt-get install -y graphviz graphviz-dev
python -m pip install --upgrade pip
pip install -r ${SCRIPT_DIR}/proc_book/requirements.txt

pytest ${SCRIPT_DIR}/