################################################################################
# tests/test_label_support.py: label_support.create paths.
################################################################################

from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools.label_support as lab


def test_create_returns_for_missing_file(monkeypatch: pytest.MonkeyPatch,
                                         tmp_path: Path) -> None:
    # A non-existent table file -> create() returns before any template work.
    made = []
    monkeypatch.setattr(lab, 'PdsTemplate',
                        lambda *a, **k: made.append('template'))
    lab.create(FCPath(tmp_path / 'nope_supplemental_index.tab'),
               FCPath(tmp_path / 'tmpl.lbl'))
    assert made == []


def _capture_template(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
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
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    host_template = host_dir / 'GO_0xxx_supplemental_index.lbl'
    table = tmp_path / 'GO_0001_supplemental_index.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               table_type='supplemental_index')
    assert captured['template_path'].name == 'GO_0xxx_supplemental_index.lbl'


def test_create_inventory_disables_preprocessor(monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    host_template = host_dir / 'inventory.lbl'
    table = tmp_path / 'GO_0001_inventory.csv'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               use_global_template=True, table_type='inventory')
    # 'inventory' in the stem -> preprocessor disabled.
    assert captured['kwargs']['preprocess'] is None
