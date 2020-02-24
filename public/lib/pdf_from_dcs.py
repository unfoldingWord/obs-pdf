#!/usr/bin/python3

from typing import List, Tuple, Union
import codecs
import datetime
import re
import shutil
import subprocess
import time
import os
from os.path import isfile, isdir
import traceback

from lib.general_tools.app_utils import get_output_dir, get_resources_dir
from lib.general_tools.file_utils import make_dir, unzip, load_yaml_object, read_file, write_file, remove_tree
from lib.general_tools.url_utils import get_catalog, download_file
from lib.aws_tools.s3_handler import S3Handler

from lib.obs.obs_classes import OBSChapter, OBS, OBSError
from lib.obs.obs_tex_export import OBSTexExport



AWS_REGION_NAME = 'us-west-2'
CDN_BUCKET_NAME = 'cdn.door43.org'
OLD_CDN_FOLDER = 'obs/auto_PDFs' # Folder inside the CDN bucket
# OLD_CDN_FOLDER = 'tx/job/auto_PDFs' # Folder inside the CDN bucket -- this one has 1-DAY AUTODELETE
DOOR43_SITE_URL = 'https://git.door43.org'



class PdfFromDcs:
    """
    Called from Flask after accepting payload.
    """

    def __init__(self, prefix:str, parameter_type:str, parameter:Union[str,Tuple[str,str,str],Tuple[str,str,str,str]]) -> None:
        """
        prefix is '' or 'dev-'

        parameter_type is either
            'Catalog_lang_code' where a language code (e.g., 'en' or 'es-419' is given)
            or
            'Door43_repo' where a repo username/repoName is given
            or
            'username_repoName_spec' where three or four parameters are given.

        parameter is the string value itself or a tuple with the three or four strings.
        """
        assert prefix in ('','dev-')
        assert parameter_type in ('Catalog_lang_code','Door43_repo','username_repoName_spec')
        assert len(parameter) in (1,3,4)

        self.prefix = prefix
        self.parameter_type = parameter_type
        self.parameter = parameter
        self.output_msgs = ''
        self.output_msg_filepath = '/tmp/last_output_msgs.txt'

        self.prefixed_bucket_name = f'{self.prefix}{CDN_BUCKET_NAME}'

        self.output_msg(f"{datetime.datetime.now()} => Starting up with type={parameter_type} and parameter(s)={parameter}…\n")
        self.lang_code = self.given_repo_spec = self.commit_hash = None
        self.extended_description = None
        if self.parameter_type == 'Catalog_lang_code':
            assert isinstance(parameter, str)
            self.lang_code = parameter
            self.cdn_folder = OLD_CDN_FOLDER
            self.description = f'D43 Catalog {self.lang_code}'
            self.filename_bit = parameter
        elif self.parameter_type == 'Door43_repo':
            assert isinstance(parameter, str)
            self.given_repo_spec = parameter.strip('/')
            self.username, self.repo_name = self.given_repo_spec.split('/')
            self.cdn_folder = OLD_CDN_FOLDER
            self.description = self.given_repo_spec
            self.filename_bit = self.given_repo_spec.replace('/','--')
        elif self.parameter_type == 'username_repoName_spec':
            assert isinstance(parameter, (tuple, list))
            if len(parameter) == 3:
                self.username, self.repo_name, self.repo_spec = parameter
                self.description = f'{self.username}/{self.repo_name}--{self.repo_spec}'
                self.filename_bit = f'{self.username}--{self.repo_name}--{self.repo_spec}'
            elif len(parameter) == 4:
                self.username, self.repo_name, self.repo_spec, self.commit_hash = parameter
                self.description = f'{self.username}/{self.repo_name}'
                self.extended_description = f'{self.repo_spec}--{self.commit_hash}'
                self.filename_bit = f'{self.username}--{self.repo_name}--{self.repo_spec}'
            self.cdn_folder = f'u/{self.username}/{self.repo_name}/{self.repo_spec}'
        else:
            err_msg = f"Unrecognized parameter type: '{self.parameter_type}'\n"
            print(f"ERROR: {err_msg}")
            self.output_msg(err_msg)
            raise TypeError
        self.tmp_download_dirpath = f"/tmp/obs-to-pdf/{self.filename_bit}--{int(time.time())}/"

        # AWS credentials -- get the secret ones from environment variables
        try:
            self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
            self.aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        except Exception as e:
            err_msg = f"Exception in __init__: {e}: {traceback.format_exc()}\n"
            # print(f"ERROR: {err_msg}")
            self.output_msg(err_msg)
            raise e
    # end of PdfFromDcs.init function


    def __enter__(self):
        return self


    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


    def output_msg(self, msg:str) -> None:
        """
        Outputs/Saves a message for debugging and/or showing status
        """
        print(msg)
        self.output_msgs += msg
        write_file(self.output_msg_filepath, self.output_msgs)


    def run(self) -> str:
        """
        Clean up left-over files from any previous runs.
        If a language code is given,
            download the uW Catalog and find the requested language.
        Or if a repo user/repo_name is given,
            skip that.
        Download the correct OBS zipped data.
            Unzip and check the OBS data.
        Call PdfFromDcs.create_and_upload_pdf function to make the PDF
        """
        self.output_msg(f"{datetime.datetime.now()} => Starting OBS PDF processing for {self.description}…\n")

        # Clean up left-over files from any previous runs
        self.cleanup_files()

        # Initialize some variables
        today = ''.join(str(datetime.date.today()).rsplit(str('-'))[0:3])  # str(datetime.date.today())
        # self.download_dir = '/tmp/obs-to-pdf/{0}-{1}'.format(self.lang_code, int(time.time()))
        make_dir(self.tmp_download_dirpath)

        if self.parameter_type == 'Catalog_lang_code':
            # Get the catalog
            self.output_msg(f"{datetime.datetime.now()} => Downloading the Door43 Catalog…\n")
            catalog = get_catalog()

            # Find the language we need
            langs = [l for l in catalog['languages'] if l['identifier'] == self.lang_code]  # type: dict

            if not langs:
                err_msg = f'Did not find "{self.lang_code}" in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            if len(langs) > 1:
                err_msg = f'Found more than one entry for "{self.lang_code}" in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            lang_info = langs[0]  # type: dict

            # 1. Get the zip file from the API
            resources = [r for r in lang_info['resources'] if r['identifier'] == 'obs']  # type: dict

            if not resources:
                err_msg = f'Did not find an entry for "{self.lang_code}" OBS in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            if len(resources) > 1:
                err_msg = f'Found more than one entry for "{self.lang_code}" OBS in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            resource = resources[0]  # type: dict

            found_sources = []

            for project in resource['projects']:
                if project['formats']:
                    urls = [f['url'] for f in project['formats']
                            if 'application/zip' in f['format'] and 'text/markdown' in f['format']]

                    if len(urls) > 1:
                        err_msg = f'Found more than one zipped markdown entry for "{self.lang_code}" OBS in the catalog.'
                        self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                        raise ValueError(err_msg)

                    if len(urls) == 1:
                        found_sources.append(urls[0])

            if not found_sources:
                err_msg = f'Did not find any zipped markdown entries for "{self.lang_code}" OBS in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            if len(found_sources) > 1:
                err_msg = f'Found more than one zipped markdown entry for "{self.lang_code}" OBS in the catalog.'
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ValueError(err_msg)

            source_zip_url = found_sources[0]
            tmp_source_dirpath = os.path.join(self.tmp_download_dirpath, f'{self.lang_code.lower()}_obs/')

        elif self.parameter_type == 'Door43_repo':
            source_zip_url = f'{DOOR43_SITE_URL}/{self.given_repo_spec}/archive/master.zip'
            tmp_source_dirpath = os.path.join(self.tmp_download_dirpath, self.repo_name)

        elif self.parameter_type == 'username_repoName_spec':
            source_zip_url = f'{DOOR43_SITE_URL}/{self.username}/{self.repo_name}/archive/{self.repo_spec}.zip'
            tmp_source_dirpath = os.path.join(self.tmp_download_dirpath, self.repo_name)


        # 2. Download source zip, then unzip
        self.output_msg(f"{datetime.datetime.now()} => Downloading '{source_zip_url}'…\n")
        downloaded_zip_tmp_filepath = f'{self.tmp_download_dirpath}/obs.zip'
        download_file(source_zip_url, downloaded_zip_tmp_filepath)
        unzip(downloaded_zip_tmp_filepath, self.tmp_download_dirpath)

        # 3. Check for valid repository structure
        manifest_filepath = os.path.join(tmp_source_dirpath, 'manifest.yaml')
        if not isfile(manifest_filepath):
            err_msg = "Did not find manifest.yaml in the resource container"
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise FileNotFoundError(err_msg)

        content_dirpath = os.path.join(tmp_source_dirpath, 'content/')
        if not isdir(content_dirpath):
            err_msg = "Did not find the content directory in the resource container"
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise NotADirectoryError(err_msg)

        # 4. Read the manifest (status, version, localized name, etc)
        self.output_msg(f"{datetime.datetime.now()} => Reading the {self.description} manifest…\n")
        manifest = load_yaml_object(manifest_filepath)

        # 5. Initialize OBS objects
        self.output_msg(f"{datetime.datetime.now()} => Initializing the OBS object…\n")
        obs_obj = OBS()
        obs_obj.date_modified = today
        obs_obj.language_id = manifest['dublin_core']['language']['identifier']
        obs_obj.language_name = manifest['dublin_core']['language']['title']
        obs_obj.language_direction = manifest['dublin_core']['language']['direction']
        obs_obj.version = manifest['dublin_core']['version']
        obs_obj.publisher = manifest['dublin_core']['publisher']
        obs_obj.description, obs_obj.extended_description = self.description, self.extended_description

        # 6. Import the chapter data
        self.output_msg(f"{datetime.datetime.now()} => Reading the {self.description} chapter files…\n")
        obs_obj.chapters = self.load_obs_chapters(content_dirpath)
        obs_obj.chapters.sort(key=lambda c: int(c['number']))

        self.output_msg(f"{datetime.datetime.now()} => Verifying the chapter data…\n")
        if not obs_obj.verify_all():
            err_msg = "Quality check did not pass."
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise OBSError(err_msg)

        # 7. Front and back matter
        self.output_msg(f"{datetime.datetime.now()} => Reading the front and back matter…\n")
        title_filepath = os.path.join(content_dirpath, 'front', 'title.md')
        if not isfile(title_filepath):
            err_msg = "Did not find the title file in the resource container"
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise OBSError(err_msg)
        obs_obj.title = read_file(title_filepath)

        front_filepath = os.path.join(content_dirpath, 'front', 'intro.md')
        if not isfile(front_filepath):
            err_msg = "Did not find the front/intro.md file in the resource container"
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise OBSError(err_msg)
        obs_obj.front_matter = self.remove_trailing_hashes(read_file(front_filepath), 'front-matter')

        back_filepath = os.path.join(content_dirpath, 'back', 'intro.md')
        if not isfile(back_filepath):
            err_msg = "Did not find the back/intro.md file in the resource container"
            self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
            raise OBSError(err_msg)
        obs_obj.back_matter = self.remove_trailing_hashes(read_file(back_filepath), 'back-matter')

        return self.create_and_upload_pdf(obs_obj) # Should return upload URL
    # end of PdfFromDcs.run()


    def create_and_upload_pdf(self, obs_obj:OBS) -> str:
        """
        Called from PdfFromDcs.run() above.

        Creates the PDF via ConTeXt and returns the full path to the finished file
        :param obs_obj: OBS
        :return: S3 uploaded URL
        """
        self.output_msg(f"{datetime.datetime.now()} => Beginning {self.description} PDF generation…\n")

        out_dirpath = os.path.join(self.tmp_download_dirpath, 'make_pdf/')
        make_dir(out_dirpath)

        obs_language_id = obs_obj.language_id
        self.output_msg(f"    obs_language_id = '{obs_language_id}'\n")

        have_exception = None
        try:
            # make sure the noto language file exists
            noto_filepath = os.path.join(get_resources_dir(), 'tex', 'noto-{0}.tex'.format(obs_language_id))
            if not isfile(noto_filepath):
                shutil.copy2(os.path.join(get_resources_dir(), 'tex', 'noto-en.tex'), noto_filepath)

            # generate a tex file
            tex_filepath = os.path.join(out_dirpath, f'{obs_language_id}.tex')
            self.output_msg(f"{datetime.datetime.now()} => Generating TeX file at {tex_filepath}…\n")
            if isfile(tex_filepath):
                os.remove(tex_filepath) # make sure it doesn't already exist

            with OBSTexExport(obs_obj=obs_obj, out_path=tex_filepath,
                                        max_chapters=0, img_res='360px') as tex:
                tex.run()

            # Run ConTeXt
            self.output_msg(f"{datetime.datetime.now()} => Preparing to run ConTeXt…\n")

            # noinspection PyTypeChecker
            trackers = ','.join(['afm.loading', 'fonts.missing', 'fonts.warnings', 'fonts.names',
                                 'fonts.specifications', 'fonts.scaling', 'system.dump'])

            # This command line has 3 parts:
            #   1. set the OSFONTDIR environment variable to the fonts directory where the noto fonts can be found
            #   2. run `mtxrun` to load the noto fonts so ConTeXt can find them
            #   3. run ConTeXt to generate the PDF
            cmd = 'export OSFONTDIR="/usr/share/fonts"' \
                  ' && mtxrun --script fonts --reload' \
                  f' && context --paranoid --nonstopmode --trackers={trackers} "{tex_filepath}"'

            # the output from the cmd will be dumped into these files
            out_log = os.path.join(get_output_dir(), 'context.out')
            if isfile(out_log):
                os.unlink(out_log)

            err_log_path = os.path.join(get_output_dir(), 'context.err')
            if isfile(err_log_path):
                os.unlink(err_log_path)

            self.output_msg(f"{datetime.datetime.now()} => Running ConTeXt -- this may take several minutes…\n")
            try:
                std_out = subprocess.check_output(cmd, shell=True,
                                                  stderr=subprocess.STDOUT, cwd=out_dirpath)
                self.output_msg(f"{datetime.datetime.now()} => Getting ConTeXt output…\n")
                std_out = re.sub(r'\n\n+', '\n', std_out.decode('utf-8', 'backslashreplace'), flags=re.MULTILINE)
                write_file(out_log, std_out)

                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)
                if err_lines:
                    write_file(err_log_path, '\n'.join(err_lines))
                    err_msg = f"Error lines were generated by ConTeXt. See {err_log_path}."
                    self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                    raise ChildProcessError(err_msg)

            except subprocess.CalledProcessError as e:
                self.output_msg(f"{datetime.datetime.now()} => ConTeXt process failed!\n")

                # find the tex error lines
                std_out = e.stdout.decode('utf-8', 'backslashreplace')
                std_out = re.sub(r'\n\n+', '\n', std_out, flags=re.MULTILINE)
                err_lines = re.findall(r'(^tex error.+)\n?', std_out, flags=re.MULTILINE)

                write_file(out_log, std_out)
                write_file(err_log_path, '\n'.join(err_lines))

                err_msg = f"Errors were generated by ConTeXt. See {err_log_path}."
                self.output_msg(f"{datetime.datetime.now()} ERROR: {err_msg}\n")
                raise ChildProcessError(err_msg)

        except Exception as e:
            err_msg = f"Exception in create_and_upload_pdf: {e}: {traceback.format_exc()}\n"
            print(f"ERROR: {err_msg}")
            self.output_msg(err_msg)
            # raise e
            err_msg = f"Supressing exception\n"
            # print(f"ERROR: {err_msg}")
            self.output_msg(err_msg)
            have_exception = e

        finally:
            self.output_msg(f"{datetime.datetime.now()} => Exiting ConTeXt PDF generation code…\n")
            # with open(, 'wt') as log_output_file:
                # log_output_file.write(self.output)

        # PDF file is in out_dirpath
        pdf_current_filepath = os.path.join(out_dirpath, f'{obs_language_id}.pdf')
        self.output_msg(f"{datetime.datetime.now()} => Finding PDF at {pdf_current_filepath}…\n")
        # version = obs_obj.version.replace('.', '_')
        # if version[0:1] != 'v':
        #     version = f'v{version}'
        # # TODO: We might want to adjust this once things become more final
        # if self.parameter_type == 'Catalog_lang_code':
        #     pdf_desired_name = f'Door43-Catalog--{obs_language_id}_obs--{version}.pdf'
        # elif self.parameter_type == 'Door43_repo':
        #     pdf_desired_name = f'{self.username}--{self.repo_name}--{version}.pdf'
        # elif self.parameter_type == 'username_repoName_spec':
        #     pdf_desired_name = f'{self.username}--{self.repo_name}--{self.repo_spec}.pdf'
        pdf_desired_name = f'{self.filename_bit}.pdf'

        # Copy the new PDF file to the /app/obs-pdf/output/{obs_lang_code}/ folder
        # self.output_msg(f"{datetime.datetime.now()} => Copying the '{obs_lang_code}' PDF file to output directory…\n")
        # output_dir = os.path.join(get_output_dir(), obs_lang_code)
        # if not isdir(output_dir):
        #     make_dir(output_dir, linux_mode=0o777, error_if_not_writable=True)
        # pdf_destination_filepath = os.path.join(output_dir, pdf_desired_name)
        # self.output_msg(f"  Copying {pdf_current_filepath} to {pdf_destination_filepath}…\n")
        # shutil.copyfile(pdf_current_filepath, pdf_destination_filepath)

        # Upload the PDF to our AWS S3 bucket
        self.output_msg(f"{datetime.datetime.now()} => Uploading '{pdf_desired_name}' to S3 {self.prefixed_bucket_name}/{self.cdn_folder}…\n")
        cdn_s3_handler = S3Handler(bucket_name=self.prefixed_bucket_name,
                                    aws_access_key_id=self.aws_access_key_id,
                                    aws_secret_access_key=self.aws_secret_access_key,
                                    aws_region_name=AWS_REGION_NAME)
        s3_commit_key = f'{self.cdn_folder}/{pdf_desired_name}'
        cdn_s3_handler.upload_file(pdf_current_filepath, s3_commit_key)

        # return pdf link
        self.output_msg(f"Should be viewable at https://{self.prefixed_bucket_name}/{s3_commit_key}.\n")
        if have_exception is None:
            return f'https://{self.prefixed_bucket_name}/{s3_commit_key}'
        return str(have_exception)
        # raise have_exception
    # end of PdfFromDcs.create_and_upload_pdf function


    @staticmethod
    def remove_trailing_hashes(given_text: str, optional_description=None) -> str:
        """
        Adjust markdown text to remove any trailing hashes (they irritate ConTeXt)
        """
        adjusted_description = f'{optional_description} ' if optional_description else ''
        new_lines = []
        for line in given_text.split('\n'):
            new_line = line.rstrip(' #') # Strips all of these characters at the end of the line
            if new_line != line:
                print(f"Stripped {adjusted_description}line '{line}' to '{new_line}'")
            new_lines.append(new_line)
        return '\n'.join(new_lines)
    # end of PdfFromDcs.remove_trailing_hashes static function


    @staticmethod
    def cleanup_files():
        """
        In order to keep running in a Docker container,
            we don't want to accumulate left-over files

        We leave /tmp/last_output_msgs.txt (and of course, /tmp/uwsgi.sock).
        """
        remove_tree('/app/obs-pdf/output/')
        remove_tree('/tmp/obs-to-pdf/')
    # end of PdfFromDcs.cleanup_files() static function


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
