import regex as re
from datetime import datetime
import os
from json import JSONEncoder
from typing import List

from lib.general_tools.file_utils import load_json_object
from lib.obs import chapters_and_frames



class OBSStatus:
    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a OBSStatus object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.checking_entity = ''
            self.checking_level = '1'
            self.comments = ''
            self.contributors = ''
            self.publish_date = datetime.today().strftime('%Y-%m-%d')
            self.source_text = 'en'
            self.source_text_version = ''
            self.version = ''


    def __contains__(self, item):
        return item in self.__dict__


    @staticmethod
    def from_manifest(manifest):
        status = OBSStatus()

        manifest_status = manifest['status']

        status.checking_entity = ', '.join(manifest_status['checking_entity'])
        status.checking_level = manifest_status['checking_level']
        status.comments = manifest_status['comments']
        status.contributors = ', '.join(manifest_status['contributors'])
        status.publish_date = manifest_status['pub_date']
        status.source_text = manifest_status['source_translations'][0]['language_slug']
        status.source_text_version = manifest_status['source_translations'][0]['version']
        status.version = manifest_status['version']

        return status



class OBSChapter:

    title_re = re.compile(r'^\s*#(.*?)#*\n')
    ref_re = re.compile(r'\n(_*.*?_*)\n*$')
    frame_re = re.compile(r'!\[OBS Image\].*?obs-en-(\d\d)-(\d\d)\.jpg.*?\)\n(.+?)(?=!\[|$)', re.DOTALL)
    img_url_template = 'https://cdn.door43.org/obs/jpg/360px/obs-en-{0}.jpg'


    def __init__(self, json_obj=None):
        """
        Class constructor. Optionally accepts an object for initialization.
        :param object json_obj: The name of a file to deserialize into a OBSStatus object
        """
        # deserialize
        if json_obj:
            self.__dict__ = json_obj  # type: dict

        else:
            self.frames = []  # type: List[dict]
            self.number = ''
            self.ref = ''
            self.title = ''


    def get_errors(self):
        """
        Checks this chapter for errors
        :returns list<str>
        """
        errors = []

        if not self.title:
            msg = 'Title not found: {0}'.format(self.number)
            print(msg)
            errors.append(msg)

        if not self.ref:
            msg = 'Ref not found: {0}'.format(self.number)
            print(msg)
            errors.append(msg)

        chapter_index = int(self.number) - 1

        # get the expected number of frames for this chapter
        expected_frame_count = chapters_and_frames.frame_counts[chapter_index]

        for x in range(1, expected_frame_count + 1):

            # frame id is formatted like '01-01'
            frame_id = '{0}-{1}'.format(self.number.zfill(2), str(x).zfill(2))

            # get the next frame
            frame = next((f for f in self.frames if f['id'] == frame_id), None)  # type: dict
            if not frame:
                msg = 'Frame not found: {0}'.format(frame_id)
                print(msg)
                errors.append(msg)
            else:
                # check the frame img and  values
                if 'img' not in frame or not frame['img']:
                    msg = 'Attribute "img" is missing for frame {0}'.format(frame_id)
                    print(msg)
                    errors.append(msg)

                if 'text' not in frame or not frame['text']:
                    msg = 'Attribute "text" is missing for frame {0}'.format(frame_id)
                    print(msg)
                    errors.append(msg)

        return errors


    def __getitem__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]


    def __str__(self):
        return self.__class__.__name__ + ' ' + self.number


    @staticmethod
    def from_markdown(markdown, chapter_number):
        """

        :param str|unicode markdown:
        :param int chapter_number:
        :return: OBSChapter
        """

        return_val = OBSChapter()
        return_val.number = str(chapter_number).zfill(2)

        # Remove Windows line endings
        markdown = markdown.replace('\r\n', '\n')


        # Title: the first non-blank line is title if it starts with '#'
        title_match = OBSChapter.title_re.search(markdown)
        if title_match:
            return_val.title = title_match.group(1).strip()
            markdown = markdown.replace(title_match.group(0), str(''), 1)

        # Ref
        ref_match = OBSChapter.ref_re.search(markdown)
        if ref_match:
            return_val.ref = ref_match.group(1).strip()
            markdown = markdown.replace(ref_match.group(0), str(''), 1)

        # Frames
        for frame_match in OBSChapter.frame_re.finditer(markdown):
            # 1: chapter number
            # 2: frame number
            # 3: frame text

            if int(frame_match.group(1)) != chapter_number:
                raise Exception(f"Expected chapter {chapter_number} but found {frame_match.group(1)}.")

            frame_id = '{0}-{1}'.format(frame_match.group(1), frame_match.group(2))

            frame_match = {'id': frame_id,
                    'img': OBSChapter.img_url_template.format(frame_id),
                    'text': frame_match.group(3).strip()
                    }

            return_val.frames.append(frame_match)

        return return_val



class OBS:

    def __init__(self, file_name=None):
        """
        Class constructor. Optionally accepts the name of a file to deserialize.
        :param str file_name: The name of a file to deserialize into a OBS object
        """
        # deserialize
        if file_name:
            if os.path.isfile(file_name):
                self.__dict__ = load_json_object(file_name)
            else:
                raise IOError('The file {0} was not found.'.format(file_name))
        else:
            self.app_words = dict(cancel='Cancel',
                                  chapters='Chapters',
                                  languages='Languages',
                                  next_chapter='Next Chapter',
                                  ok='OK',
                                  remove_locally='Remove Locally',
                                  remove_this_string='Remove this language from offline storage. You will need an '
                                                     'internet connection to view it in the future.',
                                  save_locally='Save Locally',
                                  save_this_string='Save this language locally for offline use.',
                                  select_a_language='Select a Language')
            self.chapters = []
            self.date_modified = datetime.today().strftime('%Y%m%d')
            self.direction = 'ltr'
            self.language = ''
            self.title = ''
            self.checking_level = ''
            self.version = ''
            self.status = ''
            self.front_matter = ''
            self.back_matter = ''


    def verify_all(self):

        errors = []

        for chapter in self.chapters:
            if type(chapter) is OBSChapter:
                obs_chapter = chapter
            else:
                obs_chapter = OBSChapter(chapter)
            errors = errors + obs_chapter.get_errors()

        if errors: return False
        # else:
        print('No errors were found in the OBS data.')
        return True



class OBSEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__



class OBSError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
