==================
Coding conventions
==================

The authoritative coding standards live in the project's ``.cursor/rules/``
files (most are always applied) and are summarized in ``CLAUDE.md``. Read the
relevant rule before non-trivial work. The highlights:

Paths
=====

All file access goes through ``rms-filecache`` (``FCPath``), which transparently
handles local and remote (``gs://``, ``s3://``) storage. Normalize inputs with
``FCPath(x)`` at function boundaries and never downcast to :class:`pathlib.Path`
or :class:`str` to "simplify". For libraries that need a real local file, use
``retrieve()`` / ``get_local_path()`` and ``upload()``. Prefer
``try``/``except FileNotFoundError`` over ``exists()`` pre-checks, and never
``mkdir`` through ``FCPath`` (including log directories).

Logging
=======

Use the global :class:`pdslogger.PdsLogger` via
:func:`~metadata_tools.common.get_logger` -- never the standard
:mod:`logging` module or bare ``print`` in library code. Use
``with logger.open(header):`` for sections and ``%``-style deferred formatting
(``logger.info('to %s', path)``) rather than f-strings in log calls.

Python style and typing
=======================

Maximum line length is 100. The project does not run ``ruff format`` as a gate;
``ruff check`` is the linter. Annotate every parameter and return value
(including ``-> None``); ``mypy`` runs in strict mode. Use modern generic syntax
(``list[str]``, ``X | None``). Docstrings are Google style with a
``Parameters:`` section, wrapped at 90 columns. Do not add backwards-compatibility
code unless asked, and keep modules under 1000 lines.

Testing
=======

Tests are pytest only (new tests are not :class:`unittest.TestCase`),
independent and parallel-safe, and assert precise values
(:func:`pytest.approx` for floats). The coverage target is at least 90%. See
:doc:`dev_guide_environment` for how to run them.

Documentation
=============

Documentation is Sphinx, hosted on ReadTheDocs. Every module, class, function,
and method has a Google-style docstring; the API reference is generated from
them. Narrative prose cross-references every code object with the appropriate
Sphinx role. The docs MUST build clean under both ``sphinx-build -W`` and
``sphinx-build -n``. Keep docstrings, narrative pages, and the ``README`` in
sync with the code in the same change.

Git and dependencies
====================

Use Conventional Commit subjects, work on ``feature/<name>`` or ``bugfix/<name>``
branches, and merge to ``main`` via a squashed pull request. Dependencies and
all tool configuration are declared in ``pyproject.toml``.
