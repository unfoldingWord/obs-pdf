#!/usr/bin/python3

import codecs
import datetime
import re
import shutil
import subprocess
import time
import os
from os import path
from os.path import isfile, isdir
from typing import List
import traceback

from lib.general_tools.app_utils import get_output_dir, get_resources_dir
from lib.general_tools.file_utils import make_dir, unzip, load_yaml_object, read_file, write_file, remove_tree
from lib.general_tools.url_utils import get_catalog, download_file
from lib.aws_tools.s3_handler import S3Handler

from lib.obs.obs_classes import OBSChapter, OBS, OBSError
from lib.obs.obs_tex_export import OBSTexExport



class PdfFromDcs:

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.download_dir = f'/tmp/obs-to-pdf/{lang_code}-{int(time.time())}'
        self.output_msg = ''
        self.output_msg_filepath = '/tmp/last_output_msgs.txt'

        # AWS credentials -- get the secret ones from environment variables
        self.cdn_bucket_name = 'cdn.door43.org'
        self.aws_region_name = 'us-west-2'
        try:
            self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
            self.aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        except Exception as e:
            err_msg = f"Exception in __init__: {e}: {traceback.format_exc()}\n"
            print(f"ERROR: {err_msg}")
            self.output_msg += err_msg
            write_file(self.output_msg_filepath, self.output_msg)
            raise e
    # end of PdfFromDcs.init function


    def __enter__(self):
        return self


    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


    def run(self) -> str:
        """
        Clean up left-over files from any previous runs.
        Download the uW Catalog and find the requested language.
        Download the correct OBS zipped data.
            Unzip and check the OBS data.
        Call PdfFromDcs.create_pdf function to make the PDF
        """
        # Clean up left-over files from any previous runs
        self.cleanup_files()

        # Initialize some variables
        today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])  # str(datetime.date.today())
        self.download_dir = '/tmp/obs-to-pdf/{0}-{1}'.format(self.lang_code, int(time.time()))
        make_dir(self.download_dir)
        downloaded_file = f'{self.download_dir}/obs.zip'

        # Get the catalog
        self.output_msg += f"{datetime.datetime.now()} => Downloading the catalog…\n"
        write_file(self.output_msg_filepath, self.output_msg)
        catalog = get_catalog()

        # Find the language we need
        langs = [l for l in catalog['languages'] if l['identifier'] == self.lang_code]  # type: dict

        if not langs:
            err_msg = f'Did not find "{self.lang_code}" in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        if len(langs) > 1:
            err_msg = f'Found more than one entry for "{self.lang_code}" in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        lang_info = langs[0]  # type: dict

        # 1. Get the zip file from the API
        resources = [r for r in lang_info['resources'] if r['identifier'] == 'obs']  # type: dict

        if not resources:
            err_msg = f'Did not find an entry for "{self.lang_code}" OBS in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        if len(resources) > 1:
            err_msg = f'Found more than one entry for "{self.lang_code}" OBS in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        resource = resources[0]  # type: dict

        found_sources = []

        for project in resource['projects']:
            if project['formats']:
                urls = [f['url'] for f in project['formats']
                        if 'application/zip' in f['format'] and 'text/markdown' in f['format']]

                if len(urls) > 1:
                    err_msg = f'Found more than one zipped markdown entry for "{self.lang_code}" OBS in the catalog.'
                    self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
                    write_file(self.output_msg_filepath, self.output_msg)
                    raise ValueError(err_msg)

                if len(urls) == 1:
                    found_sources.append(urls[0])

        if not found_sources:
            err_msg = f'Did not find any zipped markdown entries for "{self.lang_code}" OBS in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        if len(found_sources) > 1:
            err_msg = f'Found more than one zipped markdown entry for "{self.lang_code}" OBS in the catalog.'
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise ValueError(err_msg)

        source_zip = found_sources[0]

        # 2. Unzip
        download_file(source_zip, downloaded_file)
        unzip(downloaded_file, self.download_dir)

        # 3. Check for valid repository structure
        source_dir = os.path.join(self.download_dir, '{}_obs'.format(self.lang_code))
        manifest_file = os.path.join(source_dir, 'manifest.yaml')
        if not isfile(manifest_file):
            err_msg = "Did not find manifest.json in the resource container"
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise FileNotFoundError(err_msg)

        content_dir = os.path.join(source_dir, 'content')
        if not isdir(content_dir):
            err_msg = "Did not find the content directory in the resource container"
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise NotADirectoryError(err_msg)

        # 4. Read the manifest (status, version, localized name, etc)
        self.output_msg += f"{datetime.datetime.now()} => Reading the manifest…\n"
        write_file(self.output_msg_filepath, self.output_msg)
        manifest = load_yaml_object(manifest_file)

        # 5. Initialize OBS objects
        self.output_msg += f"{datetime.datetime.now()} => Initializing the OBS object…\n"
        write_file(self.output_msg_filepath, self.output_msg)
        lang = manifest['dublin_core']['language']['identifier']
        obs_obj = OBS()
        obs_obj.date_modified = today
        obs_obj.direction = manifest['dublin_core']['language']['direction']
        obs_obj.language = lang
        obs_obj.version = manifest['dublin_core']['version']
        obs_obj.checking_level = manifest['checking']['checking_level']

        # 6. Import the chapter data
        self.output_msg += f"{datetime.datetime.now()} => Reading the chapter files…\n"
        write_file(self.output_msg_filepath, self.output_msg)
        obs_obj.chapters = self.load_obs_chapters(content_dir)
        obs_obj.chapters.sort(key=lambda c: int(c['number']))

        self.output_msg += f"{datetime.datetime.now()} => Verifying the chapter data…\n"
        write_file(self.output_msg_filepath, self.output_msg)
        if not obs_obj.verify_all():
            err_msg = "Quality check did not pass."
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise OBSError(err_msg)

        # 7. Front and back matter
        self.output_msg += f"{datetime.datetime.now()} => Reading the front and back matter…\n"
        title_file = os.path.join(content_dir, 'front', 'title.md')
        if not isfile(title_file):
            err_msg = "Did not find the title file in the resource container"
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise OBSError(err_msg)

        obs_obj.title = read_file(title_file)

        front_file = os.path.join(content_dir, 'front', 'intro.md')
        if not isfile(front_file):
            err_msg = "Did not find the front/intro.md file in the resource container"
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise OBSError(err_msg)

        obs_obj.front_matter = read_file(front_file)

        back_file = os.path.join(content_dir, 'back', 'intro.md')
        if not isfile(back_file):
            err_msg = "Did not find the back/intro.md file in the resource container"
            self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
            write_file(self.output_msg_filepath, self.output_msg)
            raise OBSError(err_msg)

        obs_obj.back_matter = read_file(back_file)

        return self.create_pdf(obs_obj)
    # end of PdfFromDcs.run()


    def create_pdf(self, obs_obj: OBS) -> str:
        """
        Called from PdfFromDcs.run() above.

        Creates the PDF via ConTeXt and returns the full path to the finished file
        :param obs_obj: OBS
        :return: S3 uploaded URL
        """
        try:
            self.output_msg += f"{datetime.datetime.now()} => Beginning PDF generation…\n"
            write_file(self.output_msg_filepath, self.output_msg)

            out_dir = os.path.join(self.download_dir, 'make_pdf')
            make_dir(out_dir)

            obs_lang_code = obs_obj.language

            # make sure the noto language file exists
            noto_file = path.join(get_resources_dir(), 'tex', 'noto-{0}.tex'.format(obs_lang_code))
            if not isfile(noto_file):
                shutil.copy2(path.join(get_resources_dir(), 'tex', 'noto-en.tex'), noto_file)

            # generate a tex file
            self.output_msg += f"{datetime.datetime.now()} => Generating TeX file…\n"
            write_file(self.output_msg_filepath, self.output_msg)
            tex_file = os.path.join(out_dir, '{0}.tex'.format(obs_lang_code))

            # make sure it doesn't already exist
            if os.path.isfile(tex_file):
                os.remove(tex_file)

            with OBSTexExport(obs_obj, tex_file, 0, '360px') as tex:
                tex.run()

            # Run ConTeXt
            self.output_msg += f"{datetime.datetime.now()} => Preparing to run ConTeXt…\n"
            write_file(self.output_msg_filepath, self.output_msg)

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

            self.output_msg += f"{datetime.datetime.now()} => Running ConTeXt - this may take several minutes…\n"
            write_file(self.output_msg_filepath, self.output_msg)
            try:
                std_out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, cwd=out_dir)
                self.output_msg += f"{datetime.datetime.now()} => Getting ConTeXt output.\n"
                write_file(self.output_msg_filepath, self.output_msg)
                std_out = re.sub(r'\n\n+', '\n', std_out.decode('utf-8'), flags=re.MULTILINE)
                write_file(out_log, std_out)

                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                if err_lines:
                    write_file(err_log_path, '\n'.join(err_lines))
                    err_msg = f"Errors were generated by ConTeXt. See {err_log_path}."
                    self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
                    write_file(self.output_msg_filepath, self.output_msg)
                    raise ChildProcessError(err_msg)

            except subprocess.CalledProcessError as e:
                self.output_msg += f"{datetime.datetime.now()} => ConTeXt process failed!\n"
                write_file(self.output_msg_filepath, self.output_msg)

                # find the tex error lines
                std_out = e.stdout.decode('utf-8')
                std_out = re.sub(r'\n\n+', '\n', std_out, flags=re.MULTILINE)
                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                write_file(out_log, std_out)
                write_file(err_log_path, '\n'.join(err_lines))

                err_msg = f"Errors were generated by ConTeXt. See {err_log_path}."
                self.output_msg += f"{datetime.datetime.now()} ERROR: {err_msg}\n"
                write_file(self.output_msg_filepath, self.output_msg)
                raise ChildProcessError(err_msg)

            # PDF file is in out_dir
            pdf_current_filepath = os.path.join(out_dir, f'{obs_lang_code}.pdf')
            version = obs_obj.version.replace('.', '_')
            if version[0:1] != 'v':
                version = f'v{version}'
            pdf_desired_name = f'obs-{obs_lang_code}-{version}.pdf'

            # Copy the new PDF file to the /app/obs-pdf/output/{obs_lang_code}/ folder
            # self.output_msg += f"{datetime.datetime.now()} => Copying the '{obs_lang_code}' PDF file to output directory…\n"
            # write_file(self.output_msg_filepath, self.output_msg)
            # output_dir = os.path.join(get_output_dir(), obs_lang_code)
            # if not isdir(output_dir):
            #     make_dir(output_dir, linux_mode=0o777, error_if_not_writable=True)
            # pdf_destination_filepath = os.path.join(output_dir, pdf_desired_name)
            # self.output_msg += f"  Copying {pdf_current_filepath} to {pdf_destination_filepath}…\n"
            # write_file(self.output_msg_filepath, self.output_msg)
            # shutil.copyfile(pdf_current_filepath, pdf_destination_filepath)

            # Upload the PDF to our AWS S3 bucket
            self.output_msg += f"{datetime.datetime.now()} => Uploading the '{obs_lang_code}' PDF file to S3 bucket…\n"
            write_file(self.output_msg_filepath, self.output_msg)
            cdn_s3_handler = S3Handler(bucket_name=self.cdn_bucket_name,
                                       aws_access_key_id=self.aws_access_key_id,
                                       aws_secret_access_key=self.aws_secret_access_key,
                                       aws_region_name=self.aws_region_name)
            s3_commit_key = f'obs/auto_PDFs/{pdf_desired_name}'
            cdn_s3_handler.upload_file(pdf_current_filepath, s3_commit_key)

            # return pdf_desired_name
            return f'https://{self.cdn_bucket_name}/{s3_commit_key}'

        except Exception as e:
            err_msg = f"Exception in create_pdf: {e}: {traceback.format_exc()}\n"
            print(f"ERROR: {err_msg}")
            self.output_msg += err_msg
            write_file(self.output_msg_filepath, self.output_msg)
            raise e

        finally:
            self.output_msg += f"{datetime.datetime.now()} => Exiting PDF generation code.\n"
            write_file(self.output_msg_filepath, self.output_msg)
            # with open(, 'wt') as log_output_file:
                # log_output_file.write(self.output)
    # end of PdfFromDcs.create_pdf function


    def cleanup_files(self):
        """
        In order to keep running in a Docker container,
            we don't want to accumulate left-over files

        We leave /tmp/last_output_msgs.txt (and of course, /tmp/uwsgi.sock).
        """
        remove_tree('/app/obs-pdf/output/')
        remove_tree('/tmp/obs-to-pdf/')
    # end of PdfFromDcs.cleanup_files()


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
    # end of PdfFromDcs.load_obs_chapters static function
