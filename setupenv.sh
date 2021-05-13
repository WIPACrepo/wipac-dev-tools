#!/bin/sh
unset PYTHONPATH
python3.7 -m venv ./env
echo "unset PYTHONPATH" >> env/bin/activate
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

