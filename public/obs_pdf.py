#!/usr/bin/python3

import os

from flask import Flask, request, send_from_directory, Response, redirect

from lib.general_tools.app_utils import get_output_dir
from lib.general_tools.file_utils import read_file
from lib.pdf_from_dcs import PdfFromDcs


app = Flask(__name__)

project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Load the optional settings file, if it exists
config_file = os.path.join(project_dir, 'config', 'settings.ini')
if os.path.isfile(config_file):
    app.config.from_pyfile(config_file)



@app.route('/', methods=['POST', 'GET'])
def pdf_from_dcs():
    if request.method != 'GET':
        return 'Bad Request', 400

    parameter = request.args.get('lang_code', '')
    if parameter:
        print(f"Starting to process OBS PDF request for Door43 Catalog language code '{parameter}'…")
        parameter_type = 'Catalog_lang_code'
    else:
        parameter = request.args.get('repo', '')
        if parameter:
            if parameter.strip('/').count('/') == 1:
                print(f"Starting to process OBS PDF request for Door43 repo '{parameter}'…")
                parameter_type = 'Door43_repo'
            else:
                return 'Bad Request - invalid Door43 repo specification', 400
        else: # can't find any valid parameter
            return 'Bad Request - no lang_code or repo', 400

    try:
        with PdfFromDcs(parameter_type, parameter) as f:
            run_result = f.run()

    except ChildProcessError:
        err_text = 'AN ERROR OCCURRED GENERATING THE PDF\r\n\r\n'
        err_text += read_file(os.path.join(get_output_dir(), 'context.err'))
        err_text += '\r\n\r\n\r\nFULL ConTeXt OUTPUT\r\n\r\n'
        err_text += read_file(os.path.join(get_output_dir(), 'context.out'))
        return Response(err_text, mimetype='text/plain')

    except Exception as e: # all other exceptions
        print(f"Got an EXCEPTION: {e}") # Show exception string in console
        return Response(str(e), mimetype='text/plain') # Return exception string to user

    # return redirect(f'/output/{lang_code}/{pdf_file}', code=302)
    if run_result: # it should be the URL of the file on S3
        return f'Success @ <a href="{run_result}">{run_result[8:]}</a>', 200
    # else:
    return 'PDF Build Error', 500
# end of pdf_from_dcs()



@app.route('/test', methods=['POST', 'GET'], strict_slashes=False)
def test_page():
    return send_from_directory(os.path.join(project_dir, 'static'), 'test_response.html')



if __name__ == '__main__':
    app.run()
