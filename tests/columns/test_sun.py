################################################################################
# test_sun.py: Tests for the sun column definitions.
################################################################################
"""Hermetic tests for ``metadata_tools.columns.sun``."""

from types import ModuleType


def test_summary_is_columns_plus_gridless(sun_module: ModuleType) -> None:
    """Summary = base sun columns + gridless columns."""
    expected = sun_module.SUN_COLUMNS + sun_module.SUN_GRIDLESS_COLUMNS
    assert expected == sun_module.SUN_SUMMARY_COLUMNS


def test_detailed_equals_base_columns(sun_module: ModuleType) -> None:
    """Detailed = base sun columns, without the gridless columns."""
    assert sun_module.SUN_DETAILED_COLUMNS == sun_module.SUN_COLUMNS


def test_obs_longitude_uses_180_alt_format(sun_module: ModuleType) -> None:
    """The observer sun-longitude column carries the '-180' alt-format tag."""
    obs = [c for c in sun_module.SUN_COLUMNS if c[0][:2] == ('longitude', 'SUN') and 'obs' in c[0]]
    assert len(obs) == 1
    assert obs[0][2] == '-180'
