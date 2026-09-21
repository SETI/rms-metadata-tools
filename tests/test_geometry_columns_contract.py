################################################################################
# test_geometry_columns_contract.py: Static contract between geometry_support
# and the columns package.
################################################################################
"""Guard the ``col.<NAME>`` references in ``geometry_support.py``.

``Record.__init__`` selects column dictionaries from the ``metadata_tools.columns``
package by attribute (e.g. ``col.RING_DETAILED_DICT``). Two of those references were
latent ``AttributeError`` typos (``col.RING_SUMMARY_DETAILED`` /
``col.BODY_SUMMARY_DETAILED``, plus ``col.BODYX``) that never fired because the
``'detailed'`` geometry path is not exercised by the wired-up host or the
SPICE-gated tests.

These tests parse the source with ``ast`` instead of importing it, so they stay
hermetic (importing either module triggers the oops/SPICE body registry). Every
``col.<NAME>`` used in ``geometry_support.py`` must be exported by the columns
package's ``__all__``; otherwise it is a latent ``AttributeError``.
"""

import ast
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'metadata_tools'
# geometry_support is a package; the col.<NAME> references live across its
# submodules (chiefly record.py). Glob every module in the package directory.
_GEOMETRY_SUPPORT = sorted((_SRC / 'geometry_support').glob('*.py'))
_COLUMNS_INIT = _SRC / 'columns' / '__init__.py'


def _col_attributes(sources: list[pathlib.Path]) -> set[str]:
    """Return every ``NAME`` referenced as ``col.NAME`` across source files.

    Parameters:
        sources: Source files to scan.

    Returns:
        The set of attribute names referenced on ``col``.
    """
    attrs: set[str] = set()
    for source in sources:
        tree = ast.parse(source.read_text())
        attrs |= {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == 'col'
        }
    return attrs


def _columns_all() -> set[str]:
    """Return the names listed in the columns package ``__all__``."""
    tree = ast.parse(_COLUMNS_INIT.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets
        ):
            assert isinstance(node.value, (ast.List, ast.Tuple))
            return {
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    raise AssertionError('columns/__init__.py defines no __all__')


def test_every_col_reference_is_exported() -> None:
    """No ``col.<NAME>`` in geometry_support is a latent AttributeError."""
    used = _col_attributes(_GEOMETRY_SUPPORT)
    exported = _columns_all()
    missing = sorted(used - exported)
    assert not missing, f'geometry_support references undefined columns names: {missing}'


def test_catalog_accessors_are_exported() -> None:
    """The geometry path reaches the catalogs through exported accessors."""
    exported = _columns_all()
    assert 'get_catalog' in exported
    assert 'name_map' in exported


def test_removed_names_are_gone() -> None:
    """No removed name -- detailed, tiling, or per-body dict -- survives."""
    used = _col_attributes(_GEOMETRY_SUPPORT)
    exported = _columns_all()
    for name in ('RING_DETAILED_DICT', 'RING_DETAILED_COLUMNS', 'BODY_DETAILED_COLUMNS',
                 'SUN_DETAILED_COLUMNS', 'get_body_detailed_dict', 'BODY_TILES',
                 'BODY_TILE_DICT', 'RING_TILES', 'RING_TILE_DICT', 'OUTER_RING_TILES',
                 'OUTER_RING_TILE_DICT', 'SKY_TILES', 'RING_AZ',
                 'RING_SUMMARY_DETAILED', 'BODY_SUMMARY_DETAILED',
                 'RING_SUMMARY_DICT', 'get_body_summary_dict'):
        assert name not in used, f'geometry_support still references col.{name}'
        assert name not in exported, f'columns still exports {name}'
    # BODYX is a defs constant, never a columns attribute.
    assert 'BODYX' not in used
