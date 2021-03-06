import logging
import argparse
import pyparsing as pp
from pyparsing import pyparsing_unicode as ppu
from utils import FilenameInOut
import pprint
import os
import multiprocessing as mp
import re

parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('--test_cat', type=str, default=None)
parser.add_argument('--hugofy', action='store_true')
parser.add_argument('--multicores', action='store_true')
parser.add_argument('--id_complete_dir', type=str, default=None)
parser.add_argument('file_name')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
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
    return '<a{id}{href} class="empty_id">\u00B6</a>'.format(
                    id = ' id="{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else '',
                    href = ' href="#{0}"'.format(d['id_tag'][0]) if d.get('id_tag') else '')

def handle_ref(toks):
    d = toks[0].as_dict()
    if args.hugofy:
        tag = d['id_tag'][0] if d.get('id_tag') else ''
        return '[{text}]({{{{< relref "{link}" >}}}} "{description}")'.format(
            text=''.join(d.get('text')[0]),
            link='#' + tag,
            description=tag
        )
    else:
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
[]{#??????????????????????????????????-?????????-6}
??????????????????
[???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????]{.c1}
???????????????????????????????????????????????????
[??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????]{.c1}
????????????????????????????????????????????????????????????????????????
[??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????]{.c1}


[]{#??????????????????????????????????-?????????-7}
?????????????????????????????????????????????

# ?????? ????????? wded {#jk-89 .chae_ei}
## ni??? de ?????? {#j-98_w9 .c_ei}
    0. [??????[???
    ???]{.c2}???
    ]{.c1}
    1. ??????[]{#???????????????-?????????-1}
    ???*???*???[2](#???????????????-??????-2)???
    2. []{#???????????????-?????????-2}
    ???**???yi**???[4](#???????????????-??????-4)???
    3. wo[??????[??????]???{??????{???}}]
    4. [?????????]{#?????????-9 .e_8-9}
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

def get_ids(s):
    return re.findall(r'id=\"(.*?)\"', s)

def get_ref_ids(s):
    return re.findall(r'\]\(\{\{\<\s*relref\s*\"(#.*?)\"\s*\>\}\}.*?\)', s)

def parse_tags(i, file_name, in_name, out_path):

    log.info('[tags] converting ' + in_name)

    with open(in_name, 'r') as f:
        parsed_content = content.transform_string(f.read())

    res = {}

    if args.hugofy:
        out_dir = os.path.join(out_path, file_name)
        os.makedirs(out_dir, exist_ok=True) 

        with open(os.path.join(out_dir, '_index.md'), 'w') as f:
            f.write(hugo_front_matter({'weight': i+1, 'title': file_name, 'bookCollapseSection': 'true'}))

        chap_start = '\n# '
        chaps = parsed_content.split(chap_start)
        chaps[0] = chaps[0].replace('# ', '', 1)
        for chap_i in range(len(chaps)):
            chap_name = chaps[chap_i].partition('\n')[0]
            front_matter = hugo_front_matter({'weight': chap_i+1, 'title': chap_name})
            sub_file_name = '{}-{:02.0f}.{}'.format(file_name, chap_i, 'md')
            with open(os.path.join(out_dir, sub_file_name), 'w') as f:
                f.write(front_matter + chap_start + chaps[chap_i])
            res.update({id: (file_name, sub_file_name) for id in get_ids(chaps[chap_i])})
    else:
        with open(os.path.join(out_path, file_name)+'.md', 'w') as f:
            f.write(parsed_content)
        res.update({id: (file_name, '') for id in get_ids(parsed_content)})

    log.info('[tags] conversion done for ' + in_name)

    return res

in_names = fn.get_in_names()
file_names = fn.file_names
out_path = fn.out_path

if args.multicores:
    pool = mp.Pool(processes=len(os.sched_getaffinity(0)))
    results = [pool.apply_async(parse_tags, args=(i, file_names[i], in_names[i], out_path)) for i in range(len(file_names))]
    pool.close()
    pool.join()
else:
    results = []
    for i in range(len(file_names)):
        results.append(parse_tags(i, file_names[i], in_names[i], out_path))

ids = {}
for r in results:
    if r:
        if args.multicores:
            ids.update(r.get())
        else:
            ids.update(r)

def replace_id(match):
    m1 = match.group(1)
    id = match.group(2)
    m3 = match.group(3)
    if ids.get(id[1:], None):
        fname, fsubname = ids[id[1:]]
        new_id = 'docs/{}{}{}'.format(fname, '/' + fsubname if fsubname else '', id)
    else:
        new_id = id
        log.warning('[id] no id named: ' + id)
    
    return m1 + new_id + m3

def replace_file_with_id(path):
    with open(path, 'r') as f:
        text_with_new_ref = re.sub(r'(\]\(\{\{\<\s*relref\s*\")(#.*?)(\"\s*\>\}\}.*?\))',
                                    replace_id,
                                    f.read())
    with open(path, 'w') as f:
        f.write(text_with_new_ref)
    
    log.info('[id] completion done for ' + path)


id_complete_dir = args.id_complete_dir if args.id_complete_dir else out_path
if args.multicores:
    pool = mp.Pool(processes=len(os.sched_getaffinity(0)))
    results = []
    for root, dirs, files in os.walk(id_complete_dir):
        results += [pool.apply_async(replace_file_with_id, args=(os.path.join(root, file),)) for file in files]
    pool.close()
    pool.join()
else:
    for root, dirs, files in os.walk(id_complete_dir):
        for file in files:
            replace_file_with_id(os.path.join(root, file))
