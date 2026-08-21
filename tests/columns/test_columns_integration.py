################################################################################
# test_columns_integration.py: Tests requiring oops/SPICE initialization.
################################################################################
"""Integration tests for the assembled ``metadata_tools.columns`` package.

The body registry is built lazily on first call to ``get_bodies_registry()``,
so these tests require a fully initialized host and are marked ``integration``
(excluded from the default run). ``metadata_tools.columns`` is imported inside
each test, not at module top, so collection does not trigger SPICE.
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

    assert len(col.get_body_summary_dict()) > 0


def test_bodies_registry_is_shared_with_bodies_module() -> None:
    """``col.get_bodies_registry()`` and ``bodies.get_bodies_registry()`` return the same object."""
    import metadata_tools.bodies as bodies_mod
    import metadata_tools.columns as col

    assert col.get_bodies_registry() is bodies_mod.get_bodies_registry()
