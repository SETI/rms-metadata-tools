################################################################################
# tests/test_cumulative_support.py: _cat_rows walk + create_cumulative_indexes.
################################################################################
import types
from pathlib import Path
from typing import Any

import host_config as hconf
import pytest
from filecache import FCPath

import metadata_tools.common as com
import metadata_tools.cumulative_support as cum
import metadata_tools.geometry_support as geom
import metadata_tools.label_support as lab
import metadata_tools.util as util


def _silent_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))


#===============================================================================
# _cat_rows
#===============================================================================
def test_cat_rows_concatenates_volumes(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _silent_logger(monkeypatch)
    root = tmp_path / 'GO_0xxx'
    for vol, line in [('GO_0001', 'a'), ('GO_0002', 'b')]:
        vdir = root / vol
        vdir.mkdir(parents=True)
        (vdir / f'{vol}_sky_summary.tab').write_text(line + '\r\n', encoding='utf-8')
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()

    monkeypatch.setattr(hconf, 'get_volume_id',
                        lambda p: FCPath(p).name)
    written: dict[str, Any] = {}
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, content: written.update(
                            {'path': path, 'content': content}))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: None)

    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.SkyTable(level='summary'))
    assert written['content'] == ['a', 'b']
    assert 'GO_0999_sky_summary.tab' in written['path'].name


def test_cat_rows_excludes_volume(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _silent_logger(monkeypatch)
    root = tmp_path / 'GO_0xxx'
    for vol in ('GO_0001', 'GO_0002'):
        vdir = root / vol
        vdir.mkdir(parents=True)
        (vdir / f'{vol}_sky_summary.tab').write_text('x\r\n', encoding='utf-8')
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()
    monkeypatch.setattr(hconf, 'get_volume_id', lambda p: FCPath(p).name)
    written: dict[str, Any] = {}
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, content: written.update({'content': content}))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: None)
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.SkyTable(level='summary'),
                  exclude=['GO_0002'])
    # Only GO_0001 contributes a row.
    assert written['content'] == ['x']


def test_cat_rows_inventory_uses_csv(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _silent_logger(monkeypatch)
    root = tmp_path / 'GO_0xxx'
    vdir = root / 'GO_0001'
    vdir.mkdir(parents=True)
    (vdir / 'GO_0001_inventory.csv').write_text('inv\r\n', encoding='utf-8')
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()
    monkeypatch.setattr(hconf, 'get_volume_id', lambda p: FCPath(p).name)
    written: dict[str, Any] = {}
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, content: written.update({'path': path}))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: None)
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.InventoryTable())
    assert written['path'].suffix == '.csv'


def test_cat_rows_skips_missing_table(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _silent_logger(monkeypatch)
    root = tmp_path / 'GO_0xxx'
    (root / 'GO_0001').mkdir(parents=True)  # no table file present
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()
    monkeypatch.setattr(hconf, 'get_volume_id', lambda p: FCPath(p).name)
    wrote: list[Any] = []
    monkeypatch.setattr(util, 'write_txt_file', lambda *a: wrote.append(a))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: None)
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.SkyTable(level='summary'))
    # No content -> nothing written.
    assert wrote == []


#===============================================================================
# get_args / create_cumulative_indexes
#===============================================================================
def test_get_args_parses_exclude() -> None:
    parser = cum.get_args(host='GO')
    args = parser.parse_args(['/out', '--exclude', 'GO_0999'])
    assert args.exclude == ['GO_0999']


def test_create_cumulative_indexes_fires_eight_cat_rows(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(cum, '_cat_rows',
                        lambda *a, **k: calls.append((type(a[4]).__name__, a[4].level)))
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
    args = types.SimpleNamespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                                 volumes=None, exclude=None)
    # SimpleNamespace stands in for an argparse.Namespace here.
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index',
                                  args=args)  # type: ignore[arg-type]
    assert len(calls) == 8
    assert ('SkyTable', 'summary') in calls
    assert ('IndexTable', 'index') in calls
