#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import importlib.metadata
import math
import os
import sys
import types

sys.path.insert(0, os.path.abspath('../src'))

# Verify the source path exists
if not os.path.exists(os.path.abspath('../src')):
    import warnings
    warnings.warn("Source directory '../src' not found. API documentation may be incomplete.")

# -- Import shims for headless API-doc builds --------------------------------
#
# The geometry engine is built on the ``oops`` library, whose body registry is
# normally populated by loading SPICE kernels during a host initialization step
# (e.g. ``ssi.initialize()``). That data is not available on the documentation
# builder, yet several modules query the registry at import time to assemble
# their column-definition tables. A lightweight stand-in for ``oops`` lets
# ``autodoc`` import every module without SPICE: it returns real string body
# names (so the table-assembly code that calls ``str.replace`` works) and
# provides the numeric constants used at module load. Runtime-only attributes
# are present but never exercised during a docs build.
if 'oops' not in sys.modules:
    _oops = types.ModuleType('oops')
    _oops.RPD = math.pi / 180.0
    _oops.DPR = 180.0 / math.pi

    class _FakeBody:
        def __init__(self, name: str) -> None:
            self.name = name
            self.children: list = []
            self.ring_frame = None
            self.parent = None

        def select_children(self, kind: str) -> list:
            return []

    class _Body:
        BODY_REGISTRY: dict = {}

        @staticmethod
        def lookup(name: str) -> _FakeBody:
            return _FakeBody(name)

        @staticmethod
        def exists(name: str) -> bool:
            return False

    _oops.Body = _Body
    _oops.Scalar = object
    _oops.Meshgrid = object
    _oops.backplane = types.SimpleNamespace(Backplane=object)
    sys.modules['oops'] = _oops

# -- Project information -----------------------------------------------------

project = 'rms-metadata-tools'
copyright = '2025, SETI Institute'
author = 'SETI Institute'

# The full version, including alpha/beta/rc tags
try:
    release = importlib.metadata.version('rms-metadata-tools')
except importlib.metadata.PackageNotFoundError:
    release = '1.0.0'  # fallback for development

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',
    'myst_parser',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# CONTRIBUTING.md is split in contributing.rst; the tail fragment starts at
# "## ..." so MyST reports a false-positive heading-level warning.
suppress_warnings = ['myst.header']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

add_module_names = False
autodoc_typehints_format = "short"

# Host config modules (`host_config`, `index_config`, `geometry_config`) are
# imported as top-level modules by the engine and only resolve when the current
# working directory is a host directory. They cannot be imported on the docs
# builder, so they are mocked for autodoc.
autodoc_mock_imports = [
    'host_config',
    'index_config',
    'geometry_config',
]

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

# MyST-Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Mermaid settings — use client-side rendering so no mmdc binary is required
# in CI or on ReadTheDocs.
mermaid_output_format = 'raw'

# -- Nitpicky cross-reference exceptions -------------------------------------
#
# In nitpicky mode (`-n`) Sphinx flags every cross-reference (including those
# generated from type annotations) that has no resolvable target. The entries
# below cover symbols that genuinely have no Sphinx inventory to link to:
# third-party dependencies that do not publish an objects.inv, and the local
# `oops` import shim. Symbols owned by this package are deliberately NOT listed,
# so a broken reference to our own code still fails the build.
nitpick_ignore_regex = [
    # rms-filecache — FCPath and friends (no published inventory).
    (r'py:.*', r'filecache\..*'),
    (r'py:.*', r'FCPath'),
    # PDS support libraries (no published inventories).
    (r'py:.*', r'pdstable\..*'),
    (r'py:.*', r'pdsparser\..*'),
    (r'py:.*', r'pdstemplate\..*'),
    (r'py:.*', r'Pds3Table'),
    (r'py:.*', r'PdsLabel'),
    (r'py:.*', r'PdsTemplate'),
    (r'py:.*', r'pdslogger\..*'),
    (r'py:.*', r'PdsLogger'),
    # SPICE / geometry stack (oops, polymath, julian, cspyce, fortranformat).
    (r'py:.*', r'oops(\..*)?'),
    (r'py:.*', r'polymath(\..*)?'),
    (r'py:.*', r'julian(\..*)?'),
    (r'py:.*', r'cspyce(\..*)?'),
    (r'py:.*', r'fortranformat(\..*)?'),
    (r'py:.*', r'ff\..*'),
    # numpy typing aliases and scalar types that do not resolve through the
    # numpy inventory.
    (r'py:.*', r'npt\..*'),
    (r'py:.*', r'numpy\.typing\..*'),
    (r'py:.*', r'numpy\.float64'),
    (r'py:.*', r'numpy\.bool_'),
    # pytest publishes no Sphinx inventory in this build's intersphinx config.
    (r'py:.*', r'pytest\..*'),
]
