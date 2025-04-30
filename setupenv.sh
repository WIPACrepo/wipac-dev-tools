#!/bin/sh
unset PYTHONPATH
python3 -m venv ./env
echo "unset PYTHONPATH" >> env/bin/activate
. env/bin/activate
pip install --upgrade pip
pip install -e .[dev,mypy]
