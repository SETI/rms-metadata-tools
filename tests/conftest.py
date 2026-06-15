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

import numpy as np
import pytest


def _install_fakes() -> None:
    """Install fake SPICE/host modules into sys.modules before collection."""
    body_names = ['MERCURY', 'VENUS', 'EARTH', 'MARS', 'JUPITER', 'SATURN',
                  'URANUS', 'NEPTUNE', 'PLUTO', 'IO', 'EUROPA', 'GANYMEDE',
                  'CALLISTO', 'METIS', 'ADRASTEA', 'AMALTHEA', 'THEBE', 'MOON']
    fb = types.ModuleType('metadata_tools.bodies')
    fb.BODIES = {n: object() for n in body_names}
    fb.get_bodies = lambda names: {n: object() for n in names}
    sys.modules.setdefault('metadata_tools.bodies', fb)

    for name, attrs in [
        ('host_config',     {'get_volume_id': lambda p: 'GO_0001',
                             'SCLK_BASES': [16777215, 91, 10, 8],
                             'template_name': 'GO_0xxx_supplemental_index'}),
        ('index_config',    {'glob': 'C0*.LBL'}),
        ('geometry_config', {'MISSION_TABLE': [], 'SC': -77, 'EXPAND': 0.00015,
                             'target_name': lambda d: d.get('TARGET_NAME', 'SKY'),
                             'cleanup': lambda: None}),
    ]:
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

    def __init__(self, vals):
        self.vals = vals


class FakeBackplane:
    """A stand-in oops.Backplane for the mask/prep tests.

    It exposes the handful of methods that construct_excluded_mask() and
    prep_row() call, returning small fixed-shape boolean/Scalar arrays so the
    geometry logic runs without SPICE.
    """

    def __init__(self, shape=(4, 4)):
        self.shape = shape
        self._false = np.zeros(shape, dtype=bool)
        # Per-method override registries keyed by the body-name arguments.
        self.in_back = {}
        self.inside_shadow = {}
        self.antisunward = {}
        self.sunward = {}
        # evaluate() override registry keyed by the backplane key (tuple).
        self.evaluations = {}

    def _lookup(self, registry, key):
        return FakeWhere(registry.get(key, self._false))

    def where_in_back(self, target, obscurer):
        return self._lookup(self.in_back, (target, obscurer))

    def where_inside_shadow(self, target, shadower):
        return self._lookup(self.inside_shadow, (target, shadower))

    def where_antisunward(self, target):
        return self._lookup(self.antisunward, target)

    def where_sunward(self, target):
        return self._lookup(self.sunward, target)

    def evaluate(self, key):
        import oops
        if key in self.evaluations:
            return self.evaluations[key]
        # Default: an all-masked Scalar of the backplane shape.
        return oops.Scalar(np.zeros(self.shape), True)


@pytest.fixture
def fake_backplane():
    """A fresh FakeBackplane for each test."""
    return FakeBackplane()


@pytest.fixture
def make_scalar():
    """Factory building oops.Scalar values with an optional mask."""
    import oops

    def _make(values, mask=False):
        return oops.Scalar(np.asarray(values, dtype=float), mask)

    return _make


@pytest.fixture
def record_stub():
    """Factory building a bare Record via __new__ with chosen attributes.

    The geometry Record.__init__ walks the SPICE inventory/backplane path. For
    method-level tests we instead create an attribute-only stub carrying only
    what the method under test reads.
    """
    from metadata_tools.geometry_support.record import Record

    def _make(**attrs):
        record = Record.__new__(Record)
        for key, value in attrs.items():
            setattr(record, key, value)
        return record

    return _make


@pytest.fixture
def tmp_volume_tree(tmp_path):
    """Build a tiny on-disk GO_0xxx/<volume>/... tree of stub files.

    Returns the collection root (the directory whose name is the collection,
    e.g. 'GO_0xxx', containing volume subdirectories). Each volume gets the
    requested table/label stub files.
    """
    from filecache import FCPath

    def _make(collection='GO_0xxx', volumes=('GO_0001', 'GO_0002'), files=None):
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
