import logging
import argparse
from fileinout import FilenameInOut
import re

parser = argparse.ArgumentParser(description='')
parser.add_argument('--output_dir', type=str, default=None)
parser.add_argument('file_name_or_dir')
args = parser.parse_args()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")


fn = FilenameInOut(args.file_name_or_dir, dir_out=args.output_dir)
in_filenames = fn.get_in_names()
out_filenames = fn.get_out_names()
for i in range(len(in_filenames)):
    with open(in_filenames[i], "r") as f:
        text = f.read()
        text = re.sub(r'\<(\w[\w\d]*)\>', r'<span class="\1">', text)
        text = re.sub(r'\<(/\w[\w\d]*)\>', r'</span>', text)
        text = re.sub(r'\{\.(\w[\w\d]*)\}\[', r'<span class="\1">', text)
        text = re.sub(r'\]\{\.(\w[\w\d]*)\}', r'</span>', text)

    with open(out_filenames[i], "w") as f:
        f.write(text)
