################################################################################
# tests/hosts/VGISS_xxxx/test_host.py: Voyager ISS host configuration
################################################################################
"""Voyager ISS host settings, mission table, and label definitions, without SPICE."""
import fnmatch
import importlib
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any, ClassVar

import julian
import pytest
from filecache import FCPath

import metadata_tools
import metadata_tools.defs as defs
import metadata_tools.label_support as lab
import metadata_tools.util as util
from metadata_tools.column_grammar import (
    expand_format_references,
    merge_column_definitions,
    strip_comments,
)
from metadata_tools.geometry_support.label_schema import resolve_schema
from metadata_tools.hosts.VGISS_xxxx import host_config

HOST_TEMPLATES = Path(metadata_tools.__file__).parent / 'hosts' / 'VGISS_xxxx' / 'templates'

# The first and last IMAGE_TIME of each spacecraft's encounter, from the RMS
# Node's cumulative raw-image indexes (VGISS_5999-VGISS_8999)
ENCOUNTER_IMAGES = {
    ('JUPITER', 'VOYAGER 1'): ('1978-12-11T00:29:23', '1979-04-14T00:07:08'),
    ('JUPITER', 'VOYAGER 2'): ('1979-04-15T23:18:20', '1979-07-16T17:23:10'),
    ('SATURN',  'VOYAGER 1'): ('1980-08-23T12:02:10', '1980-12-15T22:30:11'),
    ('SATURN',  'VOYAGER 2'): ('1981-06-05T16:25:35', '1981-09-05T02:45:34'),
    ('URANUS',  'VOYAGER 2'): ('1985-11-06T17:13:43', '1986-02-19T18:43:55'),
    ('NEPTUNE', 'VOYAGER 2'): ('1989-06-05T08:54:48', '1989-09-29T17:44:41'),
}


#===============================================================================
# host_config
#===============================================================================
@pytest.mark.parametrize(('name', 'matches'), [
    ('C1385455_RAW.LBL', True),
    ('C1385455_CLEANED.LBL', False),
    ('C1385455_CALIB.LBL', False),
    ('C1385455_GEOMED.LBL', False),
    ('C1385455_RAW.IMG', False),
    ('VGISS_5101_index.lbl', False),
])
def test_glob_selects_the_raw_image_labels(name: str, matches: bool) -> None:
    """The data-label glob takes one label per image: the raw image's."""
    assert bool(fnmatch.filter([name], host_config.glob)) == matches


def test_border_is_the_pointing_uncertainty_angle() -> None:
    """The border is one milliradian, for the Voyager scan-platform pointing."""
    assert host_config.BORDER == 1.0e-3


def test_saturn_has_the_opaque_rings() -> None:
    """Saturn's main rings are treated as opaque."""
    assert host_config.OPAQUE_RINGS == {'SATURN': 'SATURN_MAIN_RINGS'}


