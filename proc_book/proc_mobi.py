import logging
import argparse
import mobi
from bs4 import BeautifulSoup
from utils import FilenameInOut, MdIdAttacher

parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('--test_cat', type=str, default=None)
parser.add_argument('file_name_or_dir')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")


fn = FilenameInOut(args.file_name_or_dir, '.mobi', args.output_dir, '.Rmd')
in_filenames = fn.get_in_names()
out_filenames = fn.get_out_names()
for i in range(len(in_filenames)):
    lines = []
    tempdir, filepath = mobi.extract(in_filenames[i])
    with open(filepath, "r") as f:
        page = f.read()
        soup = BeautifulSoup(page, 'html.parser')
        for div in soup.find_all('div'):
            for p in div.find_all('p'):
                if p.has_attr('align') and p["align"] == 'center':
                    prefix = '# '
                    text = p.text
                # if p.a and p.a.has_attr('href'):
                #     print('[{0}]({1})\n'.format(p.text, p.a["href"]))
                elif p.text.startswith('○'):
                    prefix = '## '
                    text = p.text[1:]
                elif p.text.startswith('◎'):
                    prefix = '## '
                    text = p.text[1:]
                else:
                    prefix = ''
                    text = p.text
                lines.append('{0}{1}'.format(prefix, text))

    attacher = MdIdAttacher('\n\n'.join(lines))

    with open(out_filenames[i], "w") as f:
        f.write(attacher.attached_full)
