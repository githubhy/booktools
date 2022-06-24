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

base_n_chars = '*[]{}()'
_text_raw = pp.CharsNotIn(base_n_chars) #pp.Word(all_chars, excludeChars="[]{}()")
_strong_emphasis = pp.QuotedString("**").set_name('strong_emphasis')
_emphasis = pp.QuotedString("*").set_name('emphasis')
# The parentheses is a must. Don't know why.
_text = (_strong_emphasis | _emphasis | _text_raw)

# Nested expressions that have multiple opener/closer types: https://stackoverflow.com/a/4802004
# Here I don't use pp.nested_expr() because it automatically suppresses the openers and closers
nestedParens = pp.Forward()
nestedBrackets = pp.Forward()
nestedCurlies = pp.Forward()
enclosed = (_text | nestedParens | nestedBrackets | nestedCurlies)[1, ...]
nestedParens << ~pp.Literal(']') + pp.Literal('(') + ~pp.one_of('# .') + enclosed + pp.Literal(')')
nestedBrackets << pp.Literal('[') + enclosed + pp.Literal(']') + ~pp.one_of('{# (# {.')
nestedCurlies << ~pp.Literal(']') + pp.Literal('{') + ~pp.one_of('# .') + enclosed + pp.Literal('}')
text = pp.Group(enclosed).set_name('text')

_id_tag = pp.Literal('#').suppress() + pp.CharsNotIn(base_n_chars+'#. ').set_name('id_tag')
_class_tag = pp.Literal('.').suppress() + pp.Word(pp.alphanums+'_-').set_name('class_tag')
_tag = pp.OneOrMore(_id_tag | _class_tag)

_empty_id = pp.Group(pp.Literal('[]{').suppress() + _tag + pp.Literal('}').suppress()).set_name('empty_id')
_title = pp.Group(
            pp.OneOrMore(pp.Literal('#')).set_parse_action(lambda toks: len(toks[0])).set_name('level')
            + pp.CharsNotIn('#{}').set_parse_action(lambda toks: toks[0].strip()).set_name('name')
            + pp.Opt(pp.Literal('{').suppress() + _tag + pp.Literal('}').suppress())
        ).set_name('title')
_ref = pp.Group(pp.Literal('[').suppress() + text
                + pp.Literal('](').suppress() + _id_tag + pp.Literal(')').suppress()
                ).set_name('ref')
_nested_class = pp.Forward()
content = (_title | _empty_id | _ref | text | _nested_class)[1, ...]
# pp.nested_expr() will make the opener and closer disappear, use the method mentioned here instead:
# https://stackoverflow.com/a/23854320
_nested_class << pp.Group(pp.Literal('[').suppress() + content
                + pp.Literal(']{').suppress() + _tag + pp.Literal('}').suppress()
                ).set_name('class')
content.set_name('content')
pp.enable_all_warnings()


result = content.parse_string('''
# 我们 看到了 wded {#jk-89 .chae_ei}
    0. [我们看到了]{.c1}
    1. 塔里[]{#宋轶二十八-徐处仁-1}
    见*吴*敏[2](#宋轶二十八-吴敏-2)。
    2. []{#宋轶二十八-徐处仁-2}
    见**吴yi**敏[4](#宋轶二十八-吴敏-4)。
    3. wo[我们[看到]了{真的{吗}}]
    4. [我到了]{#我峨嵋-9 .e_8-9}
    ''')

# print(''.join(flatten(result.as_list())))
# Use res.dump() to analyze the results, see: https://stackoverflow.com/a/9996844
print(result.dump())

# fn = FilenameInOut(args.file_name, dir_out=args.output_dir, ext_out='.Rmd')
# doc = Document(fn.get_in_names()[0])