from typing import Callable
from contextlib import closing
import json
import shutil
import ssl
import sys
import urllib.request as urllib2
from urllib.error import HTTPError
import logging
from time import sleep


def get_url(url:str, catch_exception:bool=False):
    """
    :param str|unicode url: URL to open
    :param bool catch_exception: If <True> catches all exceptions and returns <False>
    """
    if catch_exception:

        # noinspection PyBroadException
        try:
            with closing(urllib2.urlopen(url)) as request:
                response = request.read()
        except Exception:
            response = False
    else:
        with closing(urllib2.urlopen(url)) as request:
            response = request.read()

    # convert bytes to str (Python 3.5)
    if type(response) is bytes:
        return response.decode('utf-8')
    else:
        return response


# def download_file(url:str, outfile:str) -> None:
#     """
#     Downloads a file and saves it.
#     """
#     try:
#         with closing(urllib2.urlopen(url)) as request:
#             with open(outfile, 'wb') as fp:
#                 shutil.copyfileobj(request, fp)

#     except IOError as err:
#         print('ERROR retrieving %s' % url)
#         print(err)
#         sys.exit(1)


def download_file(url:str, outfile:str) -> None:
    """Downloads a file and saves it."""
    _download_file(url, outfile, urlopen=urllib2.urlopen)


def _download_file(url:str, outfile:str, urlopen:Callable[[str],bytes]) -> None:
    """
    Handles "HTTP Error 503: Service Unavailable" internally with an automatic wait and retry.
    """
    logging.debug(f"_download_file( {url}, outfile={outfile}, …)…")
    MAX_TRIES = 5
    INITIAL_WAIT_TIME = 5 # seconds
    num_tries = 0
    while True:
        num_tries += 1
        if num_tries > 1:
            logging.debug(f"  _download_file try #{num_tries}…")
        need_to_wait = False
        # err:Optional[Exception] = None

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with closing(urlopen(url)) as request:
                with open(outfile, 'wb') as fp:
                    shutil.copyfileobj(request, fp)
        except HTTPError as e:
            if num_tries < MAX_TRIES \
            and "HTTP Error 503: Service Unavailable" in str(e):
                saved_e = e
                need_to_wait = True
            else:
                raise e
        except IOError as e:
            error_message = f"Error retrieving {url}: {e}"
            logging.critical(error_message)
            raise IOError(error_message)
        if not need_to_wait \
        or num_tries >= MAX_TRIES:
            break

        adjusted_wait_time = INITIAL_WAIT_TIME * num_tries # Make the wait progressively longer
        logging.warning(f"  _download_file: Waiting {adjusted_wait_time}s to fetch {url} after {saved_e}…")
        sleep(adjusted_wait_time) # Then try again
    # end of loop
# end of _download_file function


def get_languages() -> list:
    """
    Returns an array of over 7000 dictionaries

    Structure:
    [
      {
        cc: ["DJ", "US", "CA"],
        pk: 2,
        lr: "Africa",
        ln: "Afaraf",
        ang: "Afar",
        gw: false,
        ld: "ltr",
        alt: ["Afaraf", "Danakil"],
        lc: aa
      },
      …
    ]
    """
    url = 'http://td.unfoldingword.org/exports/langnames.json'
    return json.loads(get_url(url))


def get_catalog() -> list:
    """
    Returns the api v3 catalog
    """
    url = 'https://api.door43.org/v3/catalog.json'
    return json.loads(get_url(url))


def join_url_parts(*args):
    """
    Joins a list of segments into a URL-like string
    :type args: List<string>
    """
    # check for edge case
    if len(args) == 1:
        return args[0]

    return_val = clean_url_segment(args[0])

    for i in range(1, len(args)):
        arg = args[i]

        if i == len(args) - 1:
            # no need to remove a trailing slash if this is the last segment
            return_val += '/' + arg
        else:
            # remove a trailing slash so it won't be duplicated
            return_val += '/' + clean_url_segment(arg)

    return return_val


def clean_url_segment(segment:str):

    if segment[-1:] == '/':
        return segment[:-1]

    return segment
