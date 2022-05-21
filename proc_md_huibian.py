import re
import os
import logging

file_name = '唐人轶事汇编 copy.md'

chap_re = r'^\s*(?:#|\*{2})\s*([宋|唐])人軼事彙編卷([\u4e00-\u9fa5]+)\s*(?:\*{2})?\s*\n'
sec_re = r'^\s*(?:##|\*{2})\s*([\u4e00-\u9fa5|　]+)(?:（[\u4e00-\u9fa5|　]+）)*\s*(?:\*{2})?\s*\n'


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

file_path = os.path.join('tools', file_name)
out_file_path = os.path.join('tools', 'temp_' + file_name)

new_lines = list()
people = list()
with open(file_path, 'r') as f:
    lines = f.readlines()
    dyn = None
    chap_no = None
    sec_names = None
    para_idx = None
    para = None
    tags_dict = dict()
    nls = list()
    for l in lines:
        m = re.search(chap_re, l)
        if m:
            dyn = m.group(1)
            chap_no = m.group(2)
        if chap_no:
            m_s = re.search(sec_re, l)
            if m_s:
                s_names = m_s.group(1)
                if len(s_names) >= 5:
                    sec_names = s_names.split('　')
                    # print(sec_names)
                else:
                    sec_names = [s_names]
                # print(sec_names)
            if sec_names:
                m_idx = re.search(r'^\s*(\d+)[　|\s]*(.*)\n', l)
                if m_idx:
                    para_idx = m_idx.group(1)
                    para = m_idx.group(2)
                else:
                    para_idx = None
                    para = None
        if dyn and chap_no and sec_names and para_idx and para:
            nl_start = para_idx + '. '
            for s in sec_names:
                # print(s)
                sec_name = s.replace('　', '')
                tag = dyn + '軼彙' + chap_no + '-' + sec_name + '-' + para_idx
                nl_start += '[]{#' + tag + '} '
                tags_dict[sec_name + para_idx] = tag
                people.append(sec_name)
            nl = nl_start + para + '\n'
        else:
            nl = l
        nls.append(nl)
    
    for l in nls:
        m_p = re.search(r'^(.*\s*)見\s*([\u4e00-\u9fa5]+)\s*(\d+)(.*)\n', l)
        nl = l
        possible_tag = None
        if m_p:
            possible_key = m_p.group(2) + m_p.group(3)
            possible_tag = tags_dict.get(possible_key)
            if possible_tag:
                link_2_tag = '[' + possible_key + '](#' + possible_tag + ')'
                nl = m_p.group(1) + '見' + link_2_tag + m_p.group(4) + '\n'
            else:
                log.warning("missing tags for: " + possible_key)
        new_lines.append(nl)

log.info("There are " + str(len(people)) + " people in this book.")

with open(out_file_path, 'w') as f:
    f.write(''.join(new_lines))