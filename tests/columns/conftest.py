################################################################################
# conftest.py: Fixtures for the columns package tests.
################################################################################
"""Shared fixtures for the ``metadata_tools.columns`` tests.

The ``ring``/``sky``/``sun`` submodules depend only on static data, but
importing them through the package triggers ``columns/__init__.py``, which
imports the ``body`` submodule and builds the oops/SPICE body registry. To keep
the data tests hermetic, these fixtures load those submodules directly from
their source files, bypassing the package ``__init__``.
"""

import importlib.util
import pathlib
from types import ModuleType

import pytest

_COLUMNS_DIR = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'metadata_tools' / 'columns'


def _load_standalone(name: str, filename: str) -> ModuleType:
    """Load a columns submodule from its file, bypassing the package __init__.

    Parameters:
        name: Unique module name to register the loaded module under.
        filename: Submodule file name within the columns package directory.

    Returns:
        The executed module object.
    """
    spec = importlib.util.spec_from_file_location(name, _COLUMNS_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='session')
def ring_module() -> ModuleType:
    """The ring column module, loaded without triggering SPICE."""
    return _load_standalone('_columns_ring_under_test', 'ring.py')


@pytest.fixture(scope='session')
def sky_module() -> ModuleType:
    """The sky column module, loaded without triggering SPICE."""
    return _load_standalone('_columns_sky_under_test', 'sky.py')


@pytest.fixture(scope='session')
def sun_module() -> ModuleType:
    """The sun column module, loaded without triggering SPICE."""
    return _load_standalone('_columns_sun_under_test', 'sun.py')
