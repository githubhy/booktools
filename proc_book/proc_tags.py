import logging
import argparse
from docx import Document
import pyparsing as pp
from pyparsing import pyparsing_unicode as ppu
from utils import FilenameInOut, flatten


parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('--test_cat', type=str, default=None)
parser.add_argument('file_name')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")

# id: #xx-xx-xxx
id_name_short = pp.Word(pp.alphanums + ppu.Chinese.alphanums)
id_name = pp.Group(id_name_short + (pp.Literal('-') + id_name_short)[...]).setName('id_name')
id = pp.Group(pp.Literal('#') + id_name).setName('id')

# class: .xxx
klass = pp.Literal('.') + pp.Regex(r'\w[\w\d-]*')

def t(s, l, t):
    return t[0]

all_chars = pp.printables + ppu.Chinese.printables + '〇　。，；：、﹑-！￥……（）―？《》〈〉〖〗【】「」■□♀．·“”„’‘◎○ ,;:/-!?<>~()[]{}#@$%^&*+=_/\\|`\'\'"\r\n\t\f\v'
text_raw = pp.Word(all_chars, excludeChars="[]{}()")
text_w_brackets = pp.Literal('[') + text_raw[...] + pp.Literal(']').set_name('text_w_brackets')
text_w_braces = pp.Literal('{') + text_raw[...] + pp.Literal('}').set_name('text_w_braces')
text_w_parentheses = pp.Literal('(') + text_raw[...] + pp.Literal(')').set_name('text_w_parentheses')
text = text_raw & text_w_brackets[...] & text_w_braces[...] & text_w_parentheses[...]
_attr = pp.Forward()
_id = pp.Literal('[') + text + pp.Literal(']{#') + text_raw + pp.Literal('}')
_ref = pp.Literal('[') + text + pp.Literal('](#') + text_raw + pp.Literal(')')
attr_content =  text & _id[...] & _ref[...]
_attr << attr_content[...] & pp.nested_expr('[', pp.Literal(']{.') + pp.one_of(pp.alphas) + pp.Word(pp.alphanums)[...] + pp.Literal('}'), content=attr_content)
attr = _attr
attr.set_name('attr')
attr.setDefaultWhitespaceChars("")

pp.enable_all_warnings()

result = attr.parse_string('''
1. []{#宋轶二十八-徐处仁-1}
见*吴*敏[2](#宋轶二十八-吴敏-2)。
2. []{#宋轶二十八-徐处仁-2}
见**吴**敏[4](#宋轶二十八-吴敏-4)。
''')

print(''.join(flatten(result.as_list())))

# fn = FilenameInOut(args.file_name, dir_out=args.output_dir, ext_out='.Rmd')
# doc = Document(fn.get_in_names()[0])