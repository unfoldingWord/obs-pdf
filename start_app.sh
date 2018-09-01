#!/usr/bin/env bash

thisDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# update the code
cd "${thisDir}"
#git fetch --all && git reset --hard origin/master
source venv/bin/activate
#pip install -r requirements.txt

# start the flask app
cd "${thisDir}/public"
#export FLASK_ENV=development
#export FLASK_APP=obs_pdf.py
#flask run --host=0.0.0.0
uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:app --ini ../config/obs-pdf.ini
