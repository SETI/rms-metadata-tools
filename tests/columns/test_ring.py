################################################################################
# test_ring.py: Tests for the assembled ring column definitions.
################################################################################
"""Hermetic tests for ``metadata_tools.columns.ring``.

The module is loaded via the ``ring_module`` fixture so the tests need no SPICE.
"""

from types import ModuleType

import metadata_tools.defs as defs


def test_summary_dict_covers_all_body_names(ring_module: ModuleType) -> None:
    """The per-body summary dict has exactly one entry per configured body."""
    assert set(ring_module.RING_SUMMARY_DICT) == set(defs.BODY_NAMES)


def test_summary_columns_are_columns_plus_ansa_plus_gridless(
    ring_module: ModuleType,
) -> None:
    """Summary = ring + ansa + gridless columns (the assembly invariant)."""
    expected = (
        ring_module.RING_COLUMNS + ring_module.ANSA_COLUMNS + ring_module.RING_GRIDLESS_COLUMNS
    )
    assert expected == ring_module.RING_SUMMARY_COLUMNS


def test_detailed_columns_exclude_gridless(ring_module: ModuleType) -> None:
    """Detailed = ring + ansa columns, without the gridless columns."""
    expected = ring_module.RING_COLUMNS + ring_module.ANSA_COLUMNS
    assert expected == ring_module.RING_DETAILED_COLUMNS


def test_obs_longitude_uses_180_alt_format(ring_module: ModuleType) -> None:
    """The observer ring-longitude column carries the '-180' alt-format tag."""
    cols = ring_module.RING_SUMMARY_DICT['JUPITER']
    obs = [c for c in cols if c[0][:3] == ('ring_longitude', 'JUPITER:RING', 'obs')]
    assert len(obs) == 1
    assert obs[0][2] == '-180'


def test_body_diameter_resolves_ring_system_radius(ring_module: ModuleType) -> None:
    """The former eval'd dict reference resolves to the ring-system radius."""
    cols = ring_module.RING_SUMMARY_DICT['JUPITER']
    diam = [c for c in cols if c[0][0] == 'body_diameter_in_pixels']
    assert len(diam) == 1
    assert diam[0][0][2] == defs.RING_SYSTEM_RADII['JUPITER']


def test_no_placeholder_survives_substitution(ring_module: ModuleType) -> None:
    """No ``BODYX`` sentinel leaks into the assembled summary dict."""
    assert defs.BODYX not in repr(ring_module.RING_SUMMARY_DICT)
