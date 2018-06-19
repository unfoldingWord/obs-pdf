import argparse
import codecs
import regex as re
import shutil
import datetime
import subprocess
import time
from os import path
from os.path import isfile, isdir

from app.general_tools.app_utils import get_output_dir
from app.general_tools.file_utils import make_dir, unzip, load_yaml_object, read_file, write_file
from app.general_tools.print_utils import print_error, print_ok, print_notice
from app.general_tools.url_utils import download_file, get_catalog

import sys
import os

# remember this so we can delete it
from app.obs.obs_classes import OBS, OBSChapter
from app.obs.obs_tex_export import OBSTexExport

download_dir = ''


def main(lang_code):
    global download_dir

    # initialize some variables
    today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])  # str(datetime.date.today())
    download_dir = '/tmp/obs-to-pdf/{0}-{1}'.format(lang_code, int(time.time()))
    make_dir(download_dir)
    downloaded_file = '{0}/obs.zip'.format(download_dir)

    # get the catalog
    print('Downloading the catalog...', end=' ')
    catalog = get_catalog()
    print('finished')

    # find the language we need
    langs = [l for l in catalog['languages'] if l['identifier'] == lang_code]  # type: dict

    if len(langs) == 0:
        print_error('Did not find "{}" in the catalog.'.format(lang_code))
        sys.exit(1)

    if len(langs) > 1:
        print_error('Found more than one entry for "{}" in the catalog.'.format(lang_code))
        sys.exit(1)

    lang_info = langs[0]  # type: dict

    # 1. Get the zip file from the API
    resources = [r for r in lang_info['resources'] if r['identifier'] == 'obs']  # type: dict

    if len(resources) == 0:
        print_error('Did not find an entry for "{}" OBS in the catalog.'.format(lang_code))
        sys.exit(1)

    if len(resources) > 1:
        print_error('Found more than one entry for "{}" OBS in the catalog.'.format(lang_code))
        sys.exit(1)

    resource = resources[0]  # type: dict

    found_sources = []

    for project in resource['projects']:
        if project['formats']:
            urls = [f['url'] for f in project['formats']
                    if 'application/zip' in f['format'] and 'text/markdown' in f['format']]

            if len(urls) > 1:
                print_error('Found more than one zipped markdown entry for "{}" OBS in the catalog.'.format(lang_code))
                sys.exit(1)

            if len(urls) == 1:
                found_sources.append(urls[0])

    if len(found_sources) == 0:
        print_error('Did not find any zipped markdown entries for "{}" OBS in the catalog.'.format(lang_code))
        sys.exit(1)

    if len(found_sources) > 1:
        print_error('Found more than one zipped markdown entry for "{}" OBS in the catalog.'.format(lang_code))
        sys.exit(1)

    source_zip = found_sources[0]

    # 2. Unzip
    download_file(source_zip, downloaded_file)
    unzip(downloaded_file, download_dir)

    # 3. Check for valid repository structure
    source_dir = path.join(download_dir, '{}_obs'.format(lang_code))
    manifest_file = path.join(source_dir, 'manifest.yaml')
    if not isfile(manifest_file):
        print_error('Did not find manifest.json in the resource container')
        sys.exit(1)

    content_dir = path.join(source_dir, 'content')
    if not isdir(content_dir):
        print_error('Did not find the content directory in the resource container')
        sys.exit(1)

    # 4. Read the manifest (status, version, localized name, etc)
    print('Reading the manifest...', end=' ')
    manifest = load_yaml_object(manifest_file)
    print('finished')

    # 5. Initialize OBS objects
    print('Initializing the OBS object...', end=' ')
    lang = manifest['dublin_core']['language']['identifier']
    obs_obj = OBS()
    obs_obj.date_modified = today
    obs_obj.direction = manifest['dublin_core']['language']['direction']
    obs_obj.language = lang
    obs_obj.version = manifest['dublin_core']['version']
    obs_obj.checking_level = manifest['checking']['checking_level']
    print('finished')

    # 6. Import the chapter data
    print('Reading the chapter files...', end=' ')
    obs_obj.chapters = load_obs_chapters(content_dir)
    obs_obj.chapters.sort(key=lambda c: int(c['number']))
    print('finished')

    print('Verifying the chapter data...', end=' ')
    if not obs_obj.verify_all():
        print_error('Quality check did not pass.')
        sys.exit(1)
    print('finished')

    # 7. Front and back matter
    print('Reading the front and back matter...', end=' ')
    title_file = path.join(content_dir, 'front', 'title.md')
    if not isfile(title_file):
        print_error('Did not find the title file in the resource container')
        sys.exit(1)
    obs_obj.title = read_file(title_file)

    front_file = path.join(content_dir, 'front', 'intro.md')
    if not isfile(front_file):
        print_error('Did not find the front/intro.md file in the resource container')
        sys.exit(1)
    obs_obj.front_matter = read_file(front_file)

    back_file = path.join(content_dir, 'back', 'intro.md')
    if not isfile(back_file):
        print_error('Did not find the back/intro.md file in the resource container')
        sys.exit(1)
    obs_obj.back_matter = read_file(back_file)

    print('finished')

    create_pdf(obs_obj)


