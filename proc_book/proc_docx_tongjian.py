import logging
import argparse
import re
from docx import Document
from utils import FilenameInOut, flatten, MdIdAttacher, CommentConverter


parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('file_name')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")

def iter_text(paragraphs):
    dyn = ''
    for p in paragraphs:
        # m = re.search(r'(?P<chap>卷第[一二三四五六七八九十百]+)', p.text)
        # if m:
        #     yield '{0}{1}'.format('# ', m.group('chap'))
        m = re.search(r'^\s*.{0,2}(?P<sec>(?P<dyn>[\u4e00-\u9fa5]纪)[一二三四五六七八九十]+)】?(?P<other>.*)', p.text)
        if m:
            if dyn != m.group('dyn'):
                dyn = m.group('dyn')
                yield '{0}{1}'.format('# ', dyn)
            yield '{0}{1}'.format('## ', m.group('sec'))
            yield m.group('other')
        else:
            if p.text.strip():
                yield p.text.strip()


############### Main ##############
fn = FilenameInOut(args.file_name, dir_out=args.output_dir, ext_out='.Rmd')
doc = Document(fn.get_in_names()[0])
cmt_conv = CommentConverter(iter_text(doc.paragraphs), '〔〕')
attacher = MdIdAttacher('\n\n'.join([text.strip() for text in cmt_conv.converted if text.strip()]))
with open(fn.get_out_names()[0], 'w') as f:
    f.write(attacher.attached_full)