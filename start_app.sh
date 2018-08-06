#!/usr/bin/env bash

thisDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${thisDir}/public"

export FLASK_ENV=development
export FLASK_APP=obs-pdf.py
flask run --host=0.0.0.0
