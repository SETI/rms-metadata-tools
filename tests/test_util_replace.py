################################################################################
# test_util_replace.py: Tests for the placeholder-substitution helper in util.
################################################################################
"""Unit tests for ``util.replace``.

This helper drives the geometry-column assembly: it substitutes the ``BODYX``
placeholder for a real body name throughout a nested tuple tree. The tests are
hermetic; they need no SPICE or environment variables.
"""

import metadata_tools.util as util


def test_replace_substitutes_placeholder_in_flat_tuple() -> None:
    """A placeholder string in a flat tuple is replaced by the name."""
    result = util.replace(
        ('latitude', 'bodyx', 'centric'), 'bodyx', 'JUPITER')
    assert result == ('latitude', 'JUPITER', 'centric')


def test_replace_recurses_into_nested_tuples() -> None:
    """Replacement descends into nested tuples and preserves structure."""
    tree = (('latitude', 'bodyx'), ('PM', 'P', ''))
    result = util.replace(tree, 'bodyx', 'SATURN')
    assert result == (('latitude', 'SATURN'), ('PM', 'P', ''))


def test_replace_preserves_list_type() -> None:
    """A list input yields a list (tuples yield tuples)."""
    result = util.replace(['bodyx', 'x'], 'bodyx', 'IO')
    assert result == ['IO', 'x']


def test_replace_returns_list_instance_for_list_input() -> None:
    """The returned container type matches the input container type."""
    result = util.replace(['bodyx'], 'bodyx', 'IO')
    assert isinstance(result, list)


def test_replace_preserves_nested_list_type() -> None:
    """A nested list stays a list; it is not coerced to a tuple."""
    result = util.replace([['bodyx', 'x']], 'bodyx', 'IO')
    assert result == [['IO', 'x']]
    assert isinstance(result[0], list)


def test_replace_passes_through_non_string_leaves() -> None:
    """Numbers and booleans are carried through unchanged."""
    result = util.replace(
        ('limb_altitude', 'bodyx', -0.01, 3, True), 'bodyx', 'IO')
    assert result == ('limb_altitude', 'IO', -0.01, 3, True)
