################################################################################
# tests/test_geometry_constructors.py: SPICE-bound constructors, covered with
# heavy monkeypatching instead of running real kernels.
################################################################################
"""Tests for SPICE-bound constructors, using monkeypatching instead of real kernels."""
import re
import types
from pathlib import Path
from typing import Any, cast

import oops
import pytest
from filecache import FCPath

import metadata_tools
import metadata_tools.bodies as bodies_mod
import metadata_tools.common as com
from metadata_tools.config import get_geometry_config
from metadata_tools.geometry_support import bodies_select, meshgrids
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.suite import Suite

config = get_geometry_config()


#===============================================================================
# bodies_select.inventory
#===============================================================================
def test_inventory_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """inventory() returns the observation's body list when the call succeeds."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)
    obs = types.SimpleNamespace(
        inventory=lambda bodies, expand, cache: ['IO', 'EUROPA'])
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    # `record` is a SimpleNamespace stub standing in for a Record.
    assert bodies_select.inventory(
        record, ['IO', 'EUROPA']) == ['IO', 'EUROPA']  # type: ignore[arg-type]


def test_bounding_boxes_keeps_only_bodies_in_view(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """bounding_boxes() returns the centre and diameters of each body in view.

    The inventory is taken in the field of view of the record's meshgrid, so
    that a box is located in the coordinates the meshgrid samples.
    """
    monkeypatch.setattr(config, 'EXPAND', 0.5, raising=False)
    seen: list[dict[str, Any]] = []

    def _inventory(bodies: Any, **kwargs: Any) -> Any:
        seen.append(kwargs)
        return {'IO': {'inside': True, 'center_uv': (10.5, 20.5),
                       'u_pixel_size': 3.25, 'v_pixel_size': 3.5},
                'EUROPA': {'inside': False, 'center_uv': (-900., 5.),
                           'u_pixel_size': 2., 'v_pixel_size': 2.}}

    record = types.SimpleNamespace(observation=types.SimpleNamespace(inventory=_inventory),
                                   meshgrid=types.SimpleNamespace(fov='FOV'),
                                   pointing_available=True)
    boxes = bodies_select.bounding_boxes(record, ['IO', 'EUROPA'])  # type: ignore[arg-type]
    assert boxes == {'IO': ((10.5, 20.5), (3.25, 3.5))}
    assert seen == [{'expand': 0.5, 'cache': False, 'return_type': 'full', 'fov': 'FOV'}]


def test_bounding_boxes_without_bodies_skips_the_inventory() -> None:
    """With no bodies there is nothing to locate, and no inventory call."""
    record = types.SimpleNamespace(observation=object())
    assert bodies_select.bounding_boxes(record, []) == {}  # type: ignore[arg-type]


def test_bounding_boxes_missing_ckernel_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without pointing there are no boxes, and pointing is marked unavailable."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)
    _recording_logger(monkeypatch)

    def _raise(bodies: Any, **kwargs: Any) -> Any:
        raise RuntimeError('SPICE(CKINSUFFDATA): no pointing')

    record = types.SimpleNamespace(observation=types.SimpleNamespace(inventory=_raise),
                                   meshgrid=types.SimpleNamespace(fov='FOV'),
                                   pointing_available=True)
    assert bodies_select.bounding_boxes(record, ['IO']) == {}  # type: ignore[arg-type]
    assert record.pointing_available is False


def _recording_logger(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Replace the global logger with one recording (level, message) pairs.

    Returns:
        The list the recorded warnings and exceptions are appended to.
    """
    logged: list[tuple[str, str]] = []
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            warning=lambda msg, *a: logged.append(('warning', msg % a)),
                            exception=lambda msg, *a: logged.append(('exception',
                                                                     msg % a))))
    return logged


def test_inventory_missing_ckernel_clears_pointing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A SPICE CKINSUFFDATA error is logged, yields an empty list, and clears pointing."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)
    logged = _recording_logger(monkeypatch)

    def _raise(bodies: Any, expand: Any, cache: Any) -> Any:
        raise RuntimeError('SPICE(CKINSUFFDATA): no pointing')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO']) == []  # type: ignore[arg-type]
    assert record.pointing_available is False
    assert logged == [('warning', 'SPICE(CKINSUFFDATA): no pointing')]


