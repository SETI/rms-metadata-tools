################################################################################
# tests/test_columns_import_lint.py: The columns package must not import
# geometry_support.
################################################################################
"""Guard the one-way dependency between ``columns`` and ``geometry_support``.

``geometry_support.record`` imports ``columns``, so an import back the other way
would be a cycle. It would also be a design regression: ``columns`` describes
how to compute a column and must stay independent of the engine that walks it.

Cycles of this shape fail only on certain import orders, so this checks the
source with ``ast`` rather than waiting for one to bite.
"""
import ast
import pathlib

import pytest

_COLUMNS = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'metadata_tools' / 'columns'


def _imported_modules(source: pathlib.Path) -> set[str]:
    """Return every module name imported by a source file.

    Parameters:
        source: The file to scan.

    Returns:
        The dotted module names it imports.
    """
    names: set[str] = set()
    tree = ast.parse(source.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize('source', sorted(_COLUMNS.glob('*.py')),
                         ids=lambda p: p.name)
def test_columns_never_imports_geometry_support(source: pathlib.Path) -> None:
    """No module under columns/ may import geometry_support, at any depth."""
    offenders = sorted(name for name in _imported_modules(source)
                       if 'geometry_support' in name)
    assert not offenders, (
        f'{source.name} imports {offenders}; columns must not depend on the '
        f'geometry engine that consumes it')


def test_the_lint_has_something_to_check() -> None:
    """The glob really found the catalog modules, so the test is not vacuous."""
    found = {path.name for path in _COLUMNS.glob('*.py')}
    assert {'body.py', 'ring.py', 'sky.py', 'sun.py',
            'catalog.py', 'formats.py', '__init__.py'} <= found
