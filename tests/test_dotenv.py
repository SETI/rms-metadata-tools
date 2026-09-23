################################################################################
# tests/test_dotenv.py: the package's .env lookup and loading.
################################################################################
"""Tests for metadata_tools._find_dotenv and metadata_tools._load_dotenv."""
import os
from pathlib import Path

import pytest
from filecache import FCPath

import metadata_tools as mt


def _checkout(root: Path, *, pyproject: bool = True, env: bool = True) -> Path:
    """Build a fake source-checkout layout and return its package __init__.py path.

    Parameters:
        root: Directory to become the checkout root.
        pyproject: True to create root/pyproject.toml.
        env: True to create root/.env.

    Returns:
        The path of root/src/metadata_tools/__init__.py.
    """
    init = root / 'src' / 'metadata_tools' / '__init__.py'
    init.parent.mkdir(parents=True)
    init.write_text('', encoding='utf-8')
    if pyproject:
        (root / 'pyproject.toml').write_text('', encoding='utf-8')
    if env:
        (root / '.env').write_text('', encoding='utf-8')
    return init


#===============================================================================
# _find_dotenv
#===============================================================================
def test_find_dotenv_explicit_variable_wins(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """$RMS_METADATA_ENV takes precedence over the cwd search and the checkout root."""
    explicit = tmp_path / 'custom.env'
    explicit.write_text('', encoding='utf-8')
    cwd = tmp_path / 'run'
    cwd.mkdir()
    (cwd / '.env').write_text('', encoding='utf-8')
    monkeypatch.setenv(mt.ENV_FILE_VAR, str(explicit))
    found = mt._find_dotenv(cwd=cwd, package_file=_checkout(tmp_path / 'repo'))
    assert found == FCPath(explicit)


def test_find_dotenv_explicit_variable_missing_file_raises(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An explicit $RMS_METADATA_ENV naming no file is an error, not a silent fallback."""
    monkeypatch.setenv(mt.ENV_FILE_VAR, str(tmp_path / 'absent.env'))
    with pytest.raises(FileNotFoundError, match='RMS_METADATA_ENV names a missing file'):
        mt._find_dotenv(cwd=tmp_path)


def test_find_dotenv_searches_up_from_cwd(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The nearest .env at or above the cwd is used before the checkout root."""
    monkeypatch.delenv(mt.ENV_FILE_VAR, raising=False)
    (tmp_path / 'work' / '.env').parent.mkdir()
    (tmp_path / 'work' / '.env').write_text('', encoding='utf-8')
    cwd = tmp_path / 'work' / 'runs' / '2026-09-23'
    cwd.mkdir(parents=True)
    found = mt._find_dotenv(cwd=cwd, package_file=_checkout(tmp_path / 'repo'))
    assert found == FCPath(tmp_path / 'work' / '.env')


def test_find_dotenv_falls_back_to_checkout_root(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no .env above the cwd, a source checkout's root .env is used."""
    monkeypatch.delenv(mt.ENV_FILE_VAR, raising=False)
    cwd = tmp_path / 'elsewhere'
    cwd.mkdir()
    repo = tmp_path / 'repo'
    found = mt._find_dotenv(cwd=cwd, package_file=_checkout(repo))
    assert found == FCPath(repo / '.env')


def test_find_dotenv_ignores_root_without_pyproject(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An installed package (no pyproject.toml beside src/) never reads its root .env."""
    monkeypatch.delenv(mt.ENV_FILE_VAR, raising=False)
    cwd = tmp_path / 'elsewhere'
    cwd.mkdir()
    init = _checkout(tmp_path / 'site', pyproject=False)
    assert mt._find_dotenv(cwd=cwd, package_file=init) is None


#===============================================================================
# _load_dotenv
#===============================================================================
def test_load_dotenv_sets_defaults_and_expands(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Lines become defaults; comments are skipped; $VAR refers to earlier lines."""
    # setenv-then-delenv registers the variables with monkeypatch, so the values
    # _load_dotenv writes are removed again at teardown.
    for name in ('MT_TEST_BASE', 'MT_TEST_DERIVED'):
        monkeypatch.setenv(name, '')
        monkeypatch.delenv(name)
    monkeypatch.setenv('MT_TEST_SHELL', 'from-shell')
    env = tmp_path / '.env'
    env.write_text('# comment\n'
                   '\n'
                   'MT_TEST_BASE = /data\n'
                   'MT_TEST_DERIVED=$MT_TEST_BASE/sub\n'
                   'MT_TEST_SHELL=from-file\n', encoding='utf-8')
    mt._load_dotenv(FCPath(env))
    assert os.environ['MT_TEST_BASE'] == '/data'
    assert os.environ['MT_TEST_DERIVED'] == '/data/sub'
    assert os.environ['MT_TEST_SHELL'] == 'from-shell'
