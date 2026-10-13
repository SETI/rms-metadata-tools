################################################################################
# tests/test_label_support.py: label_support.create paths.
################################################################################
"""Tests for the label_support.create template paths."""

from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools.label_support as lab
from metadata_tools.column_grammar import strip_comments


def test_create_returns_for_missing_file(monkeypatch: pytest.MonkeyPatch,
                                         tmp_path: Path) -> None:
    """A missing table file makes create() return before any template work."""
    made = []
    monkeypatch.setattr(lab, 'PdsTemplate',
                        lambda *a, **k: made.append('template'))
    lab.create(FCPath(tmp_path / 'nope_supplemental_index.tab'),
               FCPath(tmp_path / 'tmpl.lbl'))
    assert made == []


def test_create_rejects_filename_without_volume_id(tmp_path: Path) -> None:
    """A table filename with no underscore cannot yield a volume ID."""
    table = tmp_path / 'noprefix.tab'
    table.write_text('x', encoding='utf-8')
    with pytest.raises(ValueError, match=r"'noprefix\.tab' does not start with a volume id"):
        lab.create(FCPath(table), FCPath(tmp_path / 'tmpl.lbl'))


def test_create_inventory_measures_its_fields(monkeypatch: pytest.MonkeyPatch,
                                              tmp_path: Path) -> None:
    """The inventory label takes its field widths from the table's first row."""
    captured = _capture_template(monkeypatch)
    table = tmp_path / 'COISS_2001_inventory.csv'
    filespec = 'data/1455855935_1456049320/N1455970236_1.LBL'
    table.write_text(f'"COISS_2001","{filespec}","SATURN,TITAN"\r\n', encoding='utf-8')
    lab.create(FCPath(table), FCPath(tmp_path / 'templates' / 'x.lbl'),
               use_global_template=True, table_type='inventory')
    assert captured['fields']['VOLUME_ID'] == 'COISS_2001'
    assert captured['fields']['VOLUME_ID_BYTES'] == 10
    assert captured['fields']['FILESPEC_BYTES'] == 44


def test_create_inventory_without_a_complete_row(monkeypatch: pytest.MonkeyPatch,
                                                 tmp_path: Path) -> None:
    """An empty inventory still labels its volume ID field."""
    captured = _capture_template(monkeypatch)
    table = tmp_path / 'GO_0001_inventory.csv'
    table.write_text('', encoding='utf-8')
    lab.create(FCPath(table), FCPath(tmp_path / 'templates' / 'x.lbl'),
               use_global_template=True, table_type='inventory')
    assert captured['fields']['VOLUME_ID_BYTES'] == 7
    assert captured['fields']['FILESPEC_BYTES'] == 0


def test_create_supplemental_index_has_no_inventory_fields(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Only the inventory label is given the inventory field widths."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    table = tmp_path / 'GO_0001_supplemental_index.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_dir / 'GO_0xxx_supplemental_index.lbl'),
               table_type='supplemental_index')
    assert captured['fields'] == {'VOLUME_ID': 'GO_0001', 'TABLE_TYPE': 'SUPPLEMENTAL_INDEX'}


def _capture_template(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Install a PdsTemplate stub that records constructor and write arguments.

    Returns:
        The dict the stub fills with template_path, kwargs, fields, and
        label_path.
    """
    captured: dict[str, Any] = {}

    class FakeTemplate:
        def __init__(self, template_path: Any, **kwargs: Any) -> None:
            captured['template_path'] = template_path
            captured['kwargs'] = kwargs

        def write(self, fields: Any, label_path: Any = None, mode: Any = None) -> None:
            captured['fields'] = fields
            captured['label_path'] = label_path

    monkeypatch.setattr(lab, 'PdsTemplate', FakeTemplate)
    return captured


def test_create_global_template_path(monkeypatch: pytest.MonkeyPatch,
                                     tmp_path: Path) -> None:
    """use_global_template resolves the template under the global template dir."""
    captured = _capture_template(monkeypatch)
    host_template = tmp_path / 'host' / 'GO_0xxx_body_summary.lbl'
    host_template.parent.mkdir(parents=True)
    table = tmp_path / 'GO_0001_body_summary.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               use_global_template=True, table_type='body_summary')
    # Global path: template resolved under the global template dir.
    assert captured['template_path'].name == 'body_summary.lbl'
    assert captured['fields']['VOLUME_ID'] == 'GO_0001'
    assert captured['fields']['TABLE_TYPE'] == 'BODY_SUMMARY'


def test_create_host_template_path(monkeypatch: pytest.MonkeyPatch,
                                   tmp_path: Path) -> None:
    """Without the global flag, the host template path is used as given."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    host_template = host_dir / 'GO_0xxx_supplemental_index.lbl'
    table = tmp_path / 'GO_0001_supplemental_index.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               table_type='supplemental_index')
    assert captured['template_path'].name == 'GO_0xxx_supplemental_index.lbl'


def test_create_inventory_strips_only_comments(monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:
    """An 'inventory' table stem takes only the comment strip."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    host_template = host_dir / 'inventory.lbl'
    table = tmp_path / 'GO_0001_inventory.csv'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               use_global_template=True, table_type='inventory')
    # 'inventory' in the stem -> no column preprocessors, only the strip.
    assert captured['kwargs']['preprocess'] == [strip_comments]
