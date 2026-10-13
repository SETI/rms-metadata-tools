################################################################################
# tests/test_label_support.py: label_support.create paths.
################################################################################
"""Tests for the label_support.create template paths."""

from pathlib import Path
from typing import Any

import pytest
from filecache import FCPath

import metadata_tools
import metadata_tools.defs as defs
import metadata_tools.label_support as lab
from metadata_tools.column_grammar import (
    expand_format_references,
    merge_column_definitions,
    strip_comments,
)
from metadata_tools.config import get_host_config


def test_create_returns_for_missing_file(monkeypatch: pytest.MonkeyPatch,
                                         tmp_path: Path) -> None:
    """A missing table file makes create() return before any template work."""
    made = []
    monkeypatch.setattr(lab, 'HostTemplate',
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
               table_type='inventory')
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
               table_type='inventory')
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
    assert captured['fields'] == {'VOLUME_ID': 'GO_0001', 'TABLE_TYPE': 'SUPPLEMENTAL_INDEX',
                                  'FOV_BORDER': '0.15 milliradians', 'SAMPLING': None,
                                  'BODY_SAMPLES': None}


_BORDER = '0.15 milliradians'


def test_border_text_is_an_angle(monkeypatch: pytest.MonkeyPatch) -> None:
    """The border reads as an angle, and a host with none has nothing to state."""
    host = get_host_config()
    monkeypatch.setattr(host, 'BORDER', 1.5e-4, raising=False)
    assert lab._border_text() == _BORDER
    monkeypatch.setattr(host, 'BORDER', 0., raising=False)
    assert lab._border_text() is None


def test_create_states_the_border_and_the_sampling(monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path: Path) -> None:
    """A label is given the host's border and the sampling its caller states."""
    captured = _capture_template(monkeypatch)
    monkeypatch.setattr(get_host_config(), 'BORDER', 1.5e-4, raising=False)
    table = tmp_path / 'GO_0001_body_summary.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(tmp_path / 'templates' / 'x.lbl'),
               table_type='body_summary', fields={'SAMPLING': 4, 'BODY_SAMPLES': 0})
    assert captured['fields']['FOV_BORDER'] == _BORDER
    assert captured['fields']['SAMPLING'] == 4
    assert captured['fields']['BODY_SAMPLES'] == 0


def _render(tmp_path: Path, kind: str, fields: dict[str, Any]) -> str:
    """Generate a label from a shared summary template and return its text.

    The template is run as the label write runs it, less the table
    preprocessor, which would need a real table to describe.

    Parameters:
        tmp_path: The pytest temporary directory.
        kind: The table kind.
        fields: Values to give the template, over the defaults of create().

    Returns:
        The text of the label, with its line breaks removed.
    """
    host_dir = Path(metadata_tools.__file__).parent / 'hosts' / 'GO_0xxx' / 'templates'
    table = tmp_path / f'GO_0001_{kind}_summary.tab'
    table.write_text('row\r\n', encoding='utf-8')
    template = lab.HostTemplate(
        FCPath(defs.GLOBAL_TEMPLATE_PATH) / f'{kind}_summary.lbl', crlf=True,
        preprocess=[strip_comments, expand_format_references, merge_column_definitions],
        includes=[FCPath(host_dir), defs.GLOBAL_TEMPLATE_PATH])
    defaults = {'LABEL_VALUE': lambda name: 'FIXED_LENGTH', 'FOV_BORDER': None,
                'SAMPLING': None, 'BODY_SAMPLES': None}
    label = template.generate(defaults | fields,
                              label_path=table.with_suffix('.lbl').as_posix())
    assert template.error_count == 0
    return ' '.join(label.split())


def test_body_label_states_the_sampling_it_was_generated_with(tmp_path: Path) -> None:
    """The body label reports the border, the sampling, and the body grids."""
    text = _render(tmp_path, 'body', {'FOV_BORDER': _BORDER, 'SAMPLING': 8, 'BODY_SAMPLES': 16})
    assert 'at intervals of no more than 8 pixels along each axis.' in text
    assert 'with no fewer than 16 samples across the body' in text
    assert 'on every side by 0.15 milliradians.' in text
    assert 'too small to have been captured' not in text
    assert 'regardless of obstruction or apparent body size."' in text


