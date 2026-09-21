################################################################################
# test_body.py: Tests for the body column definitions and lazy dict accessors.
################################################################################
"""Hermetic tests for ``metadata_tools.columns.body``.

The module itself imports without SPICE; only ``get_bodies_registry()`` needs an
initialized host, so the accessor tests substitute a fake registry and reset the
module-level caches around each test.
"""

import pytest

import metadata_tools.columns.body as body
import metadata_tools.defs as defs

_FAKE_BODY_NAMES: list[str] = ['MIMAS', 'TETHYS']


@pytest.fixture
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Reset the dict caches and substitute a two-body registry.

    Returns:
        A list receiving one element per registry call, for call counting.
    """
    calls: list[int] = []

    def registry() -> dict[str, object]:
        """Count each call and return a two-body stand-in registry."""
        calls.append(1)
        return {name: object() for name in _FAKE_BODY_NAMES}

    monkeypatch.setattr(body, '_BODY_SUMMARY_DICT', None)
    monkeypatch.setattr(body, 'get_bodies_registry', registry)
    return calls


def test_summary_dict_keyed_by_registry_bodies(fake_registry: list[int]) -> None:
    """The summary dict has one entry per registry body, with the placeholder replaced."""
    summary = body.get_body_summary_dict()

    assert set(summary) == set(_FAKE_BODY_NAMES)
    assert len(summary['MIMAS']) == len(body.BODY_SUMMARY_COLUMNS)
    assert summary['MIMAS'][0][0] == ('latitude', 'MIMAS', 'centric')
    assert not any(defs.BODYX in str(col) for col in summary['TETHYS'])


def test_summary_dict_is_cached(fake_registry: list[int]) -> None:
    """Repeated calls return the same object and consult the registry only once."""
    first = body.get_body_summary_dict()
    assert body.get_body_summary_dict() is first
    assert len(fake_registry) == 1


def test_summary_columns_are_columns_plus_gridless() -> None:
    """Summary = per-pixel + gridless columns (the assembly invariant)."""
    assert body.BODY_SUMMARY_COLUMNS == body.BODY_COLUMNS + body.BODY_GRIDLESS_COLUMNS
