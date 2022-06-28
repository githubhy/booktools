from utils import FilenameInOut
from pathlib import Path
import os
import pytest
import random

# https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html#the-tmp-path-fixture
# https://pytest.org/en/7.1.x/explanation/fixtures.html#improvements-over-xunit-style-setup-teardown-functions
@pytest.fixture
def temp_files():
    temp_filenames = ['test_' + str(random.random()) for i in range(3)]
    return temp_filenames

@pytest.fixture
def in_files(tmp_path, temp_files):
    return [os.path.join(tmp_path, f) + '.txt' for f in temp_files]

@pytest.fixture
def out_dir(tmp_path):
    return os.path.join(tmp_path, 'test_out')

@pytest.fixture(autouse=True)
def file_env(in_files):
    for f in in_files:
        Path(f).touch()
    yield None

def test_valid_file():
    fn = FilenameInOut('test.txt')
    assert fn.get_in_names() == ['test.txt']
    assert fn.get_out_names() == ['test.txt']

def test_valid_dir(tmp_path, in_files):
    fn = FilenameInOut(tmp_path, '.txt')
    assert set(fn.get_in_names()) == set(in_files)
    assert set(fn.get_out_names()) == set(in_files)

def test_valid_dir_no_ext(tmp_path):
    with pytest.raises(Exception, match=r"ext_in"):
        FilenameInOut(tmp_path)

def test_in_file_out_dir(out_dir):
    assert not os.path.isdir(out_dir)
    fn = FilenameInOut('test.txt', dir_out=out_dir)
    assert os.path.isdir(out_dir)
    assert fn.get_out_names() == [os.path.join(out_dir, 'test.txt')]

def test_valid_out_dir(tmp_path, out_dir, temp_files):
    fn = FilenameInOut(tmp_path, '.txt', out_dir)
    assert set(fn.get_out_names()) == set([os.path.join(out_dir, f) + '.txt' for f in temp_files])

def test_valid_out_dir_w_ext(tmp_path, out_dir, temp_files):
    fn = FilenameInOut(tmp_path, '.txt', out_dir, '.Rmd')
    assert set(fn.get_out_names()) == set([os.path.join(out_dir, f) + '.Rmd' for f in temp_files])



from utils import MdIdAttacher, MdParagraphId

@pytest.fixture
def md_fsm():
    return MdParagraphId('test')

def test_md_fsm_initial(md_fsm):
    md_fsm.reset()
    assert md_fsm.state == 'outside'
    md_fsm.proc_line('## x')
    assert md_fsm.state == 'outside'
    md_fsm.proc_line('88')
    assert md_fsm.state == 'outside'
    md_fsm.proc_line('# x')
    assert md_fsm.state == 'chap_title'

def test_md_fsm_normal_trans(md_fsm):
    md_fsm.reset()
    md_fsm.proc_line('# x')
    assert md_fsm.state == 'chap_title'
    md_fsm.proc_line('## y')
    assert md_fsm.state == 'sec_title'
    md_fsm.proc_line('## z')
    assert md_fsm.state == 'sec_title'
    md_fsm.proc_line('# x')
    assert md_fsm.state == 'chap_title'
    md_fsm.proc_line('aaa')
    assert md_fsm.state == 'chap'
    md_fsm.proc_line('bbb')
    assert md_fsm.state == 'chap'
    md_fsm.proc_line('# y')
    assert md_fsm.state == 'chap_title'
    md_fsm.proc_line('ccc')
    md_fsm.proc_line('## aa')
    assert md_fsm.state == 'sec_title'
    md_fsm.proc_line('ddd')
    assert md_fsm.state == 'sec'
    md_fsm.proc_line('eee')
    assert md_fsm.state == 'sec'
    md_fsm.proc_line('## dd')
    assert md_fsm.state == 'sec_title'
    md_fsm.proc_line('fff')
    md_fsm.proc_line('# xx')
    assert md_fsm.state == 'chap_title'

test_string = '''\


# Chapter 1

This is the 1st paragraph in chapter 1.

This is the 2nd paragraph in chapter 1.
And the same paragraph beginning with a newline.

## Section 1.1

1st paragraph in section 1.

2nd paragraph in section 2.

## Section 1.2

1st paragraph in section 2.

# Chapter 2

This is chapter 2.

## Section 2.1

## Section 2.2

# Chapter 3

# Chapter 4

## Section 4.1

xxx
'''

def test_md_fsm_generated_tags(md_fsm):
    ls = iter(test_string.split('\n\n'))
    md_fsm.reset()
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_1-1'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_1-2'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_1-Section_1.1-1'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_1-Section_1.1-2'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_1-Section_1.2-1'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_2-1'
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == ''
    md_fsm.proc_line(next(ls))
    assert md_fsm.tag == 'Chapter_4-Section_4.1-1'
    
res_string = '''\


# Chapter 1

1. []{#Chapter_1-1}
This is the 1st paragraph in chapter 1.

2. []{#Chapter_1-2}
This is the 2nd paragraph in chapter 1.
And the same paragraph beginning with a newline.

## Section 1.1

1. []{#Chapter_1-Section_1.1-1}
1st paragraph in section 1.

2. []{#Chapter_1-Section_1.1-2}
2nd paragraph in section 2.

## Section 1.2

1. []{#Chapter_1-Section_1.2-1}
1st paragraph in section 2.

# Chapter 2

1. []{#Chapter_2-1}
This is chapter 2.

## Section 2.1

## Section 2.2

# Chapter 3

# Chapter 4

## Section 4.1

1. []{#Chapter_4-Section_4.1-1}
xxx
'''

def test_md_id_attacher():
    attacher = MdIdAttacher(test_string)
    assert attacher.attached_full == res_string