def test_inventory_unexpected_runtime_error_is_logged(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-pointing RuntimeError is logged as unexpected and leaves pointing set."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)
    logged = _recording_logger(monkeypatch)

    def _raise(bodies: Any, expand: Any, cache: Any) -> Any:
        raise RuntimeError('SPICE(SOMETHINGELSE)')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO']) == []  # type: ignore[arg-type]
    assert record.pointing_available is True
    assert logged == [('exception', 'Unexpected error during inventory')]


def test_inventory_other_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-SPICE exceptions from observation.inventory() propagate as genuine bugs."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)

    def _raise(bodies: Any, expand: Any, cache: Any) -> Any:
        raise ValueError('boom')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    with pytest.raises(ValueError, match='boom'):
        bodies_select.inventory(record, ['IO'])  # type: ignore[arg-type]
    # Non-CKINSUFFDATA/non-SPICE errors must NOT clear pointing_available (only the
    # SPICE(CKINSUFFDATA)/SPICE(NOFRAMECONNECT) branch does that).
    assert record.pointing_available is True


#===============================================================================
# bodies_select.select_bodies
#===============================================================================
def test_select_bodies_primary_children_and_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """The primary, its children, and the target are selected with a primary set."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    fake_bodies = {
        'JUPITER': types.SimpleNamespace(children=[
            types.SimpleNamespace(name='IO'),
            types.SimpleNamespace(name='EUROPA')]),
        'IO': types.SimpleNamespace(children=[]),
        'EUROPA': types.SimpleNamespace(children=[]),
    }
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry', lambda: fake_bodies)
    monkeypatch.setattr(bodies_select, 'get_system', lambda body: 'JUPITER')
    # inventory keeps every body it is handed.
    monkeypatch.setattr(bodies_select, 'inventory',
                        lambda record, bodies: list(bodies))
    record = types.SimpleNamespace(primary='JUPITER', selections=[],
                                   secondaries=[], additions=[], target='IO')
    result = bodies_select.select_bodies(record, fake_bodies)  # type: ignore[arg-type]
    assert result == ['JUPITER', 'IO', 'EUROPA']


def test_select_bodies_no_primary_uses_selections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a primary, the selections and secondaries drive body selection."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    fake_bodies = {'IO': object(), 'EUROPA': object()}
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry', lambda: fake_bodies)
    monkeypatch.setattr(bodies_select, 'get_system', lambda body: None)
    monkeypatch.setattr(bodies_select, 'inventory',
                        lambda record, bodies: list(bodies))
    record = types.SimpleNamespace(primary='', selections=['IO'],
                                   secondaries=['EUROPA'], additions=[],
                                   target='')
    result = bodies_select.select_bodies(record, fake_bodies)  # type: ignore[arg-type]
    assert set(result) == {'IO', 'EUROPA'}


#===============================================================================
# Record.__init__
#===============================================================================
def _patch_record_spice(monkeypatch: pytest.MonkeyPatch, primary: str = '') -> None:
    """Patch the SPICE-facing seams so Record.__init__ runs without kernels.

    Parameters:
        monkeypatch: The pytest monkeypatch fixture.
        primary: Primary body name returned by the patched get_primary.
    """
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    monkeypatch.setattr(bodies_select, 'get_primary',
                        lambda record, table, sclk: (primary, [], [], []))
    monkeypatch.setattr(bodies_select, 'inventory',
                        lambda record, bodies: [])
    monkeypatch.setattr(bodies_select, 'select_bodies',
                        lambda record, bodies: [])
    monkeypatch.setattr(bodies_select, 'bounding_boxes',
                        lambda record, bodies: {})
    monkeypatch.setattr(config, 'target_name',
                        lambda d: d.get('TARGET_NAME', 'SKY'), raising=False)
    monkeypatch.setattr(config, 'meshgrid',
                        lambda meshgrids, obs: object(), raising=False)
    monkeypatch.setattr(oops.backplane, 'Backplane',
                        lambda obs, meshgrid: 'BACKPLANE')
    # The body registry is lazy (built from SPICE on first call); stub it out so
    # Record.__init__ can run without a SPICE-initialized host.
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry', lambda: {})


def _observation(target: str = 'SKY') -> Any:
    """Return a SimpleNamespace observation stub (oops Observation stand-in)."""
    return types.SimpleNamespace(dict={
        'SPACECRAFT_CLOCK_START_COUNT': '100',
        'FILE_SPECIFICATION_NAME': 'DATA/C0123.IMG',
        'TARGET_NAME': target})


def test_record_init_no_primary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a primary, Record still builds backplane, prefixes, and dicts."""
    _patch_record_spice(monkeypatch, primary='')
    record = Record(_observation(), 'GO_0001', {}, 8)
    assert record.primary == ''
    # The patched Backplane constructor returns a string sentinel; compare as Any
    # since the attribute is typed as a real oops Backplane.
    assert cast(Any, record.backplane) == 'BACKPLANE'
    assert record.prefixes[0] == '"GO_0001"'
    # The .IMG suffix is rewritten to .LBL in the file-spec prefix, which is
    # unpadded when no column width is given.
    assert record.prefixes[1] == '"DATA/C0123.LBL"'


def test_record_init_pads_the_file_specification(monkeypatch: pytest.MonkeyPatch) -> None:
    """The file specification is padded to the width of its column."""
    _patch_record_spice(monkeypatch)
    record = Record(_observation(), 'GO_0001', {}, 8, filespec_width=20)
    assert record.prefixes[1] == '"DATA/C0123.LBL      "'


def test_record_init_rejects_an_overlong_file_specification(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A file specification wider than its column is an error, not a ragged row."""
    _patch_record_spice(monkeypatch)
    with pytest.raises(ValueError, match=re.escape(
            "file specification 'DATA/C0123.LBL' is wider than the 10 characters "
            "of the FILE_SPECIFICATION_NAME column")):
        Record(_observation(), 'GO_0001', {}, 8, filespec_width=10)


def test_record_init_defaults_the_target_to_target_name(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A host with no target_name hook takes the target from TARGET_NAME."""
    _patch_record_spice(monkeypatch)
    monkeypatch.delattr(config, 'target_name')
    record = Record(_observation(target='IO'), 'GO_0001', {}, 8)
    assert record.target == 'IO'


def test_record_init_samples_the_fov_of_the_observation(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A host with no meshgrid hook gets a meshgrid of the observation's own FOV."""
    _patch_record_spice(monkeypatch)
    monkeypatch.delattr(config, 'meshgrid')
    monkeypatch.setattr(config, 'EXPAND', 2.5e-4, raising=False)
    built: list[Any] = []

    def _fov_meshgrid(fov: Any, sampling: float, expand: float) -> str:
        built.append((fov, sampling, expand))
        return 'FOV_GRID'

    monkeypatch.setattr(meshgrids, 'fov_meshgrid', _fov_meshgrid)
    observation = _observation()
    observation.fov = 'FOV'
    cache: dict[Any, Any] = {}
    record = Record(observation, 'GO_0001', cache, 8)
    assert cast(Any, record.meshgrid) == 'FOV_GRID'
    assert built == [('FOV', 8, 2.5e-4)]
    # A second observation with the same FOV is served from the volume's cache.
    assert cast(Any, Record(observation, 'GO_0001', cache, 8).meshgrid) == 'FOV_GRID'
    assert len(built) == 1


def test_record_init_with_primary_sets_rings(monkeypatch: pytest.MonkeyPatch) -> None:
    """A primary with a ring frame sets rings_present."""
    _patch_record_spice(monkeypatch, primary='JUPITER')
    fake_bodies = {'JUPITER': types.SimpleNamespace(ring_frame=object())}
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry', lambda: fake_bodies)
    record = Record(_observation(), 'GO_0001', {}, 8)
    assert record.rings_present is True
    assert record.primary == 'JUPITER'


def test_record_init_locates_the_tabulated_bodies(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The tabulated bodies are located; the ring system is not."""
    _patch_record_spice(monkeypatch, primary='JUPITER')
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry',
                        lambda: {'JUPITER': types.SimpleNamespace(ring_frame=object())})
    monkeypatch.setattr(bodies_select, 'select_bodies',
                        lambda record, bodies: ['JUPITER', 'IO'])
    located: list[Any] = []

    def _boxes(record: Any, bodies: Any) -> dict[str, Any]:
        located.append(bodies)
        return {'IO': 'BOX'}

    monkeypatch.setattr(bodies_select, 'bounding_boxes', _boxes)
    record = Record(_observation(), 'GO_0001', {}, 8, 32)
    assert located == [['JUPITER', 'IO']]
    assert cast(Any, record.boxes) == {'IO': 'BOX'}
    assert record.body_samples == 32


def test_record_init_locates_nothing_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """With body_samples of 0, no boxes are requested and every row uses the FOV."""
    _patch_record_spice(monkeypatch, primary='JUPITER')
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry',
                        lambda: {'JUPITER': types.SimpleNamespace(ring_frame=object())})
    monkeypatch.setattr(bodies_select, 'select_bodies',
                        lambda record, bodies: ['JUPITER', 'IO'])

    def _boxes(record: Any, bodies: Any) -> dict[str, Any]:
        raise AssertionError('bounding boxes requested')

    monkeypatch.setattr(bodies_select, 'bounding_boxes', _boxes)
    record = Record(_observation(), 'GO_0001', {}, 8, 0)
    assert record.boxes == {}
    assert record.backplane_for('IO') == (record.backplane, 8)


#===============================================================================
# Record.backplane_for
#===============================================================================
def _boxed_record(monkeypatch: pytest.MonkeyPatch, grid: Any) -> tuple[Record, list[Any]]:
    """Build a record with one boxed body and a patched meshgrid builder.

    Parameters:
        monkeypatch: The pytest monkeypatch fixture.
        grid: What the patched box_meshgrid returns.

    Returns:
        The record, and the list of meshgrids that backplanes were built on.
    """
    # The sentinels stand in for oops objects, so the attributes are set untyped.
    record: Any = Record.__new__(Record)
    record.observation = 'OBS'
    record.meshgrid = 'FOV_GRID'
    record.backplane = 'FOV_BACKPLANE'
    record.sampling = 8
    record.body_samples = 16
    record.boxes = {'IO': ((10., 20.), (3., 3.))}
    record._backplanes = {}
    built: list[Any] = []

    def _backplane(obs: Any, meshgrid: Any) -> str:
        built.append(meshgrid)
        return f'ON_{meshgrid}'

    def _box_meshgrid(fov_grid: Any, center: Any, size: Any, sampling: int,
                      samples: int, margin: float) -> Any:
        return grid and (f'{grid[0]}_{margin}', grid[1])

    monkeypatch.setattr(meshgrids, 'box_meshgrid', _box_meshgrid)
    monkeypatch.setattr(oops.backplane, 'Backplane', _backplane)
    return record, built


def test_backplane_for_builds_one_backplane_per_body(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A boxed body gets its own backplane, built once and then reused."""
    record, built = _boxed_record(monkeypatch, ('IO_GRID', 2))
    assert record.backplane_for('IO') == ('ON_IO_GRID_0.1', 2)
    assert record.backplane_for('IO') == ('ON_IO_GRID_0.1', 2)
    assert built == ['IO_GRID_0.1']


def test_backplane_for_builds_one_backplane_per_margin(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Each margin asked of a body gets a backplane of its own, built once."""
    record, built = _boxed_record(monkeypatch, ('IO_GRID', 2))
    assert record.backplane_for('IO', 1.5) == ('ON_IO_GRID_1.5', 2)
    assert record.backplane_for('IO') == ('ON_IO_GRID_0.1', 2)
    assert record.backplane_for('IO', 1.5) == ('ON_IO_GRID_1.5', 2)
    # Naming the default margin is the same as naming none.
    assert record.backplane_for('IO', meshgrids.MARGIN) == ('ON_IO_GRID_0.1', 2)
    assert built == ['IO_GRID_1.5', 'IO_GRID_0.1']


def test_backplane_for_unboxed_body_uses_the_fov(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body with no box, or no body at all, is tabulated on the FOV backplane."""
    record, built = _boxed_record(monkeypatch, ('IO_GRID', 2))
    assert record.backplane_for('EUROPA') == ('FOV_BACKPLANE', 8)
    assert record.backplane_for(None) == ('FOV_BACKPLANE', 8)
    assert built == []


def test_backplane_for_falls_back_when_no_grid_is_built(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A box that yields no meshgrid of its own shares the FOV backplane."""
    record, built = _boxed_record(monkeypatch, None)
    assert record.backplane_for('IO') == ('FOV_BACKPLANE', 8)
    assert built == []


def test_record_init_sets_blocker_when_target_in_view(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A target among the selected bodies becomes the blocker if it is in the FOV."""
    _patch_record_spice(monkeypatch, primary='JUPITER')
    monkeypatch.setattr(bodies_mod, 'get_bodies_registry',
                        lambda: {'JUPITER': types.SimpleNamespace(ring_frame=None)})
    monkeypatch.setattr(bodies_select, 'select_bodies', lambda record, bodies: ['IO'])
    inventoried: list[Any] = []

    def _inventory(record: Any, bodies: Any) -> list[str]:
        inventoried.append(bodies)
        return list(bodies)

    monkeypatch.setattr(bodies_select, 'inventory', _inventory)
    record = Record(_observation(target='IO'), 'GO_0001', {}, 8)
    assert record.blocker == 'IO'
    # The second inventory call asks only whether the target itself is in view.
    assert inventoried[-1] == ['IO']


def test_record_init_no_blocker_when_target_not_selected(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A target that is not among the selected bodies leaves blocker None."""
    _patch_record_spice(monkeypatch, primary='')
    record = Record(_observation(target='IO'), 'GO_0001', {}, 8)
    assert record.blocker is None


def test_record_init_without_primary_has_no_rings(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no primary, rings_present is still defined, and False."""
    _patch_record_spice(monkeypatch, primary='')
    record = Record(_observation(), 'GO_0001', {}, 8)
    assert record.rings_present is False


#===============================================================================
# Suite.__init__ early-return paths
#===============================================================================
def test_suite_init_returns_without_index(tmp_path: Path) -> None:
    """With no index file, __init__ returns early and never builds observations."""
    suite = Suite(tmp_path, tmp_path, tmp_path, metadata_dir=tmp_path,
                  index_glob='*_index.tab')
    assert not hasattr(suite, 'observations')


def test_suite_init_defaults_index_glob_to_the_volume(tmp_path: Path) -> None:
    """With no index_glob, the index label is the one named for the volume."""
    # A second volume's label in the directory is not a match, so nothing is
    # ambiguous; the conftest host names the volume GO_0001.
    (tmp_path / 'GO_0002_index.lbl').write_text('a', encoding='utf-8')
    suite = Suite(tmp_path, tmp_path, tmp_path, metadata_dir=tmp_path)
    assert suite.index_glob == 'GO_0001_index.lbl'
    assert not hasattr(suite, 'observations')


def test_suite_init_multiple_indexes_raises(tmp_path: Path) -> None:
    """More than one matching index file raises RuntimeError."""
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.tab').write_text('a', encoding='utf-8')
    (meta / 'GO_0002_index.tab').write_text('b', encoding='utf-8')
    with pytest.raises(RuntimeError,
                       match=re.escape(f'Multiple index files found in {FCPath(meta)}.')):
        Suite(tmp_path, tmp_path, tmp_path, metadata_dir=meta,
              index_glob='*_index.tab')


def test_suite_init_missing_index_file_logs_and_returns(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """from_index raising FileNotFoundError is logged; the Suite has no observations."""
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.tab').write_text('a', encoding='utf-8')
    monkeypatch.setattr(config, 'get_volume_id', lambda d: 'GO_0001', raising=False)

    def _missing(idx: Any, supp: Any) -> Any:
        raise FileNotFoundError(supp)

    monkeypatch.setattr(config, 'from_index', _missing, raising=False)
    monkeypatch.setattr(com, 'init_logger', lambda d, t: None)
    logged: list[str] = []
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None,
                            exception=lambda msg, *a: logged.append(msg % a)))
    suite = Suite(tmp_path, tmp_path, tmp_path, metadata_dir=meta,
                  index_glob='*_index.tab')
    assert not hasattr(suite, 'observations')
    assert logged == ['Index file not found for GO_0001']


def test_suite_init_builds_tables_and_meshgrids(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A single index yields observations, meshgrids, and the standard tables."""
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.tab').write_text('a', encoding='utf-8')
    monkeypatch.setattr(config, 'get_volume_id', lambda d: 'GO_0001', raising=False)
    monkeypatch.setattr(config, 'from_index',
                        lambda idx, supp: ['obs'], raising=False)
    monkeypatch.setattr(config, 'meshgrids', lambda sampling: {'m': 1}, raising=False)
    monkeypatch.setattr(com, 'init_logger', lambda d, t: None)
    # The real host template, so the tables resolve their schemas from it just
    # as they do in a run; a tmp_path stand-in has no COLUMN objects to read.
    template = (Path(metadata_tools.__file__).parent / 'hosts' / 'GO_0xxx' /
                'templates' / 'GO_0xxx_supplemental_index.lbl')
    suite = Suite(tmp_path, tmp_path, template, metadata_dir=meta,
                  index_glob='*_index.tab')
    assert suite.observations == ['obs']
    assert suite.meshgrids == {'m': 1}
    assert [t.qualifier for t in suite.tables] == ['inventory', 'sky', 'ring', 'body']
    # Each geometry table resolved its column set from that template directory.
    by_qualifier: dict[Any, Any] = {t.qualifier: t for t in suite.tables}
    assert len(by_qualifier['sky'].schema.columns) == 2
    assert len(by_qualifier['ring'].schema.columns) == 43
    assert len(by_qualifier['body'].schema.columns) == 28
