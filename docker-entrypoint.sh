#!/usr/bin/env bash

thisDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# activate the virtual environment
cd "${thisDir}"
source venv/bin/activate

# start nginx
nginx -g "daemon off;" &

# start the flask app with uwsgi
cd "${thisDir}/public"
uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:app --ini ../config/obs-pdf.ini
