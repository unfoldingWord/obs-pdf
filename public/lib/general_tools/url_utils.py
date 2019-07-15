from contextlib import closing
import json
import shutil
import sys
import urllib.request as urllib2


def get_url(url, catch_exception=False):
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


def download_file(url, outfile):
    """
    Downloads a file and saves it.
    """
    try:
        with closing(urllib2.urlopen(url)) as request:
            with open(outfile, 'wb') as fp:
                shutil.copyfileobj(request, fp)

    except IOError as err:
        print('ERROR retrieving %s' % url)
        print(err)
        sys.exit(1)


def get_languages():
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


def get_catalog():
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


def clean_url_segment(segment):

    if segment[-1:] == '/':
        return segment[:-1]

    return segment
