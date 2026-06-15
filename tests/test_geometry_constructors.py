################################################################################
# tests/test_geometry_constructors.py: SPICE-bound constructors, covered with
# heavy monkeypatching instead of running real kernels.
################################################################################
import types

import geometry_config as config
import oops
import pytest

import metadata_tools.columns as col
from metadata_tools.geometry_support import bodies_select
from metadata_tools.geometry_support import record as record_mod
from metadata_tools.geometry_support import suite as suite_mod
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.suite import Suite


#===============================================================================
# bodies_select.inventory
#===============================================================================
def test_inventory_success(monkeypatch):
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)
    obs = types.SimpleNamespace(
        inventory=lambda bodies, expand, cache: ['IO', 'EUROPA'])
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO', 'EUROPA']) == ['IO', 'EUROPA']


def test_inventory_missing_ckernel_clears_pointing(monkeypatch):
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)

    def _raise(bodies, expand, cache):
        raise RuntimeError('SPICE(CKINSUFFDATA): no pointing')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO']) == []
    assert record.pointing_available is False


def test_inventory_other_error_returns_empty(monkeypatch):
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)

    def _raise(bodies, expand, cache):
        raise ValueError('boom')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO']) == []


#===============================================================================
# bodies_select.select_bodies
#===============================================================================
def test_select_bodies_primary_children_and_target(monkeypatch):
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    fake_bodies = {
        'JUPITER': types.SimpleNamespace(children=[
            types.SimpleNamespace(name='IO'),
            types.SimpleNamespace(name='EUROPA')]),
        'IO': types.SimpleNamespace(children=[]),
        'EUROPA': types.SimpleNamespace(children=[]),
    }
    monkeypatch.setattr(bodies_select.col, 'BODIES', fake_bodies)
    monkeypatch.setattr(bodies_select, 'get_system', lambda body: 'JUPITER')
    # inventory keeps every body it is handed.
    monkeypatch.setattr(bodies_select, 'inventory',
                        lambda record, bodies: list(bodies))
    record = types.SimpleNamespace(primary='JUPITER', selections=[],
                                   secondaries=[], additions=[], target='IO')
    result = bodies_select.select_bodies(record, fake_bodies)
    assert result == ['JUPITER', 'IO', 'EUROPA']


def test_select_bodies_no_primary_uses_selections(monkeypatch):
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    fake_bodies = {'IO': object(), 'EUROPA': object()}
    monkeypatch.setattr(bodies_select.col, 'BODIES', fake_bodies)
    monkeypatch.setattr(bodies_select, 'get_system', lambda body: None)
    monkeypatch.setattr(bodies_select, 'inventory',
                        lambda record, bodies: list(bodies))
    record = types.SimpleNamespace(primary='', selections=['IO'],
                                   secondaries=['EUROPA'], additions=[],
                                   target='')
    result = bodies_select.select_bodies(record, fake_bodies)
    assert set(result) == {'IO', 'EUROPA'}


#===============================================================================
# Record.__init__
#===============================================================================
def _patch_record_spice(monkeypatch, primary=''):
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
    monkeypatch.setattr(record_mod.bodies_select, 'get_primary',
                        lambda record, table, sclk: (primary, [], [], []))
    monkeypatch.setattr(record_mod.bodies_select, 'inventory',
                        lambda record, bodies: [])
    monkeypatch.setattr(record_mod.bodies_select, 'select_bodies',
                        lambda record, bodies: [])
    monkeypatch.setattr(config, 'target_name',
                        lambda d: d.get('TARGET_NAME', 'SKY'), raising=False)
    monkeypatch.setattr(config, 'meshgrid',
                        lambda meshgrids, obs: object(), raising=False)
    monkeypatch.setattr(oops.backplane, 'Backplane',
                        lambda obs, meshgrid: 'BACKPLANE')


def _observation(target='SKY'):
    return types.SimpleNamespace(dict={
        'SPACECRAFT_CLOCK_START_COUNT': '100',
        'FILE_SPECIFICATION_NAME': 'DATA/C0123.IMG',
        'TARGET_NAME': target})


def test_record_init_no_primary(monkeypatch):
    _patch_record_spice(monkeypatch, primary='')
    record = Record(_observation(), 'GO_0001', {}, 8, 'summary')
    assert record.primary == ''
    assert record.backplane == 'BACKPLANE'
    assert record.prefixes[0] == '"GO_0001"'
    # The .IMG suffix is rewritten to .LBL in the file-spec prefix.
    assert '.LBL' in record.prefixes[1]
    assert record.dicts['ring'] is col.RING_SUMMARY_DICT


def test_record_init_detailed_selects_detailed_dicts(monkeypatch):
    _patch_record_spice(monkeypatch, primary='')
    record = Record(_observation(), 'GO_0001', {}, 8, 'detailed')
    assert record.dicts['ring'] is col.RING_DETAILED_DICT
    assert record.dicts['body'] is col.BODY_DETAILED_DICT


def test_record_init_with_primary_sets_rings(monkeypatch):
    _patch_record_spice(monkeypatch, primary='JUPITER')
    fake_bodies = dict(col.BODIES)
    fake_bodies['JUPITER'] = types.SimpleNamespace(ring_frame=object())
    monkeypatch.setattr(record_mod.col, 'BODIES', fake_bodies)
    record = Record(_observation(), 'GO_0001', {}, 8, 'summary')
    assert record.rings_present is True
    assert record.primary == 'JUPITER'


#===============================================================================
# Suite.__init__ early-return paths
#===============================================================================
def test_suite_init_returns_without_index(tmp_path):
    # No index files in the (empty) metadata dir -> __init__ returns early and
    # never builds observations.
    suite = Suite(tmp_path, tmp_path, tmp_path, metadata_dir=tmp_path,
                  selection='S', index_glob='*_index.tab')
    assert not hasattr(suite, 'observations')
    assert suite.levels == ['summary']


def test_suite_init_multiple_indexes_raises(tmp_path):
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.tab').write_text('a', encoding='utf-8')
    (meta / 'GO_0002_index.tab').write_text('b', encoding='utf-8')
    with pytest.raises(RuntimeError, match='index files'):
        Suite(tmp_path, tmp_path, tmp_path, metadata_dir=meta,
              selection='SD', index_glob='*_index.tab')


def test_suite_init_builds_tables_and_meshgrids(tmp_path, monkeypatch):
    meta = tmp_path / 'meta'
    meta.mkdir()
    (meta / 'GO_0001_index.tab').write_text('a', encoding='utf-8')
    monkeypatch.setattr(config, 'get_volume_id', lambda d: 'GO_0001', raising=False)
    monkeypatch.setattr(config, 'from_index',
                        lambda idx, supp: ['obs'], raising=False)
    monkeypatch.setattr(config, 'meshgrids', lambda sampling: {'m': 1}, raising=False)
    monkeypatch.setattr(suite_mod.com, 'init_logger', lambda d, t: None)
    suite = Suite(tmp_path, tmp_path, tmp_path, metadata_dir=meta,
                  selection='S', index_glob='*_index.tab')
    assert suite.observations == ['obs']
    assert suite.meshgrids == {'m': 1}
    assert [t.qualifier for t in suite.tables] == ['inventory', 'sky', 'ring', 'body']
