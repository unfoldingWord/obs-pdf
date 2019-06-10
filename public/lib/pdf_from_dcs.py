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



class PdfFromDcs:

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.download_dir = f'/tmp/obs-to-pdf/{lang_code}-{int(time.time())}'
        self.output = ''
        self.output_msg_filepath = '/tmp/last_output_msgs.txt'


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
        downloaded_file = f'{self.download_dir}/obs.zip'

        # get the catalog
        self.output += f"{datetime.datetime.now()} => Downloading the catalog.\n"
        write_file(self.output_msg_filepath, self.output)
        catalog = get_catalog()

        # find the language we need
        langs = [l for l in catalog['languages'] if l['identifier'] == self.lang_code]  # type: dict

        if len(langs) == 0:
            raise ValueError(f'Did not find "{self.lang_code}" in the catalog.')

        if len(langs) > 1:
            raise ValueError(f'Found more than one entry for "{self.lang_code}" in the catalog.')

        lang_info = langs[0]  # type: dict

        # 1. Get the zip file from the API
        resources = [r for r in lang_info['resources'] if r['identifier'] == 'obs']  # type: dict

        if len(resources) == 0:
            raise ValueError(f'Did not find an entry for "{self.lang_code}" OBS in the catalog.')

        if len(resources) > 1:
            raise ValueError(f'Found more than one entry for "{self.lang_code}" OBS in the catalog.')

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
        self.output += f"{datetime.datetime.now()} => Reading the manifest.\n"
        write_file(self.output_msg_filepath, self.output)
        manifest = load_yaml_object(manifest_file)

        # 5. Initialize OBS objects
        self.output += f"{datetime.datetime.now()} => Initializing the OBS object.\n"
        write_file(self.output_msg_filepath, self.output)
        lang = manifest['dublin_core']['language']['identifier']
        obs_obj = OBS()
        obs_obj.date_modified = today
        obs_obj.direction = manifest['dublin_core']['language']['direction']
        obs_obj.language = lang
        obs_obj.version = manifest['dublin_core']['version']
        obs_obj.checking_level = manifest['checking']['checking_level']

        # 6. Import the chapter data
        self.output += f"{datetime.datetime.now()} => Reading the chapter files.\n"
        write_file(self.output_msg_filepath, self.output)
        obs_obj.chapters = self.load_obs_chapters(content_dir)
        obs_obj.chapters.sort(key=lambda c: int(c['number']))

        self.output += f"{datetime.datetime.now()} => Verifying the chapter data.\n"
        write_file(self.output_msg_filepath, self.output)
        if not obs_obj.verify_all():
            raise OBSError('Quality check did not pass.')

        # 7. Front and back matter
        self.output += f"{datetime.datetime.now()} => Reading the front and back matter.\n"
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
            self.output += f"{datetime.datetime.now()} => Beginning PDF generation.\n"
            write_file(self.output_msg_filepath, self.output)

            out_dir = os.path.join(self.download_dir, 'make_pdf')
            make_dir(out_dir)

            obs_lang_code = obs_obj.language

            # make sure the noto language file exists
            noto_file = path.join(get_resources_dir(), 'tex', 'noto-{0}.tex'.format(obs_lang_code))
            if not isfile(noto_file):
                shutil.copy2(path.join(get_resources_dir(), 'tex', 'noto-en.tex'), noto_file)

            # generate a tex file
            self.output += f"{datetime.datetime.now()} => Generating tex file.\n"
            write_file(self.output_msg_filepath, self.output)
            tex_file = os.path.join(out_dir, '{0}.tex'.format(obs_lang_code))

            # make sure it doesn't already exist
            if os.path.isfile(tex_file):
                os.remove(tex_file)

            with OBSTexExport(obs_obj, tex_file, 0, '360px') as tex:
                tex.run()

            # Run ConTeXt
            self.output += f"{datetime.datetime.now()} => Preparing to run ConTeXt.\n"
            write_file(self.output_msg_filepath, self.output)

            # noinspection PyTypeChecker
            trackers = ','.join(['afm.loading', 'fonts.missing', 'fonts.warnings', 'fonts.names',
                                 'fonts.specifications', 'fonts.scaling', 'system.dump'])

            # This command line has 3 parts:
            #   1. set the OSFONTDIR environment variable to the fonts directory where the noto fonts can be found
            #   2. run `mtxrun` to load the noto fonts so ConTeXt can find them
            #   3. run ConTeXt to generate the PDF
            cmd = 'export OSFONTDIR="/usr/share/fonts"' \
                  ' && mtxrun --script fonts --reload' \
                  f' && context --paranoid --nonstopmode --trackers={trackers} "{tex_file}"'

            # the output from the cmd will be dumped into these files
            out_log = os.path.join(get_output_dir(), 'context.out')
            if isfile(out_log):
                os.unlink(out_log)

            err_log_path = os.path.join(get_output_dir(), 'context.err')
            if isfile(err_log_path):
                os.unlink(err_log_path)

            self.output += f"{datetime.datetime.now()} => Running ConTeXt - this may take several minutes.\n"
            write_file(self.output_msg_filepath, self.output)
            try:
                std_out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=out_dir)
                self.output += f"{datetime.datetime.now()} => Getting ConTeXt output.\n"
                write_file(self.output_msg_filepath, self.output)
                std_out = re.sub(r'\n\n+', '\n', std_out.decode('utf-8'), flags=re.MULTILINE)
                write_file(out_log, std_out)

                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                if err_lines:
                    write_file(err_log_path, '\n'.join(err_lines))
                    raise ChildProcessError(f"Errors were generated by ConTeXt. See {err_log_path}.")

            except subprocess.CalledProcessError as e:
                self.output += f"{datetime.datetime.now()} => ConTeXt process failed!\n"
                write_file(self.output_msg_filepath, self.output)

                # find the tex error lines
                std_out = e.stdout.decode('utf-8')
                std_out = re.sub(r'\n\n+', '\n', std_out, flags=re.MULTILINE)
                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                write_file(out_log, std_out)
                write_file(err_log_path, '\n'.join(err_lines))

                raise ChildProcessError('Errors were generated by ConTeXt. See {}.'.format(err_log_path))

            self.output += f"{datetime.datetime.now()} => Copying the PDF file to output directory.\n"
            write_file(self.output_msg_filepath, self.output)
            version = obs_obj.version.replace('.', '_')
            if version[0:1] != 'v':
                version = 'v' + version

            output_dir = os.path.join(get_output_dir(), obs_lang_code)
            if not isdir(output_dir):
                make_dir(output_dir, linux_mode=0o777, error_if_not_writable=True)

            pdf_name = f'obs-{obs_lang_code}-{version}.pdf'
            pdf_file = os.path.join(output_dir, pdf_name)
            shutil.copyfile(os.path.join(out_dir, f'{obs_lang_code}.pdf'), pdf_file)

            return pdf_name

        finally:
            self.output += f"{datetime.datetime.now()} => Exiting PDF generation code...\n"
            write_file(self.output_msg_filepath, self.output)
            # with open(, 'wt') as log_output_file:
                # log_output_file.write(self.output)


    @staticmethod
    def load_obs_chapters(content_dir: str) -> List[OBSChapter]:
        chapters = []  # type: List[OBSChapter]

        for story_num in range(1, 51):
            chapter_num = str(story_num).zfill(2)
            story_file = os.path.join(content_dir, f'{chapter_num}.md')

            # get the translated chapter text
            with codecs.open(story_file, 'r', encoding='utf-8-sig') as in_file:
                obs_chapter = OBSChapter.from_markdown(in_file.read(), story_num)  # type: OBSChapter

            # sort the frames by id
            obs_chapter.frames.sort(key=lambda f: f['id'])

            # add this chapter to the OBS object
            chapters.append(obs_chapter)

        return chapters
