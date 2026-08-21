################################################################################
# tests/conftest.py: Hermetic import shim + shared fixtures.
#
# See plans/plan2_test_suite.md. One thing blocks importing the support modules
# without SPICE; it is solved here, before collection:
#
#   * index_support / cumulative_support / geometry_support call
#     metadata_tools.config.get_host_config() / get_index_config() /
#     get_geometry_config() (see issue #112) -> register fake config modules via
#     metadata_tools.config.set_current() so no real host or SPICE is needed.
#     (geometry_support.formats.get_mission_table() would otherwise need cspyce
#     SCLK conversion; the fake geometry_config's MISSION_TABLE = [] makes that
#     conversion a no-op.)
################################################################################
import types
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from filecache import FCPath

import metadata_tools.config as mt_config


def _install_fakes() -> None:
    """Install fake host config modules before collection."""
    attr_table: list[tuple[str, dict[str, Any]]] = [
        ('host_config',     {'get_volume_id': lambda p: 'GO_0001',
                             'SCLK_BASES': [16777215, 91, 10, 8],
                             'template_name': 'GO_0xxx_supplemental_index'}),
        ('index_config',    {'glob': 'C0*.LBL'}),
        ('geometry_config', {'MISSION_TABLE': [], 'SC': -77, 'EXPAND': 0.00015,
                             'target_name': lambda d: d.get('TARGET_NAME', 'SKY'),
                             'cleanup': lambda: None}),
    ]
    modules: dict[str, types.ModuleType] = {}
    for name, attrs in attr_table:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        modules[name] = m

    mt_config.set_current(host_id='GO_0xxx',
                          host_config=modules['host_config'],
                          index_config=modules['index_config'],
                          geometry_config=modules['geometry_config'])


_install_fakes()


################################################################################
# Shared fixtures
################################################################################

class FakeWhere:
    """Stand-in for an oops boolean backplane result exposing ``.vals``."""

    def __init__(self, vals: npt.NDArray[np.bool_]) -> None:
        self.vals = vals


class FakeBackplane:
    """A stand-in oops.Backplane for the mask/prep tests.

    It exposes the handful of methods that construct_excluded_mask() and
    prep_row() call, returning small fixed-shape boolean/Scalar arrays so the
    geometry logic runs without SPICE.
    """

    def __init__(self, shape: tuple[int, ...] = (4, 4)) -> None:
        self.shape = shape
        self._false = np.zeros(shape, dtype=bool)
        # Per-method override registries keyed by the body-name arguments.
        self.in_back: dict[tuple[str, str], npt.NDArray[np.bool_]] = {}
        self.inside_shadow: dict[tuple[str, str], npt.NDArray[np.bool_]] = {}
        self.antisunward: dict[str, npt.NDArray[np.bool_]] = {}
        self.sunward: dict[str, npt.NDArray[np.bool_]] = {}
        # evaluate() override registry keyed by the backplane key (tuple).
        self.evaluations: dict[tuple[Any, ...], Any] = {}

    def _lookup(self, registry: dict[Any, npt.NDArray[np.bool_]], key: Any) -> FakeWhere:
        return FakeWhere(registry.get(key, self._false))

    def where_in_back(self, target: str, obscurer: str) -> FakeWhere:
        return self._lookup(self.in_back, (target, obscurer))

    def where_inside_shadow(self, target: str, shadower: str) -> FakeWhere:
        return self._lookup(self.inside_shadow, (target, shadower))

    def where_antisunward(self, target: str) -> FakeWhere:
        return self._lookup(self.antisunward, target)

    def where_sunward(self, target: str) -> FakeWhere:
        return self._lookup(self.sunward, target)

    def evaluate(self, key: tuple[Any, ...]) -> Any:
        import oops
        if key in self.evaluations:
            return self.evaluations[key]
        # Default: an all-masked Scalar of the backplane shape.
        return oops.Scalar(np.zeros(self.shape), True)


@pytest.fixture
def fake_backplane() -> FakeBackplane:
    """A fresh FakeBackplane for each test."""
    return FakeBackplane()


@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every oops.Body.exists() call return True (no SPICE registry)."""
    import oops
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))


@pytest.fixture
def silent_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress all PdsLogger output for the duration of a test."""
    import metadata_tools.common as com
    monkeypatch.setattr(
        com, 'get_logger',
        lambda: types.SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            close=lambda **k: None))


@pytest.fixture
def make_scalar() -> Callable[..., Any]:
    """Factory building oops.Scalar values with an optional mask."""
    import oops

    def _make(values: Any, mask: Any = False) -> Any:
        return oops.Scalar(np.asarray(values, dtype=float), mask)

    return _make


@pytest.fixture
def record_stub() -> Callable[..., Any]:
    """Factory building a bare Record via __new__ with chosen attributes.

    The geometry Record.__init__ walks the SPICE inventory/backplane path. For
    method-level tests we instead create an attribute-only stub carrying only
    what the method under test reads.
    """
    from metadata_tools.geometry_support.record import Record

    def _make(**attrs: Any) -> Record:
        record = Record.__new__(Record)
        for key, value in attrs.items():
            setattr(record, key, value)
        return record

    return _make


@pytest.fixture
def tmp_volume_tree(tmp_path: Path) -> Callable[..., FCPath]:
    """Build a tiny on-disk GO_0xxx/<volume>/... tree of stub files.

    Returns the collection root (the directory whose name is the collection,
    e.g. 'GO_0xxx', containing volume subdirectories). Each volume gets the
    requested table/label stub files.
    """
    def _make(collection: str = 'GO_0xxx',
              volumes: Sequence[str] = ('GO_0001', 'GO_0002'),
              files: dict[str, Sequence[str]] | None = None) -> FCPath:
        if files is None:
            files = {}
        root = tmp_path / collection
        root.mkdir()
        for vol in volumes:
            vdir = root / vol
            vdir.mkdir()
            for suffix, lines in files.items():
                (vdir / f'{vol}{suffix}').write_text(
                    '\r\n'.join(lines) + '\r\n', encoding='utf-8')
        return FCPath(root)

    return _make
