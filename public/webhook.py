# TX WEBHOOK
#
# NOTE: This module name and function name are defined by the rq package and our own tx-enqueue-job package
# This code adapted by RJH June 2018 from tx-manager/client_webhook/ClientWebhook/process_webhook

# NOTE: rq_settings.py is executed at program start-up, reads some environment variables, and sets queue name, etc.
#       job() function (at bottom here) is executed by rq package when there is an available entry in the named queue.

# Python imports
from typing import Dict, Tuple, Any, Optional
import os
import tempfile
import shutil
import json
from datetime import datetime, timedelta, date
from time import time
import sys
import traceback
import logging
from urllib.error import HTTPError

# Library (PyPi) imports
from rq import get_current_job, Queue
from statsd import StatsClient # Graphite front-end
from boto3 import Session # AWS S3 handler
from watchtower import CloudWatchLogHandler # AWS CloudWatch log handler

# Local imports
from rq_settings import prefix, debug_mode_flag, webhook_queue_name
from lib.aws_tools.s3_handler import S3Handler
from lib.general_tools.app_utils import get_output_dir
from lib.general_tools.file_utils import read_file, empty_folder, write_file
from lib.general_tools.url_utils import get_url
from lib.pdf_from_dcs import PdfFromDcs


# The following will be recording in the build log (JSON) file
MY_NAME = 'ConTeXt OBS PDF creator'
MY_VERSION_STRING = '1.00' # Mostly to determine PDF fixes
CDN_BUCKET_NAME = 'cdn.door43.org'
AWS_REGION_NAME = 'us-west-2'


if prefix not in ('', 'dev-'):
    logging.critical(f"Unexpected prefix: {prefix!r} -- expected '' or 'dev-'")
tx_stats_prefix = f"tx.{'dev' if prefix else 'prod'}"
job_handler_stats_prefix = f"{tx_stats_prefix}.job-handler"


# Credentials -- get the secret ones from environment variables
aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']

test_mode_flag = os.getenv('TEST_MODE', '')
travis_flag = os.getenv('TRAVIS_BRANCH', '')
log_group_name = f"{'' if test_mode_flag or travis_flag else prefix}tX" \
                    f"{'_DEBUG' if debug_mode_flag else ''}" \
                    f"{'_TEST' if test_mode_flag else ''}" \
                    f"{'_TravisCI' if travis_flag else ''}"


# Setup logging
logger = logging.getLogger(job_handler_stats_prefix)
boto3_session = Session(aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=AWS_REGION_NAME)
main_watchtower_log_handler = CloudWatchLogHandler(boto3_session=boto3_session,
                                            # use_queues=False, # Because this forked process is quite transient
                                            log_group=log_group_name,
                                            stream_name='tX-PDF-Job-Handler')
logger.addHandler(main_watchtower_log_handler)
logger.setLevel(logging.DEBUG if debug_mode_flag else logging.INFO)
# Change these loggers to only report errors:
logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)
logger.debug(f"Logging to AWS CloudWatch group '{log_group_name}' using key '…{aws_access_key_id[-2:]}'.")


# Get the Graphite URL from the environment, otherwise use a local test instance
graphite_url = os.getenv('GRAPHITE_HOSTNAME', 'localhost')
stats_client = StatsClient(host=graphite_url, port=8125)


