################################################################################
# test_sky.py: Tests for the sky column definitions.
################################################################################
"""Hermetic tests for ``metadata_tools.columns.sky``."""

from types import ModuleType


def test_sky_columns_are_right_ascension_and_declination(
    sky_module: ModuleType,
) -> None:
    """The sky table exposes exactly right ascension and declination."""
    keys = [column[0][0] for column in sky_module.SKY_COLUMNS]
    assert keys == ['right_ascension', 'declination']


def test_sky_columns_have_empty_mask_descriptors(sky_module: ModuleType) -> None:
    """Sky columns mask nothing, so every mask descriptor is empty."""
    mask_descs = {column[1] for column in sky_module.SKY_COLUMNS}
    assert mask_descs == {('', '', '')}
