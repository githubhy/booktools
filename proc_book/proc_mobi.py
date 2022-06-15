import os
import logging
import argparse
import mobi
from bs4 import BeautifulSoup

parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('--test_cat', type=str, default=None)
parser.add_argument('file_name_or_dir')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")


try:
    filenames = []
    filepath = ''
    if os.path.isdir(args.file_name_or_dir):
        filepath = args.file_name_or_dir
        for f in os.listdir(filepath):
            if f.endswith(".mobi"):
                filenames.append(f.replace('.mobi', ''))
    else:
        file_head, file_extension = os.path.splitext(args.file_name_or_dir)
        (filepath, filename) = os.path.split(file_head)
        filenames.append(filename)
except:
    log.error("No file name/dir specified or invalid file name/dir")
    exit(1)

in_filenames = ['{0}{1}'.format(os.path.join(filepath, f), '.mobi') for f in filenames]

if args.output_dir:
    os.makedirs(args.output_dir, exist_ok=True) 
    out_dir = args.output_dir
else:
    out_dir = filepath

out_filenames = ['{0}{1}'.format(os.path.join(out_dir, f), '.md') for f in filenames]

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

    with open(out_filenames[i], "w") as f:
        f.write('\n\n'.join(lines))
