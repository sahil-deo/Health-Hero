#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python -c "from main import init_db; init_db()"