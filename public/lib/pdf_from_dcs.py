#!/usr/bin/python3
import codecs
import datetime
import os
import re
import shutil
import subprocess
import time
from os import path
from os.path import isfile, isdir
from typing import List

from lib.general_tools.app_utils import get_output_dir, get_resources_dir
from lib.general_tools.file_utils import make_dir, unzip, load_yaml_object, read_file, write_file
from lib.general_tools.url_utils import get_catalog, download_file
from lib.obs.obs_classes import OBSChapter, OBS, OBSError
from lib.obs.obs_tex_export import OBSTexExport


class PdfFromDcs(object):

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.download_dir = '/tmp/obs-to-pdf/{0}-{1}'.format(lang_code, int(time.time()))
        self.output = ''

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self) -> str:

        # initialize some variables
        today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])  # str(datetime.date.today())
        self.download_dir = '/tmp/obs-to-pdf/{0}-{1}'.format(self.lang_code, int(time.time()))
        make_dir(self.download_dir)
        downloaded_file = '{0}/obs.zip'.format(self.download_dir)

        # get the catalog
        self.output += str(datetime.datetime.now()) + ' => Downloading the catalog.\n'
        catalog = get_catalog()

        # find the language we need
        langs = [l for l in catalog['languages'] if l['identifier'] == self.lang_code]  # type: dict

        if len(langs) == 0:
            raise ValueError('Did not find "{}" in the catalog.'.format(self.lang_code))

        if len(langs) > 1:
            raise ValueError('Found more than one entry for "{}" in the catalog.'.format(self.lang_code))

        lang_info = langs[0]  # type: dict

        # 1. Get the zip file from the API
        resources = [r for r in lang_info['resources'] if r['identifier'] == 'obs']  # type: dict

        if len(resources) == 0:
            raise ValueError('Did not find an entry for "{}" OBS in the catalog.'.format(self.lang_code))

        if len(resources) > 1:
            raise ValueError('Found more than one entry for "{}" OBS in the catalog.'.format(self.lang_code))

        resource = resources[0]  # type: dict

        found_sources = []

        for project in resource['projects']:
            if project['formats']:
                urls = [f['url'] for f in project['formats']
                        if 'application/zip' in f['format'] and 'text/markdown' in f['format']]

                if len(urls) > 1:
                    raise ValueError(
                        'Found more than one zipped markdown entry for "{}" OBS in the catalog.'.format(self.lang_code))

                if len(urls) == 1:
                    found_sources.append(urls[0])

        if len(found_sources) == 0:
            raise ValueError(
                'Did not find any zipped markdown entries for "{}" OBS in the catalog.'.format(self.lang_code))

        if len(found_sources) > 1:
            raise ValueError(
                'Found more than one zipped markdown entry for "{}" OBS in the catalog.'.format(self.lang_code))

        source_zip = found_sources[0]

        # 2. Unzip
        download_file(source_zip, downloaded_file)
        unzip(downloaded_file, self.download_dir)

        # 3. Check for valid repository structure
        source_dir = os.path.join(self.download_dir, '{}_obs'.format(self.lang_code))
        manifest_file = os.path.join(source_dir, 'manifest.yaml')
        if not isfile(manifest_file):
            raise FileNotFoundError('Did not find manifest.json in the resource container')

        content_dir = os.path.join(source_dir, 'content')
        if not isdir(content_dir):
            raise NotADirectoryError('Did not find the content directory in the resource container')

        # 4. Read the manifest (status, version, localized name, etc)
        self.output += str(datetime.datetime.now()) + ' => Reading the manifest.\n'
        manifest = load_yaml_object(manifest_file)

        # 5. Initialize OBS objects
        self.output += str(datetime.datetime.now()) + ' => Initializing the OBS object.\n'
        lang = manifest['dublin_core']['language']['identifier']
        obs_obj = OBS()
        obs_obj.date_modified = today
        obs_obj.direction = manifest['dublin_core']['language']['direction']
        obs_obj.language = lang
        obs_obj.version = manifest['dublin_core']['version']
        obs_obj.checking_level = manifest['checking']['checking_level']

        # 6. Import the chapter data
        self.output += str(datetime.datetime.now()) + ' => Reading the chapter files.\n'
        obs_obj.chapters = self.load_obs_chapters(content_dir)
        obs_obj.chapters.sort(key=lambda c: int(c['number']))

        self.output += str(datetime.datetime.now()) + ' => Verifying the chapter data.\n'
        if not obs_obj.verify_all():
            raise OBSError('Quality check did not pass.')

        # 7. Front and back matter
        self.output += str(datetime.datetime.now()) + ' => Reading the front and back matter.\n'
        title_file = os.path.join(content_dir, 'front', 'title.md')
        if not isfile(title_file):
            raise OBSError('Did not find the title file in the resource container')

        obs_obj.title = read_file(title_file)

        front_file = os.path.join(content_dir, 'front', 'intro.md')
        if not isfile(front_file):
            raise OBSError('Did not find the front/intro.md file in the resource container')

        obs_obj.front_matter = read_file(front_file)

        back_file = os.path.join(content_dir, 'back', 'intro.md')
        if not isfile(back_file):
            raise OBSError('Did not find the back/intro.md file in the resource container')

        obs_obj.back_matter = read_file(back_file)

        return self.create_pdf(obs_obj)

    def create_pdf(self, obs_obj: OBS) -> str:
        """
        Creates the PDF via ConTeXt and returns the full path to the finished file
        :param obs_obj: OBS
        :return: str
        """

        try:
            self.output += str(datetime.datetime.now()) + ' => Beginning PDF generation.\n'
            out_dir = os.path.join(self.download_dir, 'make_pdf')
            make_dir(out_dir)
            obs_lang_code = obs_obj.language

            # make sure the noto language file exists
            noto_file = path.join(get_resources_dir(), 'tex', 'noto-{0}.tex'.format(obs_lang_code))
            if not isfile(noto_file):
                shutil.copy2(path.join(get_resources_dir(), 'tex', 'noto-en.tex'), noto_file)

            # generate a tex file
            self.output += str(datetime.datetime.now()) + ' => Generating tex file.\n'
            tex_file = os.path.join(out_dir, '{0}.tex'.format(obs_lang_code))

            # make sure it doesn't already exist
            if os.path.isfile(tex_file):
                os.remove(tex_file)

            with OBSTexExport(obs_obj, tex_file, 0, '360px') as tex:
                tex.run()

            # run context
            self.output += str(datetime.datetime.now()) + ' => Running ConTeXt - this may take several minutes.\n'

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
                std_out = re.sub(r'\n\n+', '\n', std_out.decode('utf-8'), flags=re.MULTILINE)
                write_file(out_log, std_out)

                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                if err_lines:
                    write_file(err_log, '\n'.join(err_lines))
                    raise ChildProcessError('Errors were generated by ConTeXt. See {}.'.format(err_log))

            except subprocess.CalledProcessError as e:

                # find the tex error lines
                std_out = e.stdout.decode('utf-8')
                std_out = re.sub(r'\n\n+', '\n', std_out, flags=re.MULTILINE)
                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                write_file(out_log, std_out)
                write_file(err_log, '\n'.join(err_lines))

                raise ChildProcessError('Errors were generated by ConTeXt. See {}.'.format(err_log))

            self.output += str(datetime.datetime.now()) + ' => Copying the PDF file to output directory.\n'
            version = obs_obj.version.replace('.', '_')
            if version[0:1] != 'v':
                version = 'v' + version

            output_dir = os.path.join(get_output_dir(), obs_lang_code)
            if not isdir(output_dir):
                make_dir(output_dir, linux_mode=0o777, error_if_not_writable=True)

            pdf_file = os.path.join(output_dir, 'obs-{0}-{1}.pdf'.format(obs_lang_code, version))
            shutil.copyfile(os.path.join(out_dir, '{0}.pdf'.format(obs_lang_code)), pdf_file)

            return pdf_file

        finally:
            self.output += str(datetime.datetime.now()) + ' => Finished generating PDF.\n'

    @staticmethod
    def load_obs_chapters(content_dir: str) -> List[OBSChapter]:
        chapters = []  # type: List[OBSChapter]

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
