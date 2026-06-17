################################################################################
# tests/test_util_textfile.py: read/write/append + expandvars.
################################################################################
from pathlib import Path
from typing import cast

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
# expandvars
#===============================================================================
def test_expandvars_expands_and_preserves_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('METADIR', '/data/meta')
    result = util.expandvars('$METADIR/index.tab')
    assert result == '/data/meta/index.tab'
    assert isinstance(result, str)


def test_expandvars_preserves_scheme_and_fcpath_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('BUCKET', 'my-bucket')
    result = util.expandvars(FCPath('gs://$BUCKET/x'))
    # expandvars() returns str | Path | FCPath; an FCPath in -> FCPath out.
    assert cast(FCPath, result).as_posix() == 'gs://my-bucket/x'
    assert isinstance(result, FCPath)


def test_expandvars_preserves_path_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('HERE', '/tmp/here')
    result = util.expandvars(Path('$HERE/file'))
    assert isinstance(result, Path)
    assert result == Path('/tmp/here/file')
