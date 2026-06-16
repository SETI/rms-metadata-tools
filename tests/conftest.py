################################################################################
# tests/conftest.py: Hermetic import shim + shared fixtures.
#
# See plans/plan2_test_suite.md. Three things block importing the support
# modules without SPICE; all three are solved here, before collection:
#
#   * metadata_tools.bodies runs oops.Body.lookup('MERCURY') at import (needs the
#     SPICE body registry) -> inject a fake module with BODIES = {name: object()}.
#   * index_support / cumulative_support do `import host_config`, `import
#     index_config` (top-level, CWD-dependent) -> inject stub modules.
#   * geometry_support.formats runs MISSION_TABLE = convert_mission_table(
#     config.MISSION_TABLE, config.SC) at import (cspyce SCLK) -> stub
#     geometry_config with MISSION_TABLE = [] so the conversion is a no-op.
#
# Stubs use setdefault so a real host environment (if ever present) is not
# clobbered.
################################################################################
import sys
import types
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from filecache import FCPath


def _install_fakes() -> None:
    """Install fake SPICE/host modules into sys.modules before collection."""
    body_names = ['MERCURY', 'VENUS', 'EARTH', 'MARS', 'JUPITER', 'SATURN',
                  'URANUS', 'NEPTUNE', 'PLUTO', 'IO', 'EUROPA', 'GANYMEDE',
                  'CALLISTO', 'METIS', 'ADRASTEA', 'AMALTHEA', 'THEBE', 'MOON']
    fb = types.ModuleType('metadata_tools.bodies')
    # Attributes are attached to a stub module, so types must be loosened.
    fb.BODIES = {n: object() for n in body_names}  # type: ignore[attr-defined]
    fb.get_bodies = lambda names: {n: object() for n in names}  # type: ignore[attr-defined]
    sys.modules.setdefault('metadata_tools.bodies', fb)

    attr_table: list[tuple[str, dict[str, Any]]] = [
        ('host_config',     {'get_volume_id': lambda p: 'GO_0001',
                             'SCLK_BASES': [16777215, 91, 10, 8],
                             'template_name': 'GO_0xxx_supplemental_index'}),
        ('index_config',    {'glob': 'C0*.LBL'}),
        ('geometry_config', {'MISSION_TABLE': [], 'SC': -77, 'EXPAND': 0.00015,
                             'target_name': lambda d: d.get('TARGET_NAME', 'SKY'),
                             'cleanup': lambda: None}),
    ]
    for name, attrs in attr_table:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules.setdefault(name, m)


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
