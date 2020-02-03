# Python imports
import codecs
import os
import sys
from string import Template
import logging
import datetime

# PyPI imports
import regex as re

from lib.general_tools.app_utils import get_resources_dir
from lib.general_tools.file_utils import write_file
from lib.general_tools.url_utils import join_url_parts
from lib.obs.obs_classes import OBS



UW_OBS_LOGO_PATH = '/opt/obs/png/uW_OBS_Logo.png'
OBS_IMAGE_FOLDER_PATH = '/opt/obs/jpg/360px/'



class OBSTexExport:

    # region Class Settings
    api_url_jpg = '/opt/obs/jpg'
    snippets_dirpath = os.path.join(get_resources_dir(), 'tex/')

    MATCH_ALL = 0
    MATCH_ONE = 0

    # Create clickable URL links with \1 \1 or \1 \2, respectively
    clickableLink_re = r'{\\underbar{{\\goto{\1}[url(\1)]}}}'
    clickableTextLink_re = r'{\\underbar{{\\goto{\1}[url(\2)]}}}'

    # Docuwiki markdown patterns
    matchRemoveDummyTokenPattern = re.compile(r'===!!!===')
    matchSingleTokenPattern = re.compile(r'^\s*(\S+)\s*$')
    matchSectionPattern = re.compile(r'==+\s*(.*?)\s*==+')

    # Character emphasis
    matchTripleAsteriskPairs = re.compile(r'[*][*][*]\s*(.*?)\s*[*][*][*]')
    matchTripleUnderlinePairs = re.compile(r'[_][_][_]\s*(.*?)\s*[_][_][_]')
    matchDoubleAsteriskPairs = re.compile(r'(?=[^*]*)[*][*]\s*(.*?)\s*[*][*](?=[^*]*)')
    matchDoubleUnderlinePairs = re.compile(r'(?=[^_]*)[_][_]\s*(.*?)\s*[_][_](?=[^_]*)')
    matchSingleAsteriskPairs = re.compile(r'(?=[^*]*)[*]\s*(.*?)\s*[*](?=[^*]*)')
    matchSingleUnderlinePairs = re.compile(r'(?=[^_]*)[_]\s*(.*?)\s*[_](?=[^_]*)')
    # matchItalicPattern = re.compile(r'(?:\A|[^:])//\s*(.*?)\s*//')
    # markdownItalic_re = re.compile(r'(\A|\s+)[_]\s*(.*?)\s*[_](\Z|\s+)')
    # markdownBold_re = re.compile(r'(\A|\s+)[_][_]\s*(.*?)\s*[_][_](\Z|\s+)')
    # matchDoubleUnderlinePairs = re.compile(r'[^_]*__\s*(.*?)\s*__[^_]*')
    # matchSingleUnderlinePairs = re.compile(r'[^_]*_\s*(.*?)\s*_[^_]*')

    matchMonoPattern = re.compile(r'[\'][\']\s*(.*?)\s*[\'][\']')
    matchRedPattern = re.compile(r'<red>\s*(.*?)\s*</red>')
    matchMagentaPattern = re.compile(r'<mag[enta]*>\s*(.*?)\s*</mag[enta]*>')
    matchBluePattern = re.compile(r'<blue>\s*(.*?)\s*</blue>')
    matchGreenPattern = re.compile(r'<green>\s*(.*?)\s*</green>')
    matchHeadingFourLevelPattern = re.compile(r'(\A|[^=])====+\s*(.*?)\s*===+?([^=]|\Z)')
    matchHeadingThreeLevelPattern = re.compile(r'(\A|[^=])===+\s*(.*?)\s*==+?([^=]|\Z)')
    matchHeadingTwoLevelPattern = re.compile(r'(\A|[^=])==+\s*(.*?)\s*==+?([^=]|\Z)')
    matchHeadingOneLevelPattern = re.compile(r'(\A|[^=])=+\s*(.*?)\s*=+?([^=]|\Z)')

    # Markdown heading patterns
    markdownH1_re = re.compile(r'^(\s*)#\s*([^#]+[^\s])(\s*#)*([^#]|\Z)')
    markdownH2_re = re.compile(r'^(\s*)##\s*([^#]+[^\s])(\s*##)*([^#]|\Z)')
    markdownH3_re = re.compile(r'^(\s*)###\s*([^#]+[^\s])(\s*###)*([^#]|\Z)')
    markdownH4_re = re.compile(r'^(\s*)####\s*([^#]+[^\s])(\s*####)*([^#]|\Z)')

    markdownTextURL_re = re.compile(r'\[(.+?)\]\(((?:https://|http://)(?:[^\[\])]+))\)')
    markdownLongTextURL_re = re.compile(r'\[(.+?)\]\(((?:https://|http://)(?:[^\[\])]{41,}))\)')
    markdownURL_re = re.compile(r'(?<!([\[(]))https*://[^\s>]+')

    matchSubScriptPattern = re.compile(r'<sub>\s*(.*?)\s*</sub>')
    matchSuperScriptPattern = re.compile(r'<sup>\s*(.*?)\s*</sup>')
    matchStrikeOutPattern = re.compile(r'<del>\s*(.*?)\s*</del>')

    matchPipePattern = re.compile(r'(\|)')
    # DocuWiki markup patterns applied only to front and back matter
    matchBulletPattern = re.compile(r'^\s*[*]\s+(.*)$')
    # Miscellaneous markup patterns
    matchTitleLogoPattern = re.compile(r'===TITLE\.LOGO===') # TITLE.LOGO
    matchFrontMatterAboutPattern = re.compile(r'===FRONT\.MATTER\.ABOUT===') # FRONT.MATTER.ABOUT
    matchFrontMatterlicensePattern = re.compile(r'===FRONT\.MATTER\.LICENSE===') # FRONT.MATTER.LICENSE
    matchChaptersPattern = re.compile(r'===CHAPTERS===')
    matchBackMatterPattern = re.compile(r'===BACK\.MATTER===') # BACK.MATTER
    matchMiscPattern = re.compile(r'<<<[\[]([^<>=]+)[\]]>>>')
    # Other patterns
    NBSP = '~'  # non-breaking 1-en space
    NBKN = '\\,\\,\\,'  # Three kerns in a row, non-breaking space
    NBHY = '\u2012'  # non-breaking hyphen
    matchColonSemicolonNotAfterDigits = re.compile(r'([^\d\s])\s*([:;])\s*([^\s])')
    matchCommaBetweenDigits = re.compile(r'(\d)\s*([,])\s*(\d)')
    matchHyphen = re.compile(r'[-\u2010\u2012\u2013\uFE63]')
    matchHyphenEM = re.compile(r'[\u2014\uFE58]')
    matchAlphaNumSpaceThenNumber = re.compile(r'(\w)\s+(\d)')
    # matchAlphaNum = re.compile(r'[A-Za-z0-9]')
    matchSignificantTex = re.compile(r'[A-Za-z0-9\\{}\[\]]')
    matchBlankLinePattern = re.compile(r'^\s*$')

    matchOrdinalBookSpaces = re.compile(r'([123](|\.|\p{L}]{1,3}))\s')
    matchChapterVersePattern = re.compile(r'\s+(\d+:\d+)')

    # endregion


    def __init__(self, obs_obj:OBS, out_path:str, max_chapters:int, img_res:str) -> None:
        """

        """
        self.language_id = obs_obj.language_id
        self.language_name = obs_obj.language_name
        self.language_direction = obs_obj.language_direction
        self.out_path = out_path
        self.max_chapters = max_chapters
        self.img_res = img_res
        # self.version_number = obs_obj.version
        self.description = obs_obj.description
        # self.checking_level = obs_obj.checking_level
        self.title = obs_obj.title
        self.publisher = obs_obj.publisher
        self.front_matter = obs_obj.front_matter
        self.back_matter = obs_obj.back_matter
        self.body_json = {'chapters': obs_obj.chapters,
                          'language_id': self.language_id,
                          'language_direction': self.language_direction,
                        #   'checking_level': self.checking_level,
                          'toctitle': self.title}

        self.num_items = 0


    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


    def check_for_standard_keys_json(self) -> None:

        # ------------------------------  header/footer spacing and body font-face

        # At 72.27 pt/inch this is width of each figure
        if 'textwidth' not in self.body_json.keys():
            self.body_json['textwidth'] = '308.9pt'
        if 'topspace' not in self.body_json.keys():
            self.body_json['topspace'] = '28pt'  # nice for en,fr,es
        if 'botspace' not in self.body_json.keys():
            self.body_json['botspace'] = '28pt'  # nice for en,fr,es
        if 'fontface' not in self.body_json.keys():
            self.body_json['fontface'] = 'noto'

        # this is for production but does not seem to work for Russian
        if 'fontstyle' not in self.body_json.keys():
            self.body_json['fontstyle'] = 'sans'
        # if 'language_direction' not in self.body_json.keys():
        #     self.body_json['language_direction'] = 'ltr'  # Use 'rtl' for Arabic, Farsi, etc.

        # ------------------------------  Front/back font size and baseline
        if 'front_align' not in self.body_json.keys():
            self.body_json['front_align'] = 'flushleft'
        if 'back_align' not in self.body_json.keys():
            self.body_json['back_align'] = 'flushleft'

        # ------------------------------  Body font size and baseline
        if 'bodysize' not in self.body_json.keys():
            self.body_json['bodysize'] = '10.0pt'
        if 'bodybaseline' not in self.body_json.keys():
            self.body_json['bodybaseline'] = '12.0pt'
        if 'body_align' not in self.body_json.keys():
            self.body_json['body_align'] = 'width'

        # ------------------------------  Body font adjusted sizes
        if 'tfasize' not in self.body_json.keys():
            self.body_json['tfasize'] = '1.10'
        if 'tfbsize' not in self.body_json.keys():
            self.body_json['tfbsize'] = '1.20'
        if 'tfcsize' not in self.body_json.keys():
            self.body_json['tfcsize'] = '1.40'
        if 'tfdsize' not in self.body_json.keys():
            self.body_json['tfdsize'] = '1.60'
        if 'tfesize' not in self.body_json.keys():
            self.body_json['tfesize'] = '1.80'
        if 'tfxsize' not in self.body_json.keys():
            self.body_json['tfxsize'] = '0.9'
        if 'tfxxsize' not in self.body_json.keys():
            self.body_json['tfxxsize'] = '0.8'
        if 'smallsize' not in self.body_json.keys():
            self.body_json['smallsize'] = '0.80'

        # ------------------------------  Table-of-contents size, etc
        if 'tocsize' not in self.body_json.keys():
            self.body_json['tocsize'] = '12pt'
        if 'licsize' not in self.body_json.keys():
            self.body_json['licsize'] = '9pt'
        if 'tocbaseline' not in self.body_json.keys():
            self.body_json['tocbaseline'] = '16pt'
        if 'licbaseline' not in self.body_json.keys():
            self.body_json['licbaseline'] = '9pt'
        if 'tocperpage' not in self.body_json.keys():
            self.body_json['tocperpage'] = '26'
        # if 'checking_level' not in self.body_json.keys():
        #     self.body_json['checking_level'] = self.checking_level


    def another_replace(self, match_obj) -> str:
        keyword = match_obj.group(1)
        if keyword in self.body_json.keys():
            return self.body_json[keyword]
        adjusted_string = match_obj.string.lstrip() # Get rid of indent
        logger = logging.info if adjusted_string.startswith('%') \
                    else logging.error
        logger(f"Returning 'nothing' for '{keyword}' from '{adjusted_string}'")
        return 'nothing'


    def tex_load_snippet_file(self, xtr, entry_name) -> str:

        if not os.path.isdir(OBSTexExport.snippets_dirpath):
            raise IOError(f"Path not found: {OBSTexExport.snippets_dirpath}")

        with codecs.open(os.path.join(OBSTexExport.snippets_dirpath, entry_name), 'r', encoding='utf-8-sig') as in_file:
            each = in_file.readlines()

        each = each[1:]  # Skip the first line which is the utf-8 coding repeated
        return_val = ''.join(each)

        occurs = 1
        while occurs > 0:
            (return_val, occurs) = OBSTexExport.matchMiscPattern.subn(self.another_replace, return_val,
                                                                  OBSTexExport.MATCH_ALL)
        each = return_val.split('\n')
        while not OBSTexExport.matchSignificantTex.search(each[-1]):
            each.pop()
        return_val = xtr + ('\n' + xtr).join(each) + '\n'
        return return_val


    def get_title(self, text):
        return f"    \\startmakeup\\textdir {'TRT' if self.language_direction=='rtl' else 'TLT'}\\section{{{text}}}\\stopmakeup"


    @staticmethod
    def get_image(xtr:str, fid:str, res:str) -> str:
        img_link = join_url_parts(OBSTexExport.api_url_jpg, res, f'obs-{fid}.jpg')
        return xtr + xtr + xtr + '{{\\externalfigure[{0}][yscale={1}]}}'.format(img_link, 950)  # 950 = 95%


    @staticmethod
    def get_frame(xtr:str, tex_reg:str) -> str:
        xtr2 = xtr + xtr
        xtr3 = xtr + xtr + xtr

        return '\n'.join([
            xtr2 + '\\placefigure[nonumber]',
            xtr3 + '{{\\copy\\{0}}}'.format(tex_reg)
        ])


    @staticmethod
    def do_not_break_before_chapter_verse(text:str) -> str:
        copy = text
        copy = OBSTexExport.matchHyphen.sub(OBSTexExport.NBHY, copy, OBSTexExport.MATCH_ALL)
        copy = OBSTexExport.matchHyphenEM.sub(OBSTexExport.NBHY, copy, OBSTexExport.MATCH_ALL)

        # change spaces to non-breaking 1/2 em
        copy = OBSTexExport.matchAlphaNumSpaceThenNumber.sub(r'\1' + OBSTexExport.NBKN + r'\2', copy,
                                                             OBSTexExport.MATCH_ALL)
        copy = OBSTexExport.matchColonSemicolonNotAfterDigits.sub(r'\1\2 \3', copy, OBSTexExport.MATCH_ALL)
        copy = OBSTexExport.matchCommaBetweenDigits.sub(r'\1\2\3', copy, OBSTexExport.MATCH_ALL)
        copy = OBSTexExport.matchOrdinalBookSpaces.sub(r'\1' + OBSTexExport.NBSP, copy, OBSTexExport.MATCH_ALL)
        return copy


    def get_ref(self, place_ref_template, text) -> str:

        if self.body_json['language_direction'] == 'rtl':
            pardir = 'TRT'
        else:
            pardir = 'TLT'
        each = place_ref_template.substitute(thetext=text, pardir=pardir).split('\n')
        return '\n'.join(each)


    @staticmethod
    def filter_apply_docuwiki_start(single_line:str) -> str:

        # Order is important here
        single_line = OBSTexExport.matchHeadingFourLevelPattern.sub(r'\1{\\bfd \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchHeadingThreeLevelPattern.sub(r'\1{\\bfc \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchHeadingTwoLevelPattern.sub(r'\1{\\bfb \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchHeadingOneLevelPattern.sub(r'\1{\\bfa \2}\3', single_line, OBSTexExport.MATCH_ALL)

        single_line = OBSTexExport.markdownH4_re.sub(r'\1{\\bfd \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.markdownH3_re.sub(r'\1{\\bfc \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.markdownH2_re.sub(r'\1{\\bfb \2}\3', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.markdownH1_re.sub(r'\1{\\bfa \2}\3', single_line, OBSTexExport.MATCH_ALL)

        # Just boldface for stories
        single_line = OBSTexExport.matchSectionPattern.sub(r'{\\bf \1}', single_line, OBSTexExport.MATCH_ALL)

        single_line = OBSTexExport.matchTripleAsteriskPairs.sub(r'{\\bf {\\em \1}}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchTripleUnderlinePairs.sub(r'{\\bf {\\em \1}}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchDoubleAsteriskPairs.sub(r'{\\bf \1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchDoubleUnderlinePairs.sub(r'{\\bf \1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchSingleAsteriskPairs.sub(r'{\\em \1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchSingleUnderlinePairs.sub(r'{\\em \1}', single_line, OBSTexExport.MATCH_ALL)

        # The \/ is an end-of-italic correction to add extra whitespace
        # single_line = OBSTexExport.matchDoubleUnderlinePairs.sub(r'\\underbar{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchMonoPattern.sub(r'{\\tt \1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchRedPattern.sub(r'\\color[middlered]{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchMagentaPattern.sub(r'\\color[magenta]{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchBluePattern.sub(r'\\color[blue]{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchGreenPattern.sub(r'\\color[middlegreen]{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchSubScriptPattern.sub(r'\\low{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchSuperScriptPattern.sub(r'\\high{\1}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchStrikeOutPattern.sub(r'\\overstrike{\1}', single_line, OBSTexExport.MATCH_ALL)

        # single_line = OBSTexExport.markdownItalic_re.sub(r'\1{\\em \2\/}\3', single_line, OBSTexExport.MATCH_ALL)
        # single_line = OBSTexExport.markdownBold_re.sub(r'\1{\\bf \2}\3', single_line, OBSTexExport.MATCH_ALL)

        return single_line


    @staticmethod
    def filter_apply_docuwiki_finish(single_line:str) -> str:
        single_line = OBSTexExport.matchPipePattern.sub(r'\\textbar{}', single_line, OBSTexExport.MATCH_ALL)
        single_line = OBSTexExport.matchRemoveDummyTokenPattern.sub(r'', single_line, OBSTexExport.MATCH_ALL)
        return single_line


    @staticmethod
    def filter_apply_docuwiki(single_line:str) -> str:
        single_line = OBSTexExport.filter_apply_docuwiki_start(single_line)
        single_line = OBSTexExport.filter_apply_docuwiki_finish(single_line)
        return single_line


    @staticmethod
    def filter_apply_docuwiki_and_links(single_line:str) -> str:
        single_line = OBSTexExport.filter_apply_docuwiki_start(single_line)

        # set up http(s) hyperlinks
        single_line = OBSTexExport.markdownURL_re.sub(OBSTexExport.clickableLink_re, single_line)
        single_line = OBSTexExport.markdownLongTextURL_re.sub(OBSTexExport.clickableTextLink_re, single_line)
        single_line = OBSTexExport.markdownTextURL_re.sub(OBSTexExport.clickableTextLink_re, single_line)

        # if (shew): print "==single_line=",single_line
        single_line = OBSTexExport.filter_apply_docuwiki_finish(single_line)
        # if (shew): print "!!single_line=",single_line
        return single_line


    def export_matter(self, lang_message:str, test:bool) -> str:
        """
        Exports JSON front/back matter to specified format.
        """
        split = lang_message.split('\n')
        matter = []
        if test:
            split.append(r'\\\\ \\\\')
            split.append(r'Testing E=mc<sup>2</sup> and also H<sub>2</sub>O but not <del>discarded</del> \\\\')
            long_str = r'Testing <red>red</red> and <green>green</green> and <blue>blue</blue> and <mag>magenta</mag>'
            split.append(long_str)
            split.append(r"and ''mono'' and  __under__  and **bold** and \/ //italics// \\\\")

        self.num_items = 0

        def another_item(match_obj) -> str:
            self.num_items += 1
            ans = '    \\item{' + match_obj.group(1) + '}'
            if self.num_items == 1:
                ans = '    \\startitemize[intro,joinedup,nowhite]\n' + ans
            return ans

        for single_line in split:
            copy = single_line
            single_line = OBSTexExport.matchBlankLinePattern.sub(r'    \\blank', single_line, OBSTexExport.MATCH_ALL)
            # single_line = matchBlankLinePat.sub(r'    \\par\\par',single_line,MATCH_ALL)
            (single_line, occurrences) = OBSTexExport.matchBulletPattern.subn(another_item, single_line,
                                                                          OBSTexExport.MATCH_ONE)

            stop_itemize = False
            if (self.num_items > 0) and (occurrences == 0):
                self.num_items = 0
                stop_itemize = True

            no_indent = (copy == single_line)

            single_line = OBSTexExport.filter_apply_docuwiki_and_links(single_line)
            single_line = OBSTexExport.matchChapterVersePattern.sub(r'~\1', single_line, OBSTexExport.MATCH_ALL)

            if stop_itemize:
                single_line = '    \\stopitemize\n' + single_line

            if no_indent:
                single_line = '    \\noindentation ' + single_line

            matter.append(single_line)
        return '\n'.join(matter)


    @staticmethod
    def start_of_physical_page(xtr:str) -> str:
        return '\n'.join([xtr + '%%START-OF-PHYSICAL-PAGE', xtr + '\\vtop{'])


    @staticmethod
    def end_of_physical_page(xtr:str) -> str:
        return '\n'.join([xtr + '}', xtr + '%%END-OF-PHYSICAL-PAGE'])


    def get_document_title_logo(self) -> str:
        """
        Determine if we need a uW logo or other Title on the front (first) page

        Returns a TeX string
        """
        # logging.critical("get_document_title_logo()…")
        # logging.critical(f"  language_id='{self.language_id}'")
        # logging.critical(f"  language_name='{self.language_name}'")
        # logging.critical(f"  title='{self.title}'")
        # logging.critical(f"  publisher='{self.publisher}'")
        # Display the logo for uW en OBS, else the vernacular title
        if self.publisher == 'unfoldingWord' and self.language_id == 'en': # Display ® logo
            return_string = f'\\midaligned{{\\externalfigure[{UW_OBS_LOGO_PATH}]}}'
        else:
            return_string = f"\\midaligned{{\\textdir {'TRT' if self.language_direction=='rtl' else 'TLT'}" \
                                            f"\\tfd{{\\WORD{{{self.title}}}}}}}"
                            # f"    {{\\tfb{{\\WORD{{{self.language_name}}}}}}}"
        # Display the language name and language code
        #   NOTE: tfb->1.2x, tfx->0.8x according to https://wiki.contextgarden.net/Font_Switching#Font_sizes
        return_string += '\n' f"    \\blank[15em]\n" \
                              f"    \\midaligned{{\\tfb{{{self.language_name}}}}}\n" \
                              f"    \\midaligned{{{self.language_id}}}"
        # logging.critical(f"  About to return '{return_string}'")
        return f'    {return_string}'


    def export_chapters(self, chapters_json, max_chapters:int, img_res:str, lang) -> str:
        """
        Exports JSON to specified format.
        """
        spaces4 = ' ' * 4

        calc_vertical_need_snip = self.tex_load_snippet_file(spaces4, 'calculate-vertical-need.tex')
        calc_leftover_snip = self.tex_load_snippet_file(spaces4, 'calculate-leftover.tex')
        begin_loop_snip = self.tex_load_snippet_file(spaces4, 'begin-adjust-loop.tex')
        in_leftover_snip = self.tex_load_snippet_file(spaces4 + spaces4, 'calculate-leftover.tex')
        in_adjust_snip = self.tex_load_snippet_file(spaces4 + spaces4, 'adjust-spacing.tex')
        end_loop_snip = self.tex_load_snippet_file(spaces4, 'end-adjust-loop.tex')
        verify_snip = self.tex_load_snippet_file(spaces4, 'verify-vertical-space.tex')
        place_ref_snip = self.tex_load_snippet_file(spaces4, 'place-reference.tex')
        adjust_one_snip = calc_vertical_need_snip + calc_leftover_snip + verify_snip
        adjust_two_snip = calc_vertical_need_snip + begin_loop_snip + in_leftover_snip + in_adjust_snip + \
            end_loop_snip + calc_leftover_snip + verify_snip
        adjust_one = Template(adjust_one_snip)
        adjust_two = Template(adjust_two_snip)
        place_ref_template = Template(place_ref_snip)

        output = []
        for ix_chp, chp in enumerate(chapters_json):
            past_max_chapters = (max_chapters > 0) and (ix_chp >= max_chapters)
            if past_max_chapters:
                break
            output.append(self.get_title(chp['title']))
            chapter_frames = chp['frames']
            n_frame = len(chapter_frames)
            ref_text_only = OBSTexExport.do_not_break_before_chapter_verse(chp['ref'])
            for ix_frame, fr in enumerate(chapter_frames):
                ix_look_ahead = 1 + ix_frame
                is_even = ((ix_frame % 2) == 0)
                is_last_page = \
                    (is_even and ((ix_frame + 2) >= n_frame)) \
                    or ((not is_even) and ((ix_frame + 1) >= n_frame))
                page_is_full = (not is_even) or (ix_look_ahead < n_frame)
                text_only = fr['text'].replace('https://cdn.door43.org/obs/jpg/360px/', OBS_IMAGE_FOLDER_PATH)

                text_only = OBSTexExport.filter_apply_docuwiki(text_only)
                # TEMP FIX for DOUBLY-emphasised Scripture references at and of each story (RJH Jan2020)
                if ref_text_only.startswith('_') and ref_text_only.endswith('_'):
                     # References are automatically emphasised by the template
                     #  so emphasing again turns it off!!!
                    ref_text_only = ref_text_only[1:-1] # Remove the leading and trailing underline characters
                ref_text_only = OBSTexExport.filter_apply_docuwiki(ref_text_only)
                text_frame = OBSTexExport.get_frame(spaces4, 'toptry' if is_even else 'bottry')
                image_frame = OBSTexExport.get_image(spaces4, fr['id'], img_res)

                also_reg = '\\refneed' if is_last_page else '\\EmptyString'
                need_also = '\\refneed + ' if is_last_page else ''
                page_word = 'LAST_PAGE' if is_last_page else 'CONTINUED'
                truth_is_last_page = 'true' if is_last_page else 'false'
                if not is_even:
                    output.append(spaces4 + spaces4 + '\\vskip \\the\\leftover')
                elif page_is_full:
                    next_fr = chapter_frames[ix_look_ahead]
                    next_text_only = next_fr['text']
                    next_text_only = OBSTexExport.filter_apply_docuwiki(next_text_only)
                    next_image_frame = OBSTexExport.get_image(spaces4, next_fr['id'], img_res)
                    tex_dict = dict(pageword=page_word, needalso=need_also, alsoreg=also_reg,
                                    topimg=image_frame, botimg=next_image_frame,
                                    lang=lang, fid=fr['id'], isLastPage=truth_is_last_page,
                                    toptxt=text_only, bottxt=next_text_only, reftxt=ref_text_only)
                    output.append(adjust_two.safe_substitute(tex_dict))
                else:
                    tex_dict = dict(pageword=page_word, needalso=need_also, alsoreg=also_reg,
                                    topimg=image_frame, botimg='',
                                    lang=lang, fid=fr['id'], isLastPage=truth_is_last_page,
                                    toptxt=text_only, bottxt='', reftxt=ref_text_only)
                    output.append(adjust_one.safe_substitute(tex_dict))
                if is_even:
                    output.append(OBSTexExport.start_of_physical_page(spaces4))
                output.append(spaces4 + spaces4 + ''.join(['\\message{FIGURE: ', lang, '-', fr['id'], '}']))
                output.append(text_frame)
                output.append(image_frame)
                if (not is_even) and (not is_last_page):
                    output.append(OBSTexExport.end_of_physical_page(spaces4))
                    output.append(spaces4 + '\\page[yes]')
            output.append(self.get_ref(place_ref_template, ref_text_only))
            output.append(OBSTexExport.end_of_physical_page(spaces4))
            output.append(spaces4 + '\\page[yes]')
        return '\n'.join(output)
    # end of export_chapters function


    def run(self) -> None:

        relative_path_re = re.compile(r'([{ ])obs/tex/')

        remember_out = sys.stdout

        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

        # Parse the front and back matter
        front_matter = self.export_matter(self.front_matter, test=False)

        # The front matter really has two parts, an "about" section and a "license" section
        # Sadly the API returns it as one blob, but we want to insert the checking level
        # indicator on between the two. Until such a time as the API returns these strings separately,
        # this is a hack to split them. Failing a match it should just put the whole thing in the first section
        # fm = re.split(r'\{\\\\bf.+:\s*\}\\n', front_matter)
        # noinspection RegExpRedundantEscape
        fm = re.split(r'\s(?=\{\\bf.+:\s*\})', front_matter)
        output_front_about = fm[0]
        if len(fm) > 1:
            output_front_license = ''.join(fm[1:])
        else:
            output_front_license = ''
        # TODO: Do these strings need to be translated???
        output_front_license += f"\n\nPDF created {datetime.date.today()} from {self.description}."

        output_back = self.export_matter(self.back_matter, test=False)

        # Parse the body matter
        self.check_for_standard_keys_json()

        output_chapters = self.export_chapters(self.body_json['chapters'], self.max_chapters, self.img_res, self.body_json['language_id'])

        # For ConTeXt files only, Read the "main_template.tex" file replacing
        # all <<<[anyvar]>>> with its definition from the body-matter JSON file
        tex_template_filepath = os.path.join(OBSTexExport.snippets_dirpath, 'main_template.tex')
        if not os.path.exists(tex_template_filepath):
            print("Failed to get TeX template.")
            sys.exit(1)

        with codecs.open(tex_template_filepath, 'r', encoding='utf-8-sig') as in_file:
            template = in_file.read()

        # replace relative path to fonts with absolute
        template = relative_path_re.sub(r'\1{0}/'.format(OBSTexExport.snippets_dirpath), template)

        outlist = []
        for single_line in template.splitlines():

            if OBSTexExport.matchTitleLogoPattern.search(single_line):
                outlist.append(self.get_document_title_logo())
            elif OBSTexExport.matchFrontMatterAboutPattern.search(single_line):
                outlist.append(output_front_about)
            elif OBSTexExport.matchFrontMatterlicensePattern.search(single_line):
                outlist.append(output_front_license)
            elif OBSTexExport.matchChaptersPattern.search(single_line):
                outlist.append(output_chapters)
            elif OBSTexExport.matchBackMatterPattern.search(single_line):
                outlist.append(output_back)
            else:
                occurs = 1
                while occurs > 0:
                    (single_line, occurs) \
                        = OBSTexExport.matchMiscPattern.subn(self.another_replace, single_line,
                                                         OBSTexExport.MATCH_ALL)
                outlist.append(single_line)
        full_output = '\n'.join(outlist)
        write_file(self.out_path, full_output)

        sys.stdout = remember_out
    # end of run()
