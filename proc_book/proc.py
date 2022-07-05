import re
import os
import logging
import argparse
import itertools
import db


chap_re = r'^\s*(?:#|\*{2})\s*(?P<chap_name>(?P<dyn>[宋|唐])人軼事彙編卷(?P<chap_no>[\u4e00-\u9fa5]+))\s*(?:\*{2})?\s*\n'
sec_re = r'^\s*(?:##|\*{2})\s*(?P<sec_name>(?P<people_name>[\u4e00-\u9fa5|　]+)[　|\s]*(?:（[\u4e00-\u9fa5|　]+）)*)[　|\s]*(?:\*{2})?\s*\n' # (?:（[\u4e00-\u9fa5|　]+）)*
para_re = r'^\s*(?P<idx0>\d+)(?:、(?P<idx1>\d+))*(?:~(?P<idxn>\d+))*[　|\s]*(?P<para>.*)\n'


parser = argparse.ArgumentParser(description='Add cross reference links to books in markdown format')
subparsers = parser.add_subparsers(title='subcommands',
                                    dest='command')#, description='valid subcommands')
persist_parser = subparsers.add_parser('persist', # aliases=['p'],
                                    help='Covert the original text and save the tags to database')
persist_parser.add_argument('--split', action='store_true',
                        help='Split the book to several chapters')
persist_parser.add_argument('--name', type=str, default=None,
                        help='Book name')
tag_parser = subparsers.add_parser('tag', # aliases=['p'],
                                    help='Process the tags saved in the database')
tag_parser.add_argument('--alt', action='store_true',
                        help='Tag the file using alternate tags')

parser.add_argument('--rmd', action='store_true',
                    help='Output with the original format instead of the R markdown')
parser.add_argument('--convert', action='store_true',
                    help='Convert the text to Simplified Chinese')
parser.add_argument('--tag_prefix', type=str, default=None,
                        help='Book tag, should be unique across all existing books in the database')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('file_name') # type=argparse.FileType('r')

args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")


#################### Dynamic load library ########################
cc = None
try:
    if args.convert:
        from opencc import OpenCC
        cc = OpenCC('t2s')
except ImportError:
    log.warning('Can not load OpenCC library')


#################### Internal functions #####################

def get_tag_key(name, index):
    return "{0}{1}".format(name, index)

def gen_ref(tag, prefix='', link_name=''):
    px = prefix + '-' if prefix else prefix
    braces = ('(', ')') if link_name else ('{', '}')
    return "[{0}]{left}#{1}{2}{right}".format(link_name, prefix, tag, left=braces[0], right=braces[1])

def proc_line(indices, names, dyn, chap_no, para, tags_dict):
    if not (indices and names and dyn and chap_no):
        return None
    inds = [indices] if type(indices) is str else list(filter(None, indices))
    secs = [names] if type(names) is str else list(filter(None, names))
    
    out_lines = list()
    for i in inds:
        tags = dict()
        for s in secs:
            tag = "{0}-{1}-{2}".format(chap_no, s, i)
            tags[get_tag_key(s,i)] = tag
        out_lines.append("{0}. {1}\n".format(i, ' '.join([gen_ref(v, args.tag_prefix) for v in tags.values()])))
        out_lines.append("{0}\n".format(para))
        tags_dict.update(tags)
    
    return out_lines


## For non-persistent processing

def exp_rg(m):
    return '、'.join([ str(i) for i in range(int(m.group('idx0')), int(m.group('idx1'))+1) ])

def gen_idx(s):
    res = []
    ns = re.sub(r'(?P<idx0>\d+)[\s　]*~[\s　]*(?P<idx1>\d+)', exp_rg, s)
    m0 = re.findall(r'(?P<idx>\d+)', ns)
    res += [int(m) for m in m0 if m0]

    return res

def proc_ref(s):
    res_dict = {}
    re_str = r'(?P<name>[\u4e00-\u9fa5]+)[\s　]*(?P<idx>[\d~、]+)'
    m0 = re.findall(re_str, s)
    for m in m0:
        res_dict[ m[0] ] = gen_idx(m[1])

    return res_dict

def cur_fun(x, flag_alt):
    cur = db.con.execute("""
                WITH g AS (
                    SELECT
                        {1}long,
                        {1}short,
                        {1}tag || {1}long AS full_long,
                        {1}tag || {1}short AS full_short
                    FROM content_tags
                    INNER JOIN books
                        ON books.id = content_tags.book_id
                ) SELECT
                    full_long
                FROM g
                WHERE
                    ({1}long = "{0}" AND (SELECT COUNT(*) FROM g WHERE {1}long = "{0}") = 1)
                    OR ({1}short = "{0}" AND (SELECT COUNT(*) FROM g WHERE {1}short = "{0}") = 1)
                    OR (full_long = "{0}" AND (SELECT COUNT(*) FROM g WHERE full_long = "{0}") = 1)
                    OR (full_short = "{0}" AND (SELECT COUNT(*) FROM g WHERE full_short = "{0}") = 1)
            """.format(x, 'alt_' if flag_alt else '')).fetchone()

    res = ''
    if cur:
        res = cur[0]
    else:
        log.warning("missing tags for: " + x)

    return res