def test_body_label_without_body_grids_warns_of_small_bodies(tmp_path: Path) -> None:
    """With body grids disabled, a small body can fall between the samples."""
    text = _render(tmp_path, 'body', {'FOV_BORDER': _BORDER, 'SAMPLING': 8, 'BODY_SAMPLES': 0})
    assert 'samples across the body' not in text
    assert 'If a body is too small to have been captured by the sampling' in text


@pytest.mark.parametrize('kind', ['body', 'ring', 'sky'])
def test_label_says_nothing_it_was_not_told(tmp_path: Path, kind: str) -> None:
    """With no sampling stated and no host border, a label claims neither."""
    text = _render(tmp_path, kind, {})
    assert 'at intervals of' not in text
    assert 'samples across the body' not in text
    assert 'pointing uncertainty' not in text
    assert '$' not in text


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

    monkeypatch.setattr(lab, 'HostTemplate', FakeTemplate)
    return captured


def test_create_shared_template_path(monkeypatch: pytest.MonkeyPatch,
                                     tmp_path: Path) -> None:
    """A host with no template of its own for a table takes the shared one."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    table = tmp_path / 'GO_0001_body_summary.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_dir / 'GO_0xxx_supplemental_index.lbl'),
               table_type='body_summary')
    assert captured['template_path'] == FCPath(defs.GLOBAL_TEMPLATE_PATH) / 'body_summary.lbl'
    # The host's directory is searched for included files before the shared one.
    assert captured['kwargs']['includes'] == [FCPath(host_dir), defs.GLOBAL_TEMPLATE_PATH]
    assert captured['fields']['VOLUME_ID'] == 'GO_0001'
    assert captured['fields']['TABLE_TYPE'] == 'BODY_SUMMARY'


def test_create_host_template_path(monkeypatch: pytest.MonkeyPatch,
                                   tmp_path: Path) -> None:
    """A table with no shared template is labeled from the host's own."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    host_template = host_dir / 'GO_0xxx_supplemental_index.lbl'
    table = tmp_path / 'GO_0001_supplemental_index.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_template),
               table_type='supplemental_index')
    assert captured['template_path'].name == 'GO_0xxx_supplemental_index.lbl'


@pytest.mark.parametrize('stem', ['body_summary', 'inventory'])
def test_create_prefers_the_host_template(monkeypatch: pytest.MonkeyPatch,
                                          tmp_path: Path, stem: str) -> None:
    """A host shadows any shared template, the inventory's included."""
    captured = _capture_template(monkeypatch)
    host_dir = tmp_path / 'GO_0xxx' / 'templates'
    host_dir.mkdir(parents=True)
    (host_dir / f'GO_0xxx_{stem}.lbl').write_text('END\n', encoding='utf-8')
    table = tmp_path / f'GO_0001_{stem}.tab'
    table.write_text('row', encoding='utf-8')
    lab.create(FCPath(table), FCPath(host_dir / 'GO_0xxx_supplemental_index.lbl'),
               table_type=stem)
    assert captured['template_path'] == FCPath(host_dir / f'GO_0xxx_{stem}.lbl')


def test_host_template_seeks_included_files_in_the_host_directory_first(
        tmp_path: Path) -> None:
    """A shared template includes the host's copy of a fragment, if it has one."""
    shared = tmp_path / 'shared'
    host = tmp_path / 'host'
    shared.mkdir()
    host.mkdir()
    (shared / 'table.lbl').write_text('$INCLUDE("columns.lbl")\nEND\n', encoding='utf-8')
    (shared / 'columns.lbl').write_text('A = "shared"\n', encoding='utf-8')
    (shared / 'other.lbl').write_text('B = "shared"\n', encoding='utf-8')
    (host / 'columns.lbl').write_text('A = "host"\n', encoding='utf-8')
    template = lab.HostTemplate(FCPath(shared / 'table.lbl'),
                                includes=[FCPath(host), FCPath(shared)])
    assert 'A = "host"' in template.content
    # Without a host copy, the shared file is still found.
    (shared / 'table.lbl').write_text('$INCLUDE("other.lbl")\nEND\n', encoding='utf-8')
    template = lab.HostTemplate(FCPath(shared / 'table.lbl'),
                                includes=[FCPath(host), FCPath(shared)])
    assert 'B = "shared"' in template.content


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
               table_type='inventory')
    # 'inventory' in the stem -> no column preprocessors, only the strip.
    assert captured['kwargs']['preprocess'] == [strip_comments]
