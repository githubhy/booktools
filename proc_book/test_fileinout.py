from fileinout import FilenameInOut
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