def proc_tags(line):
    re_str = (r'(?P<para>.*?[見|见])'    # Use *? for non-greedy * (https://docs.python.org/3/library/re.html#regular-expression-syntax)
              r'(?P<ref>[\u4e00-\u9fa5\s　~、\[\]\(\)#\-\d]{2,}[\d\)]+)') #(?<!-)
    re_link_name_str = r'\[(?P<name>[\u4e00-\u9fa5\d]+)\]\(#[\u4e00-\u9fa5\d\-]*\)'
    m0 = re.findall(re_str, line)
    line_left = line.replace(''.join([m[0]+m[1] for m in m0 if m0]), '')
    m1 = [(m[0], re.sub(re_link_name_str, '\g<name>', m[1])) for m in m0 if m0]
    m2 = [(m[0], proc_ref(m[1])) for m in m1]

    # Generate text
    new_line = ''
    for para, ref in m2:
        tags = dict()
        for name, indices in ref.items():
            tags[name] = zip(indices, [cur_fun("{2}{0}{1}".format(name,i,args.tag_prefix), args.alt) for i in indices])
        ref_text = []
        for name, ind_and_tags in tags.items():
            ref_text.append(name + '、'.join([ gen_ref(it[1], link_name=it[0]) for it in ind_and_tags ]))
        new_line += para + '、'.join(ref_text)
    new_line += line_left

    return new_line


######################################

try:
    file_head, file_extension = os.path.splitext(args.file_name)
    file_path_and_name = os.path.split(file_head)
except:
    log.error("No file name specified or invalid filename")
    exit(1)

#### Read the source file
lines = []
with open(args.file_name, 'r') as f:
    lines = f.readlines()

if args.rmd:
    file_extension = ".Rmd"
if args.output_dir:
    os.makedirs(args.output_dir, exist_ok=True) 
    filename = os.path.join(args.output_dir, file_path_and_name[1])
else:
    filename = os.path.join(file_path_and_name[0], file_path_and_name[1])


#### Process
if args.command == 'persist':
    cn = None
    try:
        if args.split:
            from cn2an import cn2an
            cn = cn2an
    except ImportError:
        log.warning('Can not load cn2an library')

    tags_dict = dict()
    chapters = dict()
    dyn = None
    chap_no = None
    people_names = None

    for l in lines:
        para_idx = None
        para = None
        nl = l

        m = re.search(chap_re, l)
        if m:
            dyn = m.group('dyn')
            chap_no = m.group('chap_no')
            if chap_no not in chapters:
                chapters[chap_no] = []
            nl = "# {0}\n".format(m.group('chap_name'))
        if chap_no:
            m_s = re.search(sec_re, l) if not re.search(chap_re, l) else None
            if m_s:
                pl_name = m_s.group('people_name')
                people_names = pl_name.split('　') if len(pl_name) >= 5 else pl_name.replace('　', '')
                nl = "## {0}\n".format(m_s.group('sec_name'))
            if people_names:
                m_idx = re.search(para_re, l)
                if m_idx:
                    m_dict = m_idx.groupdict()
                    para = m_dict.pop('para')
                    para_idx = range(int(m_dict['idx0']), int(m_dict['idxn'])+1) if m_dict.get('idxn') else list(m_dict.values())

            ls = proc_line(para_idx, people_names, dyn, chap_no, para, tags_dict)
            chapters[chap_no] += ls if ls else [nl]

    if cc:
        for chao_no, chap in chapters.items():
            chapters[chao_no] = map(cc.convert, chap)

    if cn:
        for chao_no, chap in chapters.items():
            filename_out = "{0}-{1}-out{2}".format(filename, str(cn(chao_no)).zfill(2), file_extension)
            text = ''.join(chap)
            with open(filename_out, 'w') as f:
                f.write(text)
    else:
        with open("{0}-out{1}".format(filename, file_extension), 'w') as f:
            f.write(''.join(list(itertools.chain.from_iterable(chapters.values()))))

    if args.name and args.tag_prefix:
        tags_to_insert = [(k,v) for k,v in tags_dict.items()]

        db.con.execute("""
            INSERT OR IGNORE INTO books (title, tag)
            VALUES(?, ?)
            """, (args.name, args.tag_prefix))

        db.con.executemany("""
            INSERT OR REPLACE INTO content_tags (short, long, book_id)
            VALUES(?, ?, (SELECT id FROM books
                        WHERE title = "{0}"));
            """.format(args.name), tags_to_insert)

        if cc:
            db.con.execute("""
                UPDATE books
                SET alt_title = ?,
                    alt_tag = ?
                WHERE
                    title = ? AND tag = ?;
                """,(cc.convert(args.name), cc.convert(args.tag_prefix),
                        args.name, args.tag_prefix))
            db.con.executemany("""
                UPDATE content_tags
                SET alt_long = ?,
                    alt_short = ?
                WHERE
                    long = ? AND short = ?; 
                """, [(cc.convert(v), cc.convert(k), v, k) for k,v in tags_dict.items()])

        db.con.commit()
        
    people = set([re.sub(r'\d+', '', t) for t in tags_dict.keys()])
    log.info("There are " + str(len(people)) + " people in this book.")
else:
    newlines = [ proc_tags(l) for l in lines ]
    with open("{0}-out{1}".format(filename, file_extension), 'w') as f:
        f.write(''.join(newlines))