#===============================================================================
# geometry_config, with the oops host replaced
#===============================================================================
@pytest.fixture
def geometry_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Import the host's geometry_config with a stand-in for the Voyager ISS host.

    The real host furnishes SPICE kernels when it is initialized; the stand-in
    records the index files it is asked to read in its ``calls`` attribute.
    """
    class FakeISS:
        calls: ClassVar[list[Any]] = []

        @staticmethod
        def initialize() -> None:
            pass

        @staticmethod
        def from_index(filename: Any, *, supplement: Any = None) -> list[Any]:
            FakeISS.calls.append((filename, supplement))
            return ['observation']

    FakeISS.calls = []
    monkeypatch.setitem(sys.modules, 'host_voyager', types.ModuleType('host_voyager'))
    monkeypatch.setitem(sys.modules, 'host_voyager.oops',
                        types.SimpleNamespace(VoyagerISS=FakeISS))
    names = ('metadata_tools.hosts.VGISS_xxxx.geometry_config',
             'metadata_tools.hosts.VGISS_xxxx.host_init')
    for name in names:
        monkeypatch.delitem(sys.modules, name, raising=False)
    module = importlib.import_module('metadata_tools.hosts.VGISS_xxxx.geometry_config')
    yield module
    for name in names:
        sys.modules.pop(name, None)


def test_index_glob_selects_the_raw_image_index(geometry_config: Any) -> None:
    """The geometry reads the raw-image index, not the index of every product."""
    names = ['VGISS_5101_index.lbl', 'VGISS_5101_raw_image_index.lbl',
             'VGISS_5101_supplemental_index.lbl']
    assert fnmatch.filter(names, geometry_config.index_glob) == \
        ['VGISS_5101_raw_image_index.lbl']


def test_mission_table_is_keyed_by_time(geometry_config: Any) -> None:
    """Every row is keyed by time, so the host needs no spacecraft ID."""
    assert not hasattr(geometry_config, 'SC')
    converted = util.convert_mission_table(geometry_config.MISSION_TABLE, None)
    assert {row[0].key for row in converted} == {'TIME'}


def test_mission_phases_are_ordered_and_disjoint(geometry_config: Any) -> None:
    """The four planets follow one another without overlap."""
    table = geometry_config.MISSION_TABLE
    assert [row[0].strip() for row in table] == ['JUPITER', 'SATURN', 'URANUS', 'NEPTUNE']
    times = [util.tdb_from_iso(bound) for row in table for bound in row[1]]
    assert times == sorted(times)
    assert len(set(times)) == len(times)


@pytest.mark.parametrize(('encounter', 'span'), ENCOUNTER_IMAGES.items())
def test_each_encounter_lies_in_its_planets_row(geometry_config: Any,
                                                encounter: tuple[str, str],
                                                span: tuple[str, str]) -> None:
    """Every image of each spacecraft's encounter falls in its planet's row."""
    rows = {row[0].strip(): row for row in geometry_config.MISSION_TABLE}
    (start, stop) = (util.tdb_from_iso(bound) for bound in rows[encounter[0]][1])
    first = float(julian.tdb_from_tai(julian.tai_from_iso(span[0])))
    last = float(julian.tdb_from_tai(julian.tai_from_iso(span[1])))
    # A day of margin, more than the longest exposure, as image times end exposures
    assert start + 86400. < first
    assert last + 86400. < stop


def test_each_phase_selects_its_planets_moons(geometry_config: Any) -> None:
    """Each phase's primary and selections match its moon list."""
    rows = {row[0].strip(): row for row in geometry_config.MISSION_TABLE}
    for planet in ('JUPITER', 'SATURN', 'URANUS', 'NEPTUNE'):
        assert rows[planet][3] == planet
        assert rows[planet][5] == getattr(geometry_config, planet + '_MOONS')
    for row in geometry_config.MISSION_TABLE:
        assert row[2] == geometry_config.EXCEPTIONS
        assert row[4] == []
        assert row[6] == []


def test_extra_children_are_selected_in_their_phase(geometry_config: Any) -> None:
    """Himalia, Phoebe, and Nereid are extra children, and their phases select them."""
    assert geometry_config.EXTRA_CHILDREN == ['HIMALIA', 'PHOEBE', 'NEREID']
    assert 'HIMALIA' in geometry_config.JUPITER_MOONS
    assert 'PHOEBE' in geometry_config.SATURN_MOONS
    assert 'NEREID' in geometry_config.NEPTUNE_MOONS


def test_exceptions_name_config_predicates(geometry_config: Any) -> None:
    """With no OBSERVATION_ID, every exception is a predicate, not a regex."""
    for exception in geometry_config.EXCEPTIONS:
        assert exception.isidentifier()
        assert callable(getattr(geometry_config, exception))


@pytest.mark.parametrize(('target', 'expected'), [
    ('DARK', True),
    ('CAL LAMPS', True),
    ('PLAQUE  ', True),
    ('JUPITER', False),
    ('SKY', False),
    ('VEGA', False),
    ('S RINGS', False),
])
def test_calibration_frames_are_recognized_by_target(geometry_config: Any,
                                                     target: str, expected: bool) -> None:
    """Dark, lamp, and plaque frames are calibrations; star and sky frames are not."""
    observation = types.SimpleNamespace(dict={'TARGET_NAME': target})
    assert geometry_config.is_calibration(observation) is expected


