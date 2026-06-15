################################################################################
# test_util_replace.py: Tests for the placeholder-substitution helpers in util.
################################################################################
"""Unit tests for ``util.replace``, ``replacement_dict``, and ``replacement_fn``.

These helpers drive the geometry-column assembly: they substitute the ``BODYX``
placeholder for a real body name throughout a nested tuple tree and evaluate
embedded dictionary references. The tests are hermetic — they need no SPICE or
environment variables.
"""

import metadata_tools.defs as defs
import metadata_tools.util as util


def test_replace_substitutes_placeholder_in_flat_tuple() -> None:
    """A placeholder string in a flat tuple is replaced by the name."""
    result = util.replace(('latitude', 'bodyx', 'centric'), 'bodyx', 'JUPITER')
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


def test_replace_passes_through_non_string_leaves() -> None:
    """Numbers and booleans are carried through unchanged."""
    result = util.replace(('limb_altitude', 'bodyx', -0.01, 3, True), 'bodyx', 'IO')
    assert result == ('limb_altitude', 'IO', -0.01, 3, True)


def test_replace_evaluates_embedded_dict_reference() -> None:
    """A nested dict-reference string is evaluated after substitution.

    This is the mechanism behind ``body_diameter_in_pixels``: a column tuple
    carries the string ``defs.RING_SYSTEM_RADII["bodyx"]`` which, once the
    placeholder is replaced, is ``eval``'d to the actual ring-system radius.
    """
    ref = util.replacement_fn('defs.RING_SYSTEM_RADII', defs.BODYX)
    tree = [('body_diameter_in_pixels', 'JUPITER:RING', ref)]
    result = util.replace(tree, defs.BODYX, 'JUPITER')
    assert result == [
        ('body_diameter_in_pixels', 'JUPITER:RING', defs.RING_SYSTEM_RADII['JUPITER'])
    ]


def test_replacement_dict_keys_each_tree_by_name() -> None:
    """``replacement_dict`` returns one substituted tree per name."""
    result = util.replacement_dict([('latitude', 'bodyx')], 'bodyx', ['JUPITER', 'SATURN'])
    assert result == {'JUPITER': [('latitude', 'JUPITER')], 'SATURN': [('latitude', 'SATURN')]}


def test_replacement_fn_builds_dict_reference_string() -> None:
    """``replacement_fn`` formats a ``dict["key"]`` reference string."""
    result = util.replacement_fn('defs.RING_SYSTEM_RADII', 'bodyx')
    assert result == 'defs.RING_SYSTEM_RADII["bodyx"]'