def process_PDF_job(prefix:str, payload:Dict[str,Any]) -> str:
    """
    prefix may be '' or 'dev-'.
    payload is the dict passed to tX Enqueue Job as JSON.

    Expects an identifier in the payload of one of the two following forms:
        '<repo_owner_username>--<repo_name>--<tag_name>', or
        '<repo_owner_username>--<repo_name>--<branch_name>--commit_hash'.

    Returns a job description obtained from the payload.
    """
    logger.debug(f"process_PDF_job( {prefix}, {payload} ) {' (in debug mode)' if debug_mode_flag else ''}")
    assert payload['input_format'] == 'md'
    assert payload['output_format'] == 'pdf'
    assert payload['source'].startswith('https://git.door43.org/')
    assert payload['source'].count('/') == 6
    assert payload['source'].endswith('.zip')
                # e.g., 'https://git.door43.org/unfoldingWord/en_obs/archive/master.zip'
    assert payload['identifier'].count('--') in (2,3)

    parameters = payload['identifier'].split('--')
    assert len(parameters) in (3,4) # Commit hash is optional
    description = payload['identifier']

    repo_owner_username, repo_name, tag_or_branch_name = parameters[:3]

    # See if a JSON log file already exists
    base_download_url = f'https://s3-us-west-2.amazonaws.com/{prefix}cdn.door43.org'
    repo_part = f'u/{repo_owner_username}/{repo_name}'
    filename_part = 'PDF_details.json'
    json_url = f'{base_download_url}/{repo_part}/{filename_part}'
    logger.info(f"Checking for JSON build log at {json_url}…")
    try:
        PDF_log_dict = json.loads(get_url(json_url))
    except HTTPError as e:
        logger.info(f"No existing build log to read: {e}")
        PDF_log_dict = {}
    except Exception as e:
        logger.error()
        PDF_log_dict = {f"Error when trying to read build log: {e}"}
    logger.info(f"Got previous build log = {PDF_log_dict}")

    if tag_or_branch_name not in PDF_log_dict: PDF_log_dict[tag_or_branch_name] = {}
    PDF_log_dict[tag_or_branch_name]['PDF_creator'] = MY_NAME
    PDF_log_dict[tag_or_branch_name]['PDF_creator_version'] = MY_VERSION_STRING
    PDF_log_dict[tag_or_branch_name]['source_url'] = payload['source']

    logger.info(f"Calling PdfFromDcs('{prefix}', 'username_repoName_spec', {parameters})…")
    try:
        with PdfFromDcs(prefix, parameter_type='username_repoName_spec', parameter=parameters) as f:
            upload_URL = f.run()
            logger.info(f"PDF made and uploaded to {upload_URL}")
            # Update JSON log file
            PDF_log_dict[tag_or_branch_name]['status'] = 'success'
            PDF_log_dict[tag_or_branch_name]['PDF_url'] = upload_URL
            PDF_log_dict[tag_or_branch_name]['message'] = "PDF made and uploaded"
            if len(parameters) == 4:
                PDF_log_dict[tag_or_branch_name]['commit_hash'] = parameters[3]

    except ChildProcessError:
        logger.critical(f"ConTeXt went wrong: {e}")
        err_text = 'AN ERROR OCCURRED GENERATING THE PDF\r\n\r\n'
        err_text += read_file(os.path.join(get_output_dir(), 'context.err'))
        err_text += '\r\n\r\n\r\nFULL ConTeXt OUTPUT\r\n\r\n'
        err_text += read_file(os.path.join(get_output_dir(), 'context.out'))
        logger.critical(err_text)
        PDF_log_dict[tag_or_branch_name]['status'] = 'error'
        PDF_log_dict[tag_or_branch_name]['message'] = "Error within ConTeXt PDF build system"

    except Exception as e:
        logger.critical(f"Something went wrong: {e}")
        PDF_log_dict[tag_or_branch_name]['status'] = 'error'
        PDF_log_dict[tag_or_branch_name]['message'] = str(e)

    # Save (new/updated) JSON log file
    PDF_log_dict[tag_or_branch_name]['processed_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.info(f"Final build log = {PDF_log_dict}")
    log_filepath = f'/tmp/{filename_part}'
    write_file(log_filepath, PDF_log_dict)
    logger.info(f"Saving JSON build log to {json_url} …")
    cdn_s3_handler = S3Handler(bucket_name=f'{prefix}{CDN_BUCKET_NAME}',
                                aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key,
                                aws_region_name=AWS_REGION_NAME)
    s3_commit_key = f'{repo_part}/{filename_part}'
    cdn_s3_handler.upload_file(log_filepath, s3_commit_key, cache_time=2)

    return description
# end of process_PDF_job function


def job(queued_json_payload:Dict[str,Any]) -> None:
    """
    This function is called by the rq package to process a job in the queue(s).
        (Don't rename this function.)

    The job is removed from the queue before the job is started,
        but if the job throws an exception or times out (timeout specified in enqueue process)
            then the job gets added to the 'failed' queue.
    """
    logger.info(f"{MY_NAME} v{MY_VERSION_STRING}")
    logger.debug("tX PDF JobHandler received a job" + (" (in debug mode)" if debug_mode_flag else ""))
    start_time = time()
    stats_client.incr(f'{job_handler_stats_prefix}.jobs.OBSPDF.attempted')

    logger.info(f"Clearing /tmp folder…")
    empty_folder('/tmp/', only_prefix='tX_') # Stops failed jobs from accumulating in /tmp

    # logger.info(f"Updating queue statistics…")
    our_queue= Queue(webhook_queue_name, connection=get_current_job().connection)
    len_our_queue = len(our_queue) # Should normally sit at zero here
    # logger.debug(f"Queue '{webhook_queue_name}' length={len_our_queue}")
    stats_client.gauge(f'{tx_stats_prefix}.enqueue-job.queue.OBSPDF.length.current', len_our_queue)
    logger.info(f"Updated stats for '{tx_stats_prefix}.enqueue-job.queue.OBSPDF.length.current' to {len_our_queue}")

    # Save some stats
    stats_client.incr(f"{job_handler_stats_prefix}.jobs.OBSPDF.input.{queued_json_payload['input_format']}")
    stats_client.incr(f"{job_handler_stats_prefix}.jobs.OBSPDF.subject.{queued_json_payload['resource_type']}")

    try:
        job_descriptive_name = process_PDF_job(prefix, queued_json_payload)
    except Exception as e:
        # Catch most exceptions here so we can log them to CloudWatch
        prefixed_name = f"{prefix}tX_PDF_Job_Handler"
        logger.critical(f"{prefixed_name} threw an exception while processing: {queued_json_payload}")
        logger.critical(f"{e}: {traceback.format_exc()}")
        main_watchtower_log_handler.close() # Ensure queued logs are uploaded to AWS CloudWatch
        # Now attempt to log it to an additional, separate FAILED log
        logger2 = logging.getLogger(prefixed_name)
        log_group_name = f"FAILED_{'' if test_mode_flag or travis_flag else prefix}tX" \
                         f"{'_DEBUG' if debug_mode_flag else ''}" \
                         f"{'_TEST' if test_mode_flag else ''}" \
                         f"{'_TravisCI' if travis_flag else ''}"
        boto3_session = Session(aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key,
                            region_name='us-west-2')
        failure_watchtower_log_handler = CloudWatchLogHandler(boto3_session=boto3_session,
                                                    use_queues=False,
                                                    log_group=log_group_name,
                                                    stream_name=prefixed_name)
        logger2.addHandler(failure_watchtower_log_handler)
        logger2.setLevel(logging.DEBUG)
        logger2.info(f"Logging to AWS CloudWatch group '{log_group_name}' using key '…{aws_access_key_id[-2:]}'.")
        logger2.critical(f"{prefixed_name} threw an exception while processing: {queued_json_payload}")
        logger2.critical(f"{e}: {traceback.format_exc()}")
        failure_watchtower_log_handler.close()
        raise e # We raise the exception again so it goes into the failed queue

    elapsed_milliseconds = round((time() - start_time) * 1000)
    stats_client.timing(f'{job_handler_stats_prefix}.job.OBSPDF.duration', elapsed_milliseconds)
    if elapsed_milliseconds < 2000:
        logger.info(f"{prefix}tX job handling for {job_descriptive_name} PDF completed in {elapsed_milliseconds:,} milliseconds.")
    else:
        logger.info(f"{prefix}tX job handling for {job_descriptive_name} PDF completed in {round(time() - start_time)} seconds.")

    stats_client.incr(f'{job_handler_stats_prefix}.jobs.OBSPDF.completed')
    main_watchtower_log_handler.close() # Ensure queued logs are uploaded to AWS CloudWatch
# end of job function

# end of webhook.py for tX OBS PDF Job Handler
