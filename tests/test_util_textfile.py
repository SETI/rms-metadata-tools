################################################################################
# tests/test_util_textfile.py: read/write/append text files.
################################################################################
from pathlib import Path

import pytest
from filecache import FCPath

import metadata_tools.util as util


#===============================================================================
# write_txt_file / read_txt_file
#===============================================================================
def test_write_then_read_roundtrip_list(tmp_path: Path) -> None:
    path = FCPath(tmp_path / 'a.txt')
    util.write_txt_file(path, ['one', 'two', 'three'])
    assert util.read_txt_file(path) == ['one', 'two', 'three']


def test_write_uses_requested_terminator(tmp_path: Path) -> None:
    path = tmp_path / 'crlf.txt'
    util.write_txt_file(FCPath(path), ['x', 'y'], terminator='\r\n')
    assert path.read_bytes() == b'x\r\ny\r\n'


def test_write_terminator_none_infers_from_content(tmp_path: Path) -> None:
    path = tmp_path / 'lf.txt'
    util.write_txt_file(FCPath(path), 'a\nb', terminator=None)
    assert path.read_bytes() == b'a\nb\n'


def test_read_as_string(tmp_path: Path) -> None:
    path = FCPath(tmp_path / 'b.txt')
    util.write_txt_file(path, ['p', 'q'], terminator='\n')
    assert util.read_txt_file(path, as_string=True, terminator='\n') == 'p\nq\n'


def test_write_terminator_none_infers_crlf_from_list(tmp_path: Path) -> None:
    path = tmp_path / 'list_crlf.txt'
    # First element ends in CRLF -> CRLF terminator inferred for the whole file.
    util.write_txt_file(FCPath(path), ['a\r\n', 'b'], terminator=None)
    assert path.read_bytes() == b'a\r\nb\r\n'


#===============================================================================
# append_txt_file
#===============================================================================
def test_append_to_new_file_writes_content_once(tmp_path: Path) -> None:
    # Appending to a brand-new file writes its content exactly once.
    path = FCPath(tmp_path / 'new.txt')
    util.append_txt_file(path, ['lineA', 'lineB'])
    assert util.read_txt_file(path) == ['lineA', 'lineB']


def test_append_to_existing_file_grows_once(tmp_path: Path) -> None:
    path = FCPath(tmp_path / 'existing.txt')
    util.write_txt_file(path, ['first'])
    util.append_txt_file(path, ['second'])
    assert util.read_txt_file(path) == ['first', 'second']


def test_append_to_existing_terminator_none_infers_from_list(tmp_path: Path) -> None:
    path = FCPath(tmp_path / 'existing2.txt')
    util.write_txt_file(path, ['first'], terminator='\n')
    util.append_txt_file(path, ['second'], terminator=None)
    assert util.read_txt_file(path, terminator='\n') == ['first', 'second']


#===============================================================================
# environment-variable expansion
#===============================================================================
def test_write_and_read_expand_env_vars(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('TEXTDIR', str(tmp_path))
    util.write_txt_file('$TEXTDIR/env.txt', ['one', 'two'])
    assert (tmp_path / 'env.txt').exists()
    assert util.read_txt_file('$TEXTDIR/env.txt') == ['one', 'two']
