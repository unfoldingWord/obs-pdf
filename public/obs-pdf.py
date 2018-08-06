#!/usr/bin/python3
import os
from flask import Flask, request

from lib.pdf_from_dcs import PdfFromDcs

app = Flask(__name__)

project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# load the optional settings file, if it exists
config_file = os.path.join(project_dir, 'config', 'settings.ini')
if os.path.isfile(config_file):
    app.config.from_pyfile(config_file)


@app.route('/', methods=['POST', 'GET'])
def pdf_from_dcs():
    if request.method != 'GET':
        return 'Bad Request', 400

    lang_code = request.args.get('lang_code', '')
    if len(lang_code) == 0:
        return 'Bad Request - no lang_code', 400

    with PdfFromDcs(lang_code) as f:
        f.run()

    return lang_code


if __name__ == '__main__':
    app.run()