def create_pdf(obs_obj):
    """

    :type obs_obj: OBS
    """
    global download_dir

    # Create PDF via ConTeXt
    try:
        print_ok('BEGINNING: ', 'PDF generation.')
        out_dir = os.path.join(download_dir, 'make_pdf')
        make_dir(out_dir)
        lang_code = obs_obj.language

        # generate a tex file
        print('Generating tex file...', end=' ')
        tex_file = os.path.join(out_dir, '{0}.tex'.format(lang_code))

        # make sure it doesn't already exist
        if os.path.isfile(tex_file):
            os.remove(tex_file)

        with OBSTexExport(obs_obj, tex_file, 0, '360px') as tex:
            tex.run()
        print(str('finished.'))

        # run context
        print_notice('Running ConTeXt - this may take several minutes.')

        # noinspection PyTypeChecker
        trackers = ','.join(['afm.loading', 'fonts.missing', 'fonts.warnings', 'fonts.names',
                             'fonts.specifications', 'fonts.scaling', 'system.dump'])

        # this command line has 3 parts:
        #   1. set the OSFONTDIR environment variable to the fonts directory where the noto fonts can be found
        #   2. run `mtxrun` to load the noto fonts so ConTeXt can find them
        #   3. run ConTeXt to generate the PDF
        cmd = 'export OSFONTDIR="/usr/share/fonts"' \
              ' && mtxrun --script fonts --reload' \
              ' && context --paranoid --batchmode --trackers={0} "{1}"'.format(trackers, tex_file)

        # the output from the cmd will be dumped into these files
        out_log = os.path.join(get_output_dir(), 'context.out')
        if isfile(out_log):
            os.unlink(out_log)

        err_log = os.path.join(get_output_dir(), 'context.err')
        if isfile(err_log):
            os.unlink(err_log)

        try:
            std_out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=out_dir)
            std_out = re.sub(r'\n\n+', '\n', std_out.decode(sys.getfilesystemencoding()), flags=re.MULTILINE)
            write_file(out_log, std_out)

            err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

            if err_lines:
                write_file(err_log, '\n'.join(err_lines))
                print_error('Errors were generated by ConTeXt. See {}.'.format(err_log))
                sys.exit(1)

        except subprocess.CalledProcessError as e:

            # find the tex error lines
            std_out = e.stdout.decode(sys.getfilesystemencoding())
            std_out = re.sub(r'\n\n+', '\n', std_out, flags=re.MULTILINE)
            err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

            write_file(out_log, std_out)
            write_file(err_log, '\n'.join(err_lines))

            print_error('Errors were generated by ConTeXt. See {}.'.format(err_log))
            sys.exit(1)

        print('Finished running context.')

        print('Copying PDF to API...', end=' ')
        version = obs_obj.version.replace('.', '_')
        if version[0:1] != 'v':
            version = 'v' + version

        output_dir = os.path.join(get_output_dir(), lang_code)
        if not isdir(output_dir):
            make_dir(output_dir, linux_mode=0o777, error_if_not_writable=True)

        pdf_file = os.path.join(output_dir, 'obs-{0}-{1}.pdf'.format(lang_code, version))
        shutil.copyfile(os.path.join(out_dir, '{0}.pdf'.format(lang_code)), pdf_file)
        print('finished.')

    finally:
        print_ok('FINISHED:', 'generating PDF.')


def load_obs_chapters(content_dir):
    chapters = []

    for story_num in range(1, 51):
        chapter_num = str(story_num).zfill(2)
        story_file = os.path.join(content_dir, '{0}.md'.format(chapter_num))

        # get the translated chapter text
        with codecs.open(story_file, 'r', encoding='utf-8-sig') as in_file:
            obs_chapter = OBSChapter.from_markdown(in_file.read(), story_num)  # type: OBSChapter

        # sort the frames by id
        obs_chapter.frames.sort(key=lambda f: f['id'])

        # add this chapter to the OBS object
        chapters.append(obs_chapter)

    return chapters


if __name__ == '__main__':
    print('')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--lang-code', dest='lang_code', default='en',
                        required=True, help='The language code to process in https://api.door43.org/v3/catalog.json.')

    args = parser.parse_args(sys.argv[1:])

    print_ok('STARTING: ', 'publishing OBS as PDF.')
    main(args.lang_code)
    print_ok('ALL FINISHED: ', 'publishing OBS as PDF.')
    print_notice('Don\'t forget to notify the interested parties.')
