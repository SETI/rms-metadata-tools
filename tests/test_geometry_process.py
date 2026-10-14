################################################################################
# tests/test_geometry_process.py: get_args + process_tables walk.
################################################################################
"""Tests for geometry get_args and the process_tables volume walk."""
import types
from pathlib import Path
from typing import Any

import oops
import pytest
from filecache import FCPath

from metadata_tools.geometry_support import process as proc


def _args(tree: FCPath, **over: Any) -> types.SimpleNamespace:
    """Build a SimpleNamespace mimicking the parsed geometry arguments.

    Parameters:
        tree: Path used for both metadata_tree and output_tree.
        over: Attribute overrides applied on top of the defaults.

    Returns:
        The populated namespace.
    """
    ns = types.SimpleNamespace(
        metadata_tree=str(tree), output_tree=str(tree), new_only=False,
        labels=False, volumes=None, exclude=None, first=None, sampling=8,
        body_samples=16, no_body_meshgrids=False, pattern=None)
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


def _tree(tmp_path: Path) -> FCPath:
    """Create a GO_0xxx tree with two empty volume directories.

    Returns:
        The collection root as an FCPath.
    """
    root = tmp_path / 'GO_0xxx'
    for vol in ('GO_0001', 'GO_0002'):
        (root / vol).mkdir(parents=True)
    return FCPath(root)


#===============================================================================
# get_args
#===============================================================================
def test_get_args_defaults_and_parse() -> None:
    """--sampling parses over the provided default."""
    parser = proc.get_args(host='GO', sampling=8)
    args = parser.parse_args(['/meta', '/out', '--sampling', '4'])
    assert args.sampling == 4


def test_get_args_body_samples_default_and_override() -> None:
    """--body-samples defaults to 16 and parses over the provided default."""
    parser = proc.get_args(host='GO')
    assert parser.parse_args(['/meta', '/out']).body_samples == 16
    assert parser.parse_args(['/meta', '/out', '--body-samples', '32']).body_samples == 32
    assert proc.get_args(host='GO', body_samples=8).parse_args(
        ['/meta', '/out']).body_samples == 8


def test_get_args_no_body_meshgrids_is_off_by_default() -> None:
    """--no-body-meshgrids is a flag, unset unless given."""
    parser = proc.get_args(host='GO')
    assert parser.parse_args(['/meta', '/out']).no_body_meshgrids is False
    assert parser.parse_args(['/meta', '/out', '--no-body-meshgrids']).no_body_meshgrids is True


@pytest.mark.parametrize(('disabled', 'expected'), [(False, 16), (True, 0)])
def test_process_tables_passes_body_samples(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
        disabled: bool, expected: int) -> None:
    """The suite gets the sample count, or 0 when body meshgrids are disabled."""
    tree = _tree(tmp_path)
    seen: list[int] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            seen.append(k['body_samples'])

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree, no_body_meshgrids=disabled))  # type: ignore[arg-type]
    assert seen == [expected, expected]


def test_get_args_new_only_is_a_flag() -> None:
    """--new_only is a plain flag that defaults to False and takes no values."""
    parser = proc.get_args(host='GO')
    assert parser.parse_args(['/meta', '/out']).new_only is False
    assert parser.parse_args(['/meta', '/out', '--new_only']).new_only is True
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['/meta', '/out', '--new_only', 'GO_0001'])
    assert excinfo.value.code == 2


#===============================================================================
# process_tables
#===============================================================================

def test_process_tables_builds_suite(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """One Suite is built and created per volume directory."""
    tree = _tree(tmp_path)
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, outdir: str, template_path: Any,
                     metadata_dir: Any, **kwargs: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, labels_only: bool = False, pattern: Any = None) -> None:
            built.append('created')

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree))  # type: ignore[arg-type]
    assert 'GO_0001' in built
    assert built.count('created') == 2


def test_process_tables_limits_quick_caches(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The oops QuickPath and QuickFrame caches are cut to QUICK_CACHE_SIZE."""
    quick = oops.config.QUICK.dictionary
    monkeypatch.setitem(quick, 'quickpath_cache_size', 40)
    monkeypatch.setitem(quick, 'quickframe_cache_size', 40)

    class FakeSuite:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(_tree(tmp_path)))  # type: ignore[arg-type]
    assert quick['quickpath_cache_size'] == proc.QUICK_CACHE_SIZE
    assert quick['quickframe_cache_size'] == proc.QUICK_CACHE_SIZE


def test_process_tables_excludes_volume(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Volumes listed in exclude are skipped."""
    tree = _tree(tmp_path)
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree),  # type: ignore[arg-type]
                        exclude=['GO_0002'])
    assert built == ['GO_0001']


def test_process_tables_excludes_the_cumulative_volume_by_default(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no exclude at all, the tree's cumulative volume is skipped."""
    tree = _tree(tmp_path)
    (Path(tree.as_posix()) / 'GO_0999').mkdir()
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree))  # type: ignore[arg-type]
    assert sorted(built) == ['GO_0001', 'GO_0002']


def test_process_tables_uses_args_exclude_over_parameter(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A user-supplied --exclude (args.exclude) must override the exclude= parameter."""
    tree = _tree(tmp_path)
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree, exclude=['GO_0001']),  # type: ignore[arg-type]
                        exclude=['GO_0002'])
    assert built == ['GO_0002']


def test_process_tables_falls_back_to_parameter_when_args_exclude_unset(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no --exclude on the command line, the host's configured default must be used."""
    tree = _tree(tmp_path)
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree, exclude=None),  # type: ignore[arg-type]
                        exclude=['GO_0001'])
    assert built == ['GO_0002']


def test_process_tables_new_only_skips_processed_volume(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With new_only, a volume that already has an inventory file is skipped."""
    tree = _tree(tmp_path)
    (Path(tree.as_posix()) / 'GO_0001' / 'GO_0001_inventory.csv').write_text(
        'x\r\n', encoding='utf-8')
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree, new_only=True))  # type: ignore[arg-type]
    assert built == ['GO_0002']


def test_process_tables_volumes_disable_new_only(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An explicit volumes list processes those volumes even under new_only."""
    tree = _tree(tmp_path)
    (Path(tree.as_posix()) / 'GO_0001' / 'GO_0001_inventory.csv').write_text(
        'x\r\n', encoding='utf-8')
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree, new_only=True),  # type: ignore[arg-type]
                        volumes=['GO_0001'])
    assert built == ['GO_0001']


def test_process_tables_volumes_filter(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Only volumes named in the volumes filter are processed."""
    tree = _tree(tmp_path)
    built: list[str] = []

    class FakeSuite:
        def __init__(self, indir: str, *a: Any, **k: Any) -> None:
            built.append(FCPath(indir).name)

        def create(self, **k: Any) -> None:
            pass

    monkeypatch.setattr(proc, 'Suite', FakeSuite)
    proc.process_tables('GO_0xxx_supplemental_index',
                        args=_args(tree),  # type: ignore[arg-type]
                        volumes=['GO_0001'])
    assert built == ['GO_0001']
