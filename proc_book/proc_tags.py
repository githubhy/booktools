import logging
import argparse
import pyparsing as pp
from pyparsing import pyparsing_unicode as ppu
from utils import FilenameInOut
import pprint
import os

parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('--test_cat', type=str, default=None)
parser.add_argument('--hugofy', action='store_true')
parser.add_argument('file_name')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                    datefmt="%d/%b/%Y %H:%M:%S")


pp.enable_all_warnings()


def handle_title(toks):
    d = toks[0].as_dict()
    return '\n<h{0}{id}{cls}>{1}</h{0}>\n'.format(
                    d.get('level')[0], d.get('text')[0],
                    id = ' id="{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else '',
                    cls = ' class="{0}"'.format(' '.join(d['class_tag'])) if d.get('class_tag') else ''
                    )


def handle_nested_class(toks):
    d = toks[0].as_dict()
    l = toks[0].as_list()
    id_tag = d.get('id_tag', [''])[0]
    class_tag = ''.join(d.get('class_tag', []))
    attr = ''
    if id_tag:
        attr += ' id="{0}"'.format(id_tag)
        l.remove(id_tag)
    if class_tag:
        attr += ' class="{0}"'.format(class_tag)
        l.remove(class_tag)
    return '<span{id}{cls}>{0}</span>'.format(''.join(l),
                    id = ' id="{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else '',
                    cls = ' class="{0}"'.format(' '.join(d['class_tag'])) if d.get('class_tag') else '')

