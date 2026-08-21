################################################################################
# tests/test_config.py: Tests for metadata_tools.config
################################################################################
"""Tests for config: set_host/set_current registration and the unregistered-host
error paths of current_host_id/get_host_config/get_index_config/get_geometry_config.
"""
import importlib
import types

import pytest

import metadata_tools.config as cfg

_NOT_REGISTERED = r'set_host\(\) has not been called'


def _clear_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Temporarily clear all registered host config modules for one test."""
    monkeypatch.setattr(cfg, '_host_id', None)
    monkeypatch.setattr(cfg, '_host_config', None)
    monkeypatch.setattr(cfg, '_index_config', None)
    monkeypatch.setattr(cfg, '_geometry_config', None)


#===============================================================================
# unregistered-host error paths
#===============================================================================
def test_current_host_id_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        cfg.current_host_id()


def test_get_host_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        cfg.get_host_config()


def test_get_index_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        cfg.get_index_config()


def test_get_geometry_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        cfg.get_geometry_config()


#===============================================================================
# set_current / set_host registration
#===============================================================================
def test_set_current_registers_host_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    fake = types.ModuleType('fake')
    cfg.set_current(host_id='TEST_HOST', host_config=fake,
                    index_config=fake, geometry_config=fake)
    assert cfg.current_host_id() == 'TEST_HOST'
    # monkeypatch restores the original (conftest-installed) registry at teardown.


def test_set_current_registers_all_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    host = types.ModuleType('host')
    idx = types.ModuleType('idx')
    geom = types.ModuleType('geom')
    cfg.set_current(host_id='X', host_config=host, index_config=idx,
                    geometry_config=geom)
    assert cfg.get_host_config() is host
    assert cfg.get_index_config() is idx
    assert cfg.get_geometry_config() is geom


def test_set_host_imports_and_registers_host_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    host = types.ModuleType('metadata_tools.hosts.FAKE_HOST.host_config')
    idx = types.ModuleType('metadata_tools.hosts.FAKE_HOST.index_config')
    geom = types.ModuleType('metadata_tools.hosts.FAKE_HOST.geometry_config')
    modules = {
        'metadata_tools.hosts.FAKE_HOST.host_config': host,
        'metadata_tools.hosts.FAKE_HOST.index_config': idx,
        'metadata_tools.hosts.FAKE_HOST.geometry_config': geom,
    }
    monkeypatch.setattr(importlib, 'import_module', lambda name: modules[name])

    cfg.set_host('FAKE_HOST')

    assert cfg.current_host_id() == 'FAKE_HOST'
    assert cfg.get_host_config() is host
    assert cfg.get_index_config() is idx
    assert cfg.get_geometry_config() is geom
################################################################################
