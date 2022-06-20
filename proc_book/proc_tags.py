import logging
import argparse
from docx import Document
import pyparsing as pp
from pyparsing import pyparsing_unicode as ppu
from fileinout import FilenameInOut


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

all_chars = pp.printables + ppu.Chinese.printables + '〇 　。，；：、﹑-！￥……（）―？《》〈〉〖〗【】■□♀．·“”„’‘◎○,;:/-!?<>~()[]{}#@$%^&*+=_/\\|`\'\'"\r\n\t\f\v'
text = pp.Word(all_chars.translate(str.maketrans('', '', '[]')))
text_w_brackets = pp.Literal('[') + text[...] + pp.Literal(']')
attr_content = text[...] + text_w_brackets[...] + text[...]
attr_content_w_brackets = pp.Group(pp.Literal('[') + attr_content + pp.Literal(']'))

def make_attr_parser(attr_name):
    attr = pp.Forward()
    attr_0 = attr_content_w_brackets + pp.Literal('{') + attr_name + pp.Literal('}')
    attr_1 = attr_0 | attr
    attr << pp.nested_expr(content=attr_1)
    attr.set_name('attr')
    return attr

# attr: [yyy]{id}
id_attr = make_attr_parser(id)
# ref: [yyy](id)
id_ref = attr_content_w_brackets + pp.Literal('(') + id + pp.Literal(')').setName('id_ref')
# attr: [yyy]{class}
klass_attr = make_attr_parser(klass)

pp.enable_all_warnings()

fn = FilenameInOut(args.file_name, dir_out=args.output_dir, ext_out='.Rmd')
doc = Document(fn.get_in_names()[0])