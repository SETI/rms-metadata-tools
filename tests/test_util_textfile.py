################################################################################
# tests/test_util_textfile.py: read/write/append text files.
################################################################################
"""Tests for the read/write/append text-file helpers in util.py."""
from pathlib import Path

import pytest
from filecache import FCPath

import metadata_tools.util as util


#===============================================================================
# write_txt_file / read_txt_file
#===============================================================================
def test_write_then_read_roundtrip_list(tmp_path: Path) -> None:
    """A written list of lines reads back identically."""
    path = FCPath(tmp_path / 'a.txt')
    util.write_txt_file(path, ['one', 'two', 'three'])
    assert util.read_txt_file(path) == ['one', 'two', 'three']


def test_write_uses_requested_terminator(tmp_path: Path) -> None:
    """An explicit terminator ends every written line."""
    path = tmp_path / 'crlf.txt'
    util.write_txt_file(FCPath(path), ['x', 'y'], terminator='\r\n')
    assert path.read_bytes() == b'x\r\ny\r\n'


def test_write_terminator_none_infers_from_content(tmp_path: Path) -> None:
    """terminator=None infers the terminator from the string content."""
    path = tmp_path / 'lf.txt'
    util.write_txt_file(FCPath(path), 'a\nb', terminator=None)
    assert path.read_bytes() == b'a\nb\n'


def test_read_as_string(tmp_path: Path) -> None:
    """as_string=True returns the joined file content."""
    path = FCPath(tmp_path / 'b.txt')
    util.write_txt_file(path, ['p', 'q'], terminator='\n')
    assert util.read_txt_file(path, as_string=True, terminator='\n') == 'p\nq\n'


def test_write_terminator_none_infers_crlf_from_list(tmp_path: Path) -> None:
    """A CRLF ending on the first element sets CRLF for the whole file."""
    path = tmp_path / 'list_crlf.txt'
    util.write_txt_file(FCPath(path), ['a\r\n', 'b'], terminator=None)
    assert path.read_bytes() == b'a\r\nb\r\n'


#===============================================================================
# append_txt_file
#===============================================================================
def test_append_to_new_file_writes_content_once(tmp_path: Path) -> None:
    """Appending to a file that does not yet exist writes its content once."""
    path = FCPath(tmp_path / 'new.txt')
    util.append_txt_file(path, ['lineA', 'lineB'])
    assert util.read_txt_file(path) == ['lineA', 'lineB']


def test_append_to_existing_file_grows_once(tmp_path: Path) -> None:
    """Appending to an existing file adds the lines after the current content."""
    path = FCPath(tmp_path / 'existing.txt')
    util.write_txt_file(path, ['first'])
    util.append_txt_file(path, ['second'])
    assert util.read_txt_file(path) == ['first', 'second']


def test_append_to_existing_terminator_none_infers_from_list(tmp_path: Path) -> None:
    """terminator=None on append infers the terminator from the appended list."""
    path = FCPath(tmp_path / 'existing2.txt')
    util.write_txt_file(path, ['first'], terminator='\n')
    util.append_txt_file(path, ['second'], terminator=None)
    assert util.read_txt_file(path, terminator='\n') == ['first', 'second']


#===============================================================================
# environment-variable expansion
#===============================================================================
def test_write_and_read_expand_env_vars(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """$VAR path references expand from the environment on write and read."""
    monkeypatch.setenv('TEXTDIR', str(tmp_path))
    util.write_txt_file('$TEXTDIR/env.txt', ['one', 'two'])
    assert (tmp_path / 'env.txt').exists()
    assert util.read_txt_file('$TEXTDIR/env.txt') == ['one', 'two']
