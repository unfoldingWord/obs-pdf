#! /usr/bin/env bash
set -e

# Start the Rq worker
cd /app/obs-pdf/public
#rq worker --config rq_settings --name tX_Dev_HTML_Job_Handler
rq worker --config rq_settings
