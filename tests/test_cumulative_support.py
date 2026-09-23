################################################################################
# tests/test_cumulative_support.py: _cat_rows walk + create_cumulative_indexes.
################################################################################
"""Tests for cumulative_support: _cat_rows and create_cumulative_indexes."""
import argparse
import types
from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools.cumulative_support as cum
import metadata_tools.geometry_support as geom
import metadata_tools.label_support as lab
import metadata_tools.util as util
from metadata_tools.config import get_host_config

hconf = get_host_config()


#===============================================================================
# _cat_rows
#===============================================================================
def test_cat_rows_concatenates_volumes(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """Rows from every volume are concatenated into the cumulative table file."""
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
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """Volumes listed in exclude contribute no rows."""
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
    assert written['content'] == ['x']


def test_cat_rows_inventory_uses_csv(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """The inventory table is written with a .csv suffix."""
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
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """A volume without the table file contributes nothing; nothing is written."""
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
    assert wrote == []


def test_cat_rows_labels_only_relabels_existing_table(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """labels_only regenerates the cumulative label without rewriting the table."""
    root = tmp_path / 'GO_0xxx'
    vdir = root / 'GO_0001'
    vdir.mkdir(parents=True)
    (vdir / 'GO_0001_sky_summary.tab').write_text('new\r\n', encoding='utf-8')
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()
    cumulative_file = cumulative_dir / 'GO_0999_sky_summary.tab'
    cumulative_file.write_text('old\r\n', encoding='utf-8')
    monkeypatch.setattr(hconf, 'get_volume_id', lambda p: FCPath(p).name)
    wrote: list[Any] = []
    monkeypatch.setattr(util, 'write_txt_file', lambda *a: wrote.append(a))
    labeled: list[Any] = []
    monkeypatch.setattr(lab, 'create',
                        lambda path, *a, **k: labeled.append((path, k['table_type'])))
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.SkyTable(level='summary'),
                  labels_only=True)
    assert wrote == []
    assert labeled == [(FCPath(cumulative_file), 'SKY_SUMMARY')]
    assert cumulative_file.read_bytes() == b'old\r\n'


def test_cat_rows_labels_only_warns_on_missing_table(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """labels_only with no existing cumulative table logs a warning and writes nothing."""
    import metadata_tools.common as com

    root = tmp_path / 'GO_0xxx'
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir(parents=True)
    warnings: list[Any] = []
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None,
                            warning=lambda msg, *a: warnings.append(msg % a)))
    labeled: list[Any] = []
    monkeypatch.setattr(lab, 'create', lambda *a, **k: labeled.append(a))
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.InventoryTable(),
                  labels_only=True)
    assert labeled == []
    assert warnings == ['No cumulative inventory table at %s; label skipped.'
                        % FCPath(cumulative_dir / 'GO_0999_inventory.csv')]


#===============================================================================
# get_args / create_cumulative_indexes
#===============================================================================
def test_get_args_parses_exclude() -> None:
    """--exclude collects volume IDs into args.exclude."""
    parser = cum.get_args(host='GO')
    args = parser.parse_args(['/out', '--exclude', 'GO_0999'])
    assert args.exclude == ['GO_0999']


def test_get_args_parses_labels() -> None:
    """--labels sets args.labels."""
    parser = cum.get_args(host='GO')
    args = parser.parse_args(['/out', '--labels'])
    assert args.labels is True


def test_get_args_rejects_pattern() -> None:
    """--pattern is not offered by the cumulative stage."""
    parser = cum.get_args(host='GO')
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['/out', '--pattern', '*.LBL'])
    assert excinfo.value.code == 2


def test_create_cumulative_indexes_passes_labels_only(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """args.labels reaches every _cat_rows pass as labels_only."""
    seen: list[Any] = []
    monkeypatch.setattr(cum, '_cat_rows',
                        lambda *a, **k: seen.append(k.get('labels_only')))
    args = argparse.Namespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                              volumes=None, exclude=None, labels=True)
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index', args=args)
    assert seen == [True] * 5


def test_create_cumulative_indexes_fires_five_cat_rows(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """All five cumulative tables get a _cat_rows pass; the sun table is not wired in."""
    calls: list[Any] = []
    monkeypatch.setattr(cum, '_cat_rows',
                        lambda *a, **k: calls.append((type(a[4]).__name__, a[4].level)))
    args = argparse.Namespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                              volumes=None, exclude=None, labels=False)
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index', args=args)
    # No sun table: it is not wired in (see geometry_support.tables.SunTable).
    assert calls == [('SkyTable', 'summary'), ('BodyTable', 'summary'),
                     ('RingTable', 'summary'), ('InventoryTable', None),
                     ('IndexTable', 'index')]


def test_create_cumulative_indexes_uses_args_exclude_over_parameter(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """A user-supplied --exclude (args.exclude) must override the exclude= parameter."""
    excludes_seen: list[list[str] | None] = []
    monkeypatch.setattr(cum, '_cat_rows',
                        lambda *a, **k: excludes_seen.append(k.get('exclude')))
    args = argparse.Namespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                              volumes=None, exclude=['GO_0016'], labels=False)
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index',
                                  args=args,
                                  exclude=['GO_0999'])
    assert excludes_seen == [['GO_0016']] * 5


def test_create_cumulative_indexes_falls_back_to_parameter_when_args_exclude_unset(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """With no --exclude on the command line, the host's configured default must be used."""
    excludes_seen: list[list[str] | None] = []
    monkeypatch.setattr(cum, '_cat_rows',
                        lambda *a, **k: excludes_seen.append(k.get('exclude')))
    args = argparse.Namespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                              volumes=None, exclude=None, labels=False)
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index',
                                  args=args,
                                  exclude=['GO_0999'])
    assert excludes_seen == [['GO_0999']] * 5
