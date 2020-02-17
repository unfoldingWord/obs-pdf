#!/usr/bin/python3

import os

from lib.general_tools.app_utils import get_output_dir
from lib.general_tools.file_utils import read_file
from lib.pdf_from_dcs import PdfFromDcs


prefix = os.getenv('QUEUE_PREFIX', '') # Gets (optional) QUEUE_PREFIX environment variable -- set to 'dev-' for development
assert prefix in ('','dev-')


username = 'unfoldingWord'
repo_name = 'en_obs'
tag_or_branch_name = 'master'
print(f"\n\nStarting to process OBS PDF request for Door43 '{username}'/'{repo_name}'--'{tag_or_branch_name}'…")
parameter_type = 'username_repoName_spec'

try:
    with PdfFromDcs(prefix, parameter_type, (username, repo_name, tag_or_branch_name)) as f:
        run_result = f.run()

except ChildProcessError:
    err_text = 'AN ERROR OCCURRED GENERATING THE PDF\n\n'
    err_text += read_file(os.path.join(get_output_dir(), 'context.err'))
    err_text += '\n\n\nFULL ConTeXt OUTPUT\n\n'
    err_text += read_file(os.path.join(get_output_dir(), 'context.out'))
    print(err_text)

except Exception as e: # all other exceptions
    print(f"Got an EXCEPTION: {e}") # Show exception string in console
