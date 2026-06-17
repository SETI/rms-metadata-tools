=================
Environment setup
=================

Development checkout
====================

.. code-block:: bash

   git clone https://github.com/SETI/rms-metadata-tools.git
   cd rms-metadata-tools
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"

The ``dev`` extra installs the linting, type-checking, test, and documentation
tooling (and pulls in the ``docs`` extra). The toolchain assumes a virtual
environment at ``./venv``; the helper scripts honor ``VENV`` / ``VENV_PATH`` to
override that.

Environment variables
=====================

The engine reads no environment variable directly; path arguments are expanded
for ``$NAME`` references at runtime (see
:doc:`/user_guide/user_guide_installation`). For development the relevant
variables are those the **test suite** reads at import time:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Variable
     - Meaning
   * - ``RMS_METADATA``
     - Root of the metadata holdings tree. Read in ``tests/archive_support.py``.
   * - ``RMS_VOLUMES``
     - Root of the data volume tree. Read in ``tests/archive_support.py``.

The default test run is hermetic and does not need these, but the top-level
``tests/`` package imports ``archive_support`` at collection time, so the
variables must be *defined* (even if pointed at a placeholder) for collection to
succeed. The archive-backed and host tests additionally require the real trees
and SPICE kernels.

Running the entry points
========================

Run a host's programs from inside its directory, because they import their
configuration as top-level modules:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" -vv GO_0017

A fast smoke test is to add ``--first 5`` to the geometry stage so it stops
after five images. See :doc:`/user_guide/user_guide_examples`.

Running the tests
=================

The suite is pytest-based; configuration lives in ``pyproject.toml``
(``pythonpath = src``, ``-n auto``, coverage on by default). Two markers gate
the slow tiers and are excluded by default:

- ``integration`` — requires ``oops``/SPICE host initialization.
- ``requires_archive`` — requires the ``$RMS_METADATA`` holdings tree.

.. code-block:: bash

   pytest                                   # default hermetic engine suite
   pytest tests/test_index.py               # one file
   pytest tests/test_index.py::Test_Index_Common::test_supplemental_index_common
   pytest -m requires_archive               # the archive-backed tier
   pytest -n 1                              # serial (easier to read failures)

The default run measures coverage of the host-agnostic engine (the ``hosts/``
package, ``bodies.py``, and ``tests/`` are excluded from the denominator; see
``[tool.coverage]`` in ``pyproject.toml``). The project targets at least 90%
coverage. Host-specific tests live under ``tests/hosts/<HOST>/`` and carry the
``requires_archive`` marker.

Linting, typing, and docs
=========================

The single command that runs every quality gate, kept in sync with CI, is:

.. code-block:: bash

   scripts/run-all-checks.sh        # everything, in parallel
   scripts/run-all-checks.sh -s     # sequential (easier to read failures)
   scripts/run-all-checks.sh -c     # code checks only
   scripts/run-all-checks.sh --pytest   # a single check (also --ruff-check, --mypy, ...)

The individual tools, run from the repository root inside the venv:

.. code-block:: bash

   ruff check src tests
   ruff format --check src tests
   mypy src tests
   bandit -c pyproject.toml -r src -q
   vulture src tests
   sphinx-build -W -b html docs docs/_build
   sphinx-build -n -b html docs docs/_build
   pymarkdown scan docs/ README.md CONTRIBUTING.md

The documentation MUST build clean under both ``-W`` (warnings as errors) and
``-n`` (nitpicky) before delivery. To build and open the docs locally:

.. code-block:: bash

   scripts/read-docs.sh

CI/CD and release
=================

The ``Run Tests`` GitHub Actions workflow runs on pull requests to ``main``,
pushes to ``main``, a weekly schedule, and manual dispatch. It has two jobs:

- **lint** (Python 3.13): ``ruff check``, ``ruff format --check``, ``mypy``,
  ``bandit``, ``vulture``, the ``sphinx-build -W`` docs build, and ``pymarkdown``.
- **test**: the pytest suite with coverage across Python 3.11, 3.12, and 3.13,
  uploading coverage to Codecov.

Releases are tag-driven: the version is derived from Git tags by
``setuptools_scm`` (written to ``src/metadata_tools/_version.py``), and separate
workflows publish to TestPyPI and PyPI.

Contribution workflow
=====================

Use Conventional Commit subjects (``feat:``, ``fix:``, ``docs:``, ...), work on
``feature/<name>`` or ``bugfix/<name>`` branches, and merge to ``main`` via a
squashed pull request. The full policy is in :doc:`/contributing`.
