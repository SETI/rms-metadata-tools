################################################################################
# test_columns_integration.py: Tests requiring oops/SPICE initialization.
################################################################################
"""Integration tests for the assembled ``metadata_tools.columns`` package.

Importing the package builds the oops/SPICE body registry (``BODIES``), so these
tests require a fully initialized host and are marked ``integration`` (excluded
from the default run). ``metadata_tools.columns`` is imported inside each test,
not at module top, so collection does not trigger SPICE.
"""

import pytest

pytestmark = pytest.mark.integration


def test_package_reexports_every_public_name() -> None:
    """Every name in ``__all__`` is accessible as a package attribute."""
    import metadata_tools.columns as col

    missing = [name for name in col.__all__ if not hasattr(col, name)]
    assert missing == []


def test_body_summary_dict_is_populated() -> None:
    """The body summary dict is keyed by the resolved oops body names."""
    import metadata_tools.columns as col

    assert len(col.BODY_SUMMARY_DICT) > 0


def test_bodies_registry_is_shared_with_bodies_module() -> None:
    """The package re-exports the same ``BODIES`` object as ``bodies``."""
    import metadata_tools.bodies as bodies
    import metadata_tools.columns as col

    assert col.BODIES is bodies.BODIES
