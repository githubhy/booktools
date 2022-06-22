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

#all_chars = pp.printables + ppu.Chinese.printables + '〇　。，；：、﹑-！￥……（）―？《》〈〉〖〗【】「」■□♀．·“”„’‘◎○ ,;:/-!?<>~()[]{}#@$%^&*+=_/\\|`\'\'"\r\n\t\f\v'
base_n_chars = '*[]{}()'
_text_raw = pp.CharsNotIn(base_n_chars) #pp.Word(all_chars, excludeChars="[]{}()")
_text_emphasis = pp.QuotedString("**") | pp.QuotedString("*")
_text = _text_emphasis | _text_raw

# Nested expressions that have multiple opener/closer types: https://stackoverflow.com/a/4802004
enclosed = pp.Forward()
#sym_not_followd_by = ~(pp.Literal('{#') | pp.Literal('(#') | pp.Literal('{.'))
nestedParens = pp.nestedExpr(pp.Literal('('), pp.Literal(')'), content=enclosed) 
nestedBrackets = pp.nestedExpr(pp.Literal('['), pp.Literal(']') + ~pp.one_of('{# (# {.'), content=enclosed) 
nestedCurlies = pp.nestedExpr(pp.Literal('{'), pp.Literal('}'), content=enclosed) 
enclosed << (_text | nestedParens | nestedBrackets | nestedCurlies)
text = (_text | enclosed)[1,...]

_tag = pp.CharsNotIn(base_n_chars+'#')
_id = pp.Literal('[') + text[...] + pp.Literal(']{#') + _tag + pp.Literal('}')
_id_for_line = ~pp.Literal('[') + pp.Literal('{#') + _tag + pp.Literal('}')
_ref = pp.Literal('[') + text + pp.Literal('](#') + _tag + pp.Literal(')')
_content = (_id | _ref | text)[1,...]
_class = pp.nested_expr('[', pp.Literal(']{.') + pp.Word(pp.alphanums) + pp.Literal('}'),
                        content=_content,
                        ignore_expr=None)
content = (_content | _class)[1,...]
content.set_name('content')
content.setDefaultWhitespaceChars("")
pp.enable_all_warnings()

result = content.parse_string('''
    0. [我们看到了]{.c1}
    1. 塔里[]{#宋轶二十八-徐处仁-1}
    见*吴*敏[2](#宋轶二十八-吴敏-2)。
    2. []{#宋轶二十八-徐处仁-2}
    见**吴**敏[4](#宋轶二十八-吴敏-4)。
    3. [我们[看到]了]
    4. [我们看到了]{.c1}
    ''')

print(''.join(flatten(result.as_list())))
print(result)

# fn = FilenameInOut(args.file_name, dir_out=args.output_dir, ext_out='.Rmd')
# doc = Document(fn.get_in_names()[0])