def handle_empty_id(toks):
    d = toks[0].as_dict()
    return '<span{id}></span>'.format(
                    id = ' id="{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else '')

def handle_ref(toks):
    d = toks[0].as_dict()
    return '<a{link}>{0}</a>'.format(''.join(d.get('text')[0]),
                    link = ' href="{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else ''
                    )


base_n_chars = '*[]{}()'
_text_raw = pp.CharsNotIn(base_n_chars)
_strong_emphasis = pp.QuotedString(
    "**").set_results_name('strong_emphasis', listAllMatches=True).set_parse_action(lambda toks: '<strong>{}</strong>'.format(toks[0]))
_emphasis = pp.QuotedString(
    "*").set_results_name('emphasis', listAllMatches=True).set_parse_action(lambda toks: '<em>{}</em>'.format(toks[0]))
# The parentheses is a must. Don't know why.
_text = (_strong_emphasis | _emphasis | _text_raw)

# Nested expressions that have multiple opener/closer types: https://stackoverflow.com/a/4802004
# Here I don't use pp.nested_expr() because it automatically suppresses the openers and closers
nestedParens = pp.Forward()
nestedBrackets = pp.Forward()
nestedCurlies = pp.Forward()
enclosed = (_text | nestedParens | nestedBrackets | nestedCurlies)[1, ...]
nestedParens << ~pp.Literal(
    ']') + pp.Literal('(') + ~pp.one_of('# .') + enclosed + pp.Literal(')')
nestedBrackets << pp.Literal(
    '[') + enclosed + pp.Literal(']') + ~pp.one_of('{# (# {.')
nestedCurlies << ~pp.Literal(
    ']') + pp.Literal('{') + ~pp.one_of('# .') + enclosed + pp.Literal('}')
text = pp.Group(enclosed).set_results_name('text', listAllMatches=True).set_parse_action(lambda toks: toks[0])

_id_tag = pp.Literal('#').suppress() + pp.CharsNotIn(base_n_chars +
                                                     '#. ').set_results_name('id_tag', listAllMatches=True)
_class_tag = pp.Literal('.').suppress(
) + pp.Word(pp.alphanums+'_-').set_results_name('class_tag', listAllMatches=True)
_tag = pp.OneOrMore(_id_tag | _class_tag)

_empty_id = pp.Group(pp.Literal('[]{').suppress() + _tag
                + pp.Literal('}').suppress()).set_results_name('empty_id', listAllMatches=True).set_parse_action(handle_empty_id)
# _title = pp.Group(
#                 pp.LineStart() + pp.OneOrMore(pp.Literal('#')).set_parse_action(lambda toks: len(
#                         toks)).set_results_name('level', listAllMatches=True)
#                 + pp.CharsNotIn('#{}\n').set_parse_action(
#                         lambda toks: toks[0].strip()).set_results_name('text', listAllMatches=True)
#                 + pp.Opt(pp.Literal('{').suppress() +
#                         _tag + pp.Literal('}').suppress())
#                 ).set_results_name('title', listAllMatches=True).set_parse_action(handle_title)
_ref = pp.Group(pp.Literal('[').suppress() + text
                + pp.Literal('](').suppress() + _id_tag +
                pp.Literal(')').suppress()
                ).set_results_name('ref', listAllMatches=True).set_parse_action(handle_ref)


nested_class = pp.Forward()
_content = (_empty_id | _ref | text | nested_class)[1, ...] # (_title |_empty_id | _ref | text | nested_class)[1, ...]
# pp.nested_expr() will make the opener and closer disappear, use the method mentioned here instead:
# https://stackoverflow.com/a/23854320
nested_class << pp.Group(pp.Literal('[').suppress() + _content
                          + pp.Literal(']{').suppress() +
                          _tag + pp.Literal('}').suppress()
                          ).set_results_name('class', listAllMatches=True).set_parse_action(handle_nested_class)
content = _content.leave_whitespace()

test_string = '''\
[]{#卷三·魏书三·明帝纪第三-明帝叡-6}
三年夏四月，
[是年春，诸葛亮拔取武都、阴平二郡。夏四月，孙权即皇帝位，改元黄龙。《魏志》均未书。]{.c1}
元城王礼薨。六月癸卯，繁阳王穆薨。
[◎钱大昭曰：明帝子有清河王冏、繁阳王穆、安平哀王殷，〖追封谥。〗虽曰早薨，然既有封地，自可于《王公传》中备书，今传但载武、文，不及明帝者，以宫省事秘，莫知其所由来。亦由班史于孝惠后宫子三王、三侯不书于表、传中也。]{.c1}
戊申，追尊高祖大长秋曰高皇帝，夫人吴氏曰高皇后。
[◎《通典》卷七十二云：明帝太和三年，六月，司空陈群等议，以为：“周武追尊太王、王季、文王皆为王，是时周天子以王为号，追尊即同，故谓不以卑临尊也。魏以皇帝为号，今追号皇高祖中常侍大长秋特进君为王，乃以卑临尊也。故汉祖尊其父为上皇，自是以后诸侯为帝者，皆尊其父为皇也。大长秋特进君宜号高皇，载主宜以金根车，可遣大鸿胪持节，乘大使车，从驺骑，奉印绶，即邺庙以太牢告祠。”从之。〖《通典》又引明帝诏及刘晔议，已见本志《刘晔传》，不录。〗侍中缪袭议以为：“元者，一也，首也，气之初也。是以周文演《易》以冠四德，仲尼作《春秋》以统三正。又《谥法》曰：‘行义悦人曰元，尊仁贵德曰元。’处士君宜追加谥号曰元皇。”太傅钟繇议：“案《礼·小记》曰：‘亲亲以三为五，以五为九，上杀下杀旁杀而亲毕矣。’乃唐尧之所以敦叙于九族也。其礼上杀于五，非不孝敬于祖也；下杀于五，非不慈爱于其孙也；旁杀于五，非不笃友于昆弟也。故为族属，以礼杀之。处士君其数在六，于属已尽，其庙当毁，其主当迁。今若追崇帝王之号，天下素不闻其受命之符，则是武皇帝栉风沐雨、勤劳天下为非功也。推以人情，普天率土不袭此议，处士君明神不安此礼。（令）〈今〉诸博士以礼断之，其议可从。”诏从之。◎何焯曰：与其追尊曹腾，自实其为赘阉乞养，不如丕之杀于礼矣。此自为叡不能生子而以加隆所后之亲，为后来劝，与下七月诏书连类而观，可以得其情矣。]{.c1}


[]{#卷三·魏书三·明帝纪第三-明帝叡-7}
秋七月，诏曰：“礼，皇后无嗣，

# 我们 看到了 wded {#jk-89 .chae_ei}
## ni们 de 我们 {#j-98_w9 .c_ei}
    0. [我们[看
    到]{.c2}了
    ]{.c1}
    1. 塔里[]{#宋轶二十八-徐处仁-1}
    见*吴*敏[2](#宋轶二十八-吴敏-2)。
    2. []{#宋轶二十八-徐处仁-2}
    见**吴yi**敏[4](#宋轶二十八-吴敏-4)。
    3. wo[我们[看到]了{真的{吗}}]
    4. [我到了]{#我峨嵋-9 .e_8-9}
    '''

flag_DEBUG = 0

if flag_DEBUG:
    # content.run_tests(test_string)
    res = content.transform_string(test_string)
    # Use res.dump() to analyze the results, see: https://stackoverflow.com/a/9996844
    print(content.parse_string(test_string).dump())
    p = pprint.PrettyPrinter(indent=4)
    p.pprint(res)
    exit(0)

def dict2str(d):
    return '\n'.join(['{}: {}'.format(k,v) for k,v in d.items()])

def hugo_front_matter(d):
    return '---\n{}\n---\n'.format(dict2str(d))


fn = FilenameInOut(args.file_name, ext_in='.Rmd', dir_out=args.output_dir, ext_out='.md')
in_names = fn.get_in_names()
out_names = fn.get_out_names()
file_names = fn.file_names
out_path = fn.out_path
for i in range(len(in_names)):
    with open(in_names[i], 'r') as f:
        parsed_content = content.transform_string(f.read())

    if args.hugofy:
        out_dir = os.path.join(out_path, file_names[i])
        os.makedirs(out_dir, exist_ok=True) 
        out_name = os.path.join(out_dir, file_names[i])

        chap_start = '\n# '
        chaps = parsed_content.split('\n# ')
        chaps[0] = chaps[0].replace('# ', '')
        for chap_i in range(len(chaps)):
            chap_name = chaps[chap_i].partition('\n')[0]
            front_matter = hugo_front_matter({'weight': chap_i+1, 'title': chap_name})
            with open('{}-{:02.0f}.{}'.format(out_name, chap_i, 'md'), 'w') as f:
                f.write(front_matter + chap_start + chaps[chap_i])
        with open(os.path.join(out_dir, '_index.md'), 'w') as f:
            f.write(hugo_front_matter({'weight': i+1, 'title': file_names[i], 'bookCollapseSection': 'true'}))
    else:
        with open(out_names[i], 'w') as f:
            f.write(parsed_content)
