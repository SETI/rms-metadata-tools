################################################################################
# tests/hosts/COISS_xxxx/test_host.py: Cassini ISS host configuration
################################################################################
"""Cassini ISS host settings, mission table, and label definitions, without SPICE."""
import fnmatch
import importlib
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

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
from metadata_tools.geometry_support.label_schema import resolve_schema
from metadata_tools.hosts.COISS_xxxx import host_config

HOST_TEMPLATES = Path(metadata_tools.__file__).parent / 'hosts' / 'COISS_xxxx' / 'templates'


#===============================================================================
# host_config
#===============================================================================
@pytest.mark.parametrize(('name', 'matches'), [
    ('N1454725799_1.LBL', True),
    ('W1459561618_9.LBL', True),
    ('N1454725799_1.IMG', False),
    ('COISS_2001_index.LBL', False),
])
def test_glob_selects_the_narrow_and_wide_angle_labels(name: str, matches: bool) -> None:
    """The data-label glob takes NAC and WAC labels and nothing else."""
    assert bool(fnmatch.filter([name], host_config.glob)) == matches


def test_border_is_the_pointing_uncertainty_angle() -> None:
    """The border is 0.15 milliradians, as for Galileo."""
    assert host_config.BORDER == 1.5e-4


#===============================================================================
# geometry_config, with the oops host replaced
#===============================================================================
@pytest.fixture
def geometry_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Import the host's geometry_config with a stand-in for the oops ISS host.

    The real host furnishes SPICE kernels when it is initialized; the stand-in
    records the index files it is asked to read in its ``calls`` attribute.
    """
    class FakeISS:
        calls: ClassVar[list[Any]] = []

        @staticmethod
        def _initialize() -> None:
            pass

        @staticmethod
        def from_index(filename: Any) -> list[Any]:
            FakeISS.calls.append(filename)
            return ['observation']

    monkeypatch.setitem(sys.modules, 'hosts.cassini.iss',
                        types.SimpleNamespace(ISS=FakeISS))
    for name in ('metadata_tools.hosts.COISS_xxxx.geometry_config',
                 'metadata_tools.hosts.COISS_xxxx.host_init'):
        monkeypatch.delitem(sys.modules, name, raising=False)
    module = importlib.import_module('metadata_tools.hosts.COISS_xxxx.geometry_config')
    yield module
    for name in ('metadata_tools.hosts.COISS_xxxx.geometry_config',
                 'metadata_tools.hosts.COISS_xxxx.host_init'):
        sys.modules.pop(name, None)


def test_mission_phases_are_ordered_and_disjoint(geometry_config: Any) -> None:
    """The Earth, Jupiter, and Saturn phases follow one another without overlap."""
    table = geometry_config.MISSION_TABLE
    assert [row[0].strip() for row in table] == ['EARTH', 'JUPITER', 'SATURN']
    sclks = [float(sclk) for row in table for sclk in row[1]]
    assert sclks == sorted(sclks)
    assert len(set(sclks)) == len(sclks)


def test_each_phase_selects_its_planets_moons(geometry_config: Any) -> None:
    """Each phase's primary and selections match its moon list."""
    rows = {row[0].strip(): row for row in geometry_config.MISSION_TABLE}
    assert rows['EARTH'][3] == 'EARTH'
    assert rows['EARTH'][5] == ['EARTH', 'MOON']
    assert rows['JUPITER'][3] == 'JUPITER'
    assert rows['JUPITER'][5] == geometry_config.JUPITER_MOONS
    assert rows['SATURN'][3] == 'SATURN'
    assert rows['SATURN'][5] == geometry_config.SATURN_MOONS
    for row in geometry_config.MISSION_TABLE:
        assert row[2] == geometry_config.EXCEPTIONS
        assert row[4] == []
        assert row[6] == []


def test_extra_children_are_selected_in_their_phase(geometry_config: Any) -> None:
    """Himalia and Phoebe are extra children, and their phases select them."""
    assert geometry_config.EXTRA_CHILDREN == ['HIMALIA', 'PHOEBE']
    assert 'HIMALIA' in geometry_config.JUPITER_MOONS
    assert 'PHOEBE' in geometry_config.SATURN_MOONS


def test_from_index_reads_only_the_index(geometry_config: Any) -> None:
    """Observations come from the volume index; the supplemental index is unused."""
    result = geometry_config.from_index('COISS_2001_index.lbl', 'unused.lbl')
    assert result == ['observation']
    assert geometry_config.ISS.calls == ['COISS_2001_index.lbl']


#===============================================================================
# Label definitions
#===============================================================================
@pytest.mark.parametrize('qualifier', ['sky', 'ring', 'body'])
def test_prefix_widths_come_from_the_host_definitions(qualifier: str) -> None:
    """VOLUME_ID is ten characters and the file specification 45, plus quotes."""
    stubs = resolve_schema(FCPath(HOST_TEMPLATES), qualifier).prefix_stubs
    assert [stub.name for stub in stubs[:2]] == ['VOLUME_ID', 'FILE_SPECIFICATION_NAME']
    assert [stub.width for stub in stubs[:2]] == [12, 47]


def _render(tmp_path: Path, volume_id: str) -> str:
    """Generate a body summary label for a Cassini volume and return its text.

    Parameters:
        tmp_path: The pytest temporary directory.
        volume_id: The volume whose table the label describes.

    Returns:
        The text of the label, with its line breaks removed.
    """
    table = tmp_path / f'{volume_id}_body_summary.tab'
    table.write_text('row\r\n', encoding='utf-8')
    template = lab.HostTemplate(
        FCPath(defs.GLOBAL_TEMPLATE_PATH) / 'body_summary.lbl', crlf=True,
        preprocess=[strip_comments, expand_format_references, merge_column_definitions],
        includes=[FCPath(HOST_TEMPLATES), defs.GLOBAL_TEMPLATE_PATH])
    fields = {'LABEL_VALUE': lambda name: 'FIXED_LENGTH', 'FOV_BORDER': None,
              'SAMPLING': None, 'BODY_SAMPLES': None, 'VOLUME_ID': volume_id,
              'TABLE_TYPE': 'BODY_SUMMARY'}
    label = template.generate(fields, label_path=table.with_suffix('.lbl').as_posix())
    assert template.error_count == 0
    return ' '.join(label.split())


@pytest.mark.parametrize(('volume_id', 'data_set_id'), [
    ('COISS_1001', 'CO-E/V/J-ISSNA/ISSWA-2-EDR-V1.0'),
    ('COISS_2001', 'CO-S-ISSNA/ISSWA-2-EDR-V1.0'),
])
def test_data_set_follows_the_volume_series(tmp_path: Path, volume_id: str,
                                            data_set_id: str) -> None:
    """COISS_1xxx is the cruise data set and COISS_2xxx the Saturn data set."""
    text = _render(tmp_path, volume_id)
    assert f'DATA_SET_ID = "{data_set_id}"' in text
    assert 'INSTRUMENT_HOST_NAME = "CASSINI ORBITER"' in text
    assert 'INSTRUMENT_ID = "ISS"' in text
