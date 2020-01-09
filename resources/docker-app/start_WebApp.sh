#! /usr/bin/env bash
set -e

# If there's a prestart.sh script in the /app directory, run it before starting
PRE_START_PATH=/app/prestart.sh
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    source $PRE_START_PATH
else
    echo "There is no script $PRE_START_PATH"
fi

# Start Supervisor, with Nginx and uWSGI
# Presumably the following line is to help it find /app/obs-pdf/public/uwsgi.ini
cd /app/obs-pdf/public
# The following line uses /etc/supervisor/conf.d/supervisord.conf
exec /usr/bin/supervisord
# Seems /etc/uwsgi/uwsgi.ini is also used.
