import re
import os
import logging
import argparse
import itertools

from regex import E


parser = argparse.ArgumentParser(description='Add cross reference links to the book 《唐|宋轶事汇编》 in markdown format')
parser.add_argument('file_name') # type=argparse.FileType('r')
parser.add_argument('--orig', '-o', action='store_const', const=True, default=False,
                    help='Output with the original format instead of the R markdown')
parser.add_argument('--convert', '-c', action='store_const', const=True, default=False,
                    help='Convert the text to Simplified Chinese')
parser.add_argument('--split', '-s', action='store_const', const=True, default=False,
                    help='Split the book to several chapters')
parser.add_argument('--output_dir', '-d', type=str, default=None)
args = parser.parse_args()

chap_re = r'^\s*(?:#|\*{2})\s*(?P<chap_name>(?P<dyn>[宋|唐])人軼事彙編卷(?P<chap_no>[\u4e00-\u9fa5]+))\s*(?:\*{2})?\s*\n'
sec_re = r'^\s*(?:##|\*{2})\s*(?P<sec_name>(?P<people_name>[\u4e00-\u9fa5|　]+)[　|\s]*(?:（[\u4e00-\u9fa5|　]+）)*)[　|\s]*(?:\*{2})?\s*\n' # (?:（[\u4e00-\u9fa5|　]+）)*
para_re = r'^\s*(?P<idx0>\d+)(?:、(?P<idx1>\d+))*(?:~(?P<idxn>\d+))*[　|\s]*(?P<para>.*)\n'


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

tags_dict = dict()
chapters = dict()

def get_tag_key(name, index):
    return "{0}{1}".format(name, index)

def proc_line(indices, names, dyn, chap_no, para):
    if not (indices and names and dyn and chap_no):
        return None
    inds = [indices] if type(indices) is str else list(filter(None, indices))
    secs = [names] if type(names) is str else list(filter(None, names))
    
    out_lines = list()
    for i in inds:
        tags = dict()
        for s in secs:
            tag = "{0}軼{1}-{2}-{3}".format(dyn, chap_no, s, i)
            tags[get_tag_key(s,i)] = tag
        out_lines.append("{0}. {1}\n{2}\n".format(i, ' '.join(["[]{{#{0}}}".format(v) for v in tags.values()]), para))
        tags_dict.update(tags)
    
    return out_lines


try:
    file_head, file_extension = os.path.splitext(args.file_name)
    file_path_and_name = os.path.split(file_head)
except:
    log.error("No file name specified or invalid filename")
    exit()



with open(args.file_name, 'r') as f:
    lines = f.readlines()
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

            ls = proc_line(para_idx, people_names, dyn, chap_no, para)
            chapters[chap_no] += ls if ls else [nl]

flag_able_to_use_cc = True
try:
    from opencc import OpenCC
except ImportError:
    flag_able_to_use_cc = False

flag_able_to_split = True
try:
    from cn2an import cn2an
except ImportError:
    flag_able_to_split = False

for chao_no, chap in chapters.items():
    new_lines = list()
    for l in chap:
        m_p = re.search(r'^(?P<para_start>.*\s*)見\s*(?P<name>[\u4e00-\u9fa5]+)\s*(?P<index>\d+)(?P<para_end>.*)\n', l)
        nl = l
        possible_tag = None
        if m_p:
            possible_key = get_tag_key(m_p.group('name'), m_p.group('index'))
            possible_tag = tags_dict.get(possible_key)
            if possible_tag:
                link_2_tag = '[' + possible_key + '](#' + possible_tag + ')'
                nl = m_p.group('para_start') + '見' + link_2_tag + m_p.group('para_end') + '\n'
            else:
                log.warning("missing tags for: " + possible_key)
        new_lines.append(nl)
    chapters[chao_no] = new_lines


if not args.orig:
    file_extension = ".Rmd"


if flag_able_to_use_cc and args.convert:
    cc = OpenCC('t2s')
    for chao_no, chap in chapters.items():
        chapters[chao_no] = map(cc.convert, chap)


if args.output_dir:
    filename = os.path.join(args.output_dir, file_path_and_name[1])
else:
    filename = os.path.join(file_path_and_name[0], file_path_and_name[1])

if flag_able_to_split and args.split:
    for chao_no, chap in chapters.items():
        filename_out = "{0}-{1}-out{2}".format(filename, cn2an(chao_no), file_extension)
        text = ''.join(chap)
        with open(filename_out, 'w') as f:
            f.write(text)
else:
    with open("{0}-out{1}".format(filename, file_extension), 'w') as f:
        f.write(''.join(list(itertools.chain.from_iterable(chapters.values()))))


people = set([re.sub(r'\d+', '', t) for t in tags_dict.keys()])
log.info("There are " + str(len(people)) + " people in this book.")