def test_from_index_passes_the_supplemental_index(geometry_config: Any) -> None:
    """Observations come from the raw-image index with its supplemental index."""
    result = geometry_config.from_index('VGISS_5101_raw_image_index.lbl',
                                        'VGISS_5101_supplemental_index.lbl')
    assert result == ['observation']
    assert geometry_config.VoyagerISS.calls == [
        ('VGISS_5101_raw_image_index.lbl', 'VGISS_5101_supplemental_index.lbl')]


#===============================================================================
# Label definitions
#===============================================================================
@pytest.mark.parametrize('qualifier', ['sky', 'ring', 'body'])
def test_prefix_widths_come_from_the_host_definitions(qualifier: str) -> None:
    """VOLUME_ID is ten characters and the file specification 34, plus quotes."""
    stubs = resolve_schema(FCPath(HOST_TEMPLATES), qualifier).prefix_stubs
    assert [stub.name for stub in stubs[:2]] == ['VOLUME_ID', 'FILE_SPECIFICATION_NAME']
    assert [stub.width for stub in stubs[:2]] == [12, 36]


def _render(tmp_path: Path, volume_id: str) -> str:
    """Generate a body summary label for a Voyager volume and return its text.

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
              'SAMPLING': None, 'BODY_SAMPLES': None, 'OPAQUE_RINGS': '',
              'VOLUME_ID': volume_id, 'TABLE_TYPE': 'BODY_SUMMARY'}
    label = template.generate(fields, label_path=table.with_suffix('.lbl').as_posix())
    assert template.error_count == 0
    return ' '.join(label.split())


@pytest.mark.parametrize(('volume_id', 'data_set_id'), [
    ('VGISS_5101', 'VG1/VG2-J-ISS-2/3/4/6-PROCESSED-V1.0'),
    ('VGISS_5214', 'VG1/VG2-J-ISS-2/3/4/6-PROCESSED-V1.0'),
    ('VGISS_6101', 'VG1/VG2-S-ISS-2/3/4/6-PROCESSED-V1.1'),
    ('VGISS_6215', 'VG1/VG2-S-ISS-2/3/4/6-PROCESSED-V1.1'),
    ('VGISS_7201', 'VG2-U-ISS-2/3/4/6-PROCESSED-V1.0'),
    ('VGISS_8210', 'VG2-N-ISS-2/3/4/6-PROCESSED-V1.0'),
])
def test_data_set_follows_the_planet(tmp_path: Path, volume_id: str,
                                     data_set_id: str) -> None:
    """Each planet's volumes belong to its own data set."""
    text = _render(tmp_path, volume_id)
    assert f'DATA_SET_ID = "{data_set_id}"' in text
    assert 'MISSION_NAME = "VOYAGER"' in text
    assert 'INSTRUMENT_ID = "ISS"' in text


@pytest.mark.parametrize(('volume_id', 'host_name', 'host_id'), [
    ('VGISS_5101', '"VOYAGER 1"', '"VG1"'),
    ('VGISS_6215', '"VOYAGER 2"', '"VG2"'),
    ('VGISS_5999', '{"VOYAGER 1", "VOYAGER 2"}', '{"VG1", "VG2"}'),
    ('VGISS_6999', '{"VOYAGER 1", "VOYAGER 2"}', '{"VG1", "VG2"}'),
    ('VGISS_7999', '"VOYAGER 2"', '"VG2"'),
    ('VGISS_8999', '"VOYAGER 2"', '"VG2"'),
])
def test_spacecraft_follows_the_volume_number(tmp_path: Path, volume_id: str,
                                              host_name: str, host_id: str) -> None:
    """The second digit names the spacecraft; a cumulative volume names both, if both flew."""
    text = _render(tmp_path, volume_id)
    assert f'INSTRUMENT_HOST_NAME = {host_name}' in text
    assert f'INSTRUMENT_HOST_ID = {host_id}' in text
