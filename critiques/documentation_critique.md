# Documentation Critique Report

**Generated:** 2026-07-08
**Scope:** All files under `docs/`, `README.md`, `CONTRIBUTING.md`, all module/class/function
docstrings in `src/metadata_tools/`, and `pyproject.toml` documentation-adjacent sections.
Rules applied: `.cursor/rules/doc_python.mdc`, `.cursor/rules/doc_readme.mdc`,
`.cursor/rules/doc_user_guide.mdc`, `.cursor/rules/doc_dev_guide.mdc`,
`.cursor/rules/doc_how_to.mdc`, `.cursor/rules/documentation.mdc`.

**Note on prior critique (2026-06-29):** The previous version of this file made incorrect
assertions ("User guide — PASS", "sphinx-build passes with zero warnings"). This version
replaces it with findings based on actual file content read 2026-07-08.

---

## Executive summary

The documentation has serious accuracy gaps that will mislead users and break the
sphinx-build `-n` (nitpicky) check. Two issues are severe enough to be considered
blocking:

1. **The user guide instructs users to run old-style per-host scripts** (`python
   GO_0xxx_index.py`) from the host directory — but the package now ships seven
   installable console scripts (`metadata-index`, `metadata-geometry`, etc.). The
   installation section explicitly says "The package does not install console
   scripts", which is the opposite of the truth.

2. **`dev_guide_support_subsystem.rst` cross-references three functions**
   (`:func:`~metadata_tools.common.add_task``, `write_task_file`, `task_source`)
   that do not exist in `metadata_tools.common`. They live in
   `metadata_tools.task_list_support`. These stale Sphinx cross-references cause
   `sphinx-build -n` to emit warnings (failures if run with `-W -n` combined).

Beyond those blockers, the `src/metadata_tools/__init__.py` package docstring is
completely outdated and the `dev_guide_layout.rst` source tree is missing the `cli/`
package, `task_list_support.py`, and `config.py` — all of which now exist and are
central to the architecture.

Ten additional issues are documented below, ranging from missing module docstrings to
a contradictory statement about `ruff format` in the conventions chapter.

**Summary by priority:**

| Priority | Count | Key items |
|----------|-------|-----------|
| Critical | 2 | User-guide console-script inversion, stale `common.py` cross-refs |
| High | 7 | Stale `__init__.py` docstring, missing `cli/` in layout, missing module docstrings (10 files), missing CLI `main()` docstrings (7 functions), wrong `Args:` in `_host.py`, old-style examples throughout user guide |
| Medium | 4 | `dev_guide_conventions.rst` contradicts `ruff format` truth, missing API pages (`config`, `task_list_support`), `CONTRIBUTING.md` build command and commit example |
| Low | 2 | README section title `Licensing` vs `License`, stale `py.typed` comment in `pyproject.toml` |

---

## 1. Documentation system and build (`doc_python`)

**Finding C1 (Critical) — `sphinx-build -n` fails due to stale cross-references.**
`docs/dev_guide/dev_guide_support_subsystem.rst:29-33` contains:

```rst
- The cloud-task plumbing
  (:func:`~metadata_tools.common.add_task`,
  :func:`~metadata_tools.common.write_task_file`,
  :func:`~metadata_tools.common.task_source`) shared by the ``*_cloud.py``
  workers.
```

`grep` confirms none of `add_task`, `write_task_file`, or `task_source` exist in
`src/metadata_tools/common.py`. These functions live in
`src/metadata_tools/task_list_support.py` (confirmed by reading that file). The
stale cross-references make `sphinx-build -n` emit unresolved-reference warnings;
combined with `-W` this turns them into errors.

**Fix:** In `dev_guide_support_subsystem.rst:29-33`, replace the three `:func:` cross-references and the surrounding sentence. The corrected text should be:

```rst
- The cloud-task plumbing
  (:func:`~metadata_tools.task_list_support.make_task`,
  :func:`~metadata_tools.task_list_support.task_generator`,
  :func:`~metadata_tools.task_list_support.write_task_file`,
  :func:`~metadata_tools.task_list_support.scan_volumes`) is in
  :mod:`metadata_tools.task_list_support`, not in :mod:`~metadata_tools.common`.
```

Also update the `common.py` bullet (line 31 of that file) description of `common` to
remove the claim that it contains cloud-task plumbing; that responsibility has moved.

---

## 2. Docstrings and API reference (`doc_python`)

**Finding H1 (High) — `src/metadata_tools/__init__.py` module docstring is completely stale.**
The public package docstring (lines 4-84) describes the old architecture and contains
multiple inaccuracies:

- Lines 39-41 instruct users to run `<collection>_index.py`, `<collection>_geometry.py`,
  `<collection>_cumulative.py` — these per-host scripts no longer exist. The package now
  ships console scripts (`metadata-index`, `metadata-geometry`, `metadata-cumulative`).
- Line 81 says: "Add a row to the format dictionary in `geometry_support.py`" —
  `geometry_support` is now a package; the format dictionary lives in
  `geometry_support/formats.py`.
- The docstring uses `####` RST section headers inside a Python `"""` string. This is not
  valid Google-style and does not render correctly in autodoc — autodoc expects prose, not
  RST section headers in module docstrings.
- The "Generating New Metadata Tables" section (lines 47-59) describes a manual copy
  workflow that is now handled by the config registry; it omits the `cli/` step and
  references `hosts/` scripts that no longer exist.

**Evidence:** `src/metadata_tools/__init__.py:4-84`.

**Fix:** Replace the entire module docstring with a concise, Google-style description
covering: what the package does, the three-stage pipeline, and the console entry points.
Example replacement:

```python
"""PDS Ring-Moon Systems Node metadata table generator.

``rms-metadata-tools`` generates PDS3 index, geometry, and cumulative metadata
tables (and their PDS3 labels) for planetary science data collections. Each table
row holds metadata for one data file (e.g. an image).

Three stages are run in order for each collection:

1. **Index** — supplemental index columns sourced from PDS labels
   (``metadata-index HOST_ID ...``).
2. **Geometry** — geometric quantities computed from SPICE via ``oops``
   (``metadata-geometry HOST_ID ...``).
3. **Cumulative** — per-volume table concatenations across a volume tree
   (``metadata-cumulative HOST_ID ...``).

Per-collection configuration lives in
``src/metadata_tools/hosts/<HOST>/`` (e.g. ``GO_0xxx/`` for Galileo SSI).
See the `user guide <https://rms-metadata-tools.readthedocs.io>`_ for setup
and usage, and the developer guide for extending to a new host.
"""
```

**Finding H2 (High) — `geometry_support/__init__.py` has no module docstring.**
`src/metadata_tools/geometry_support/__init__.py` contains only a `#`-style banner
comment (lines 1-8). `ast.get_docstring()` returns `None`; autodoc renders a blank
description for the `metadata_tools.geometry_support` module page.

**Evidence:** `src/metadata_tools/geometry_support/__init__.py:1-8`.

**Fix:** Insert a `"""..."""` module docstring immediately after the `#` banner:

```python
"""Geometry table generation engine for metadata_tools.

Computes geometric quantities (body, ring, sky, sun) from SPICE via ``oops``
and writes them as PDS3 summary (and optionally detailed) CSV tables.
Re-exports the public surface: :class:`Record`, :class:`Suite`,
:data:`FORMAT_DICT`, :data:`ALT_FORMAT_DICT`, and the table classes.
"""
```

**Finding H3 (High) — Nine `geometry_support` submodules lack module-level docstrings.**
Every file below has only a `#`-style banner header; none has a `"""..."""` module
docstring, so autodoc generates blank module descriptions:

| File | Current banner text |
|---|---|
| `geometry_support/bodies_select.py` | Body selection and primary lookup |
| `geometry_support/masks.py` | Excluded-pixel mask construction |
| `geometry_support/prep.py` | Row preparation for a geometry record |
| `geometry_support/formatting.py` | Column value formatting helpers |
| `geometry_support/formats.py` | Geometry column format dictionaries |
| `geometry_support/record.py` | The Record class (one geometry table row) |
| `geometry_support/tables.py` | Geometry table classes |
| `geometry_support/suite.py` | The Suite class (a volume's geometry tables) |
| `geometry_support/process.py` | Entry points for geometry table generation |

**Fix:** Add a one-sentence `"""..."""` module docstring to each file, inserted
immediately after the `#` banner and before the first `import`. Use the existing banner
text as the source material. Example:

```python
# geometry_support/formats.py - Geometry column format dictionaries.
################################################################################
"""Master format dictionaries (FORMAT_DICT, ALT_FORMAT_DICT) for geometry columns."""
```

**Finding H4 (High) — Seven CLI `main()` functions have no docstrings.**
All seven `src/metadata_tools/cli/*.py` entry-point modules define a `main() -> None`
function with no docstring. `doc_python` and `mypy` strict mode both flag missing
docstrings on public functions:

| File | Line |
|---|---|
| `cli/index.py` | 15 |
| `cli/geometry.py` | 16 |
| `cli/cumulative.py` | 15 |
| `cli/task_list.py` | 25 |
| `cli/index_cloud.py` | 60 |
| `cli/geometry_cloud.py` | 70 |
| `cli/cumulative_cloud.py` | 52 |

**Fix:** Add a one-line docstring to each `main()`:

```python
def main() -> None:
    """Entry point for the ``metadata-index`` console script."""
```

Use the module-level docstring's first sentence as source material for the per-file
variant. These functions are not autodoc'd but the missing docstring is still a
violation of the project's "every function has a docstring" rule.

**Finding H5 (High) — `cli/_host.py::run_cloud_worker` uses `Args:` not `Parameters:`.**
`src/metadata_tools/cli/_host.py:173` uses `Args:` as the docstring section header.
The project mandates Google style with `Parameters:` (`.cursor/rules/doc_python.mdc` §3,
`.cursor/rules/python.mdc`).

**Evidence:** `src/metadata_tools/cli/_host.py:173`.

**Fix:** Change `Args:` → `Parameters:` at line 173 of `_host.py`.

**Finding M1 (Medium) — Missing API reference pages for `config` and `task_list_support`.**
`docs/dev_guide/api/` contains autodoc pages for `core`, `index_support`,
`geometry_support`, `cumulative_support`, and `columns`, but has no pages for
`metadata_tools.config` or `metadata_tools.task_list_support`. Both modules are
public engine components used by every CLI entry point, and both have complete
Google-style docstrings. The dev guide refers to `task_list_support` in prose
(once corrected per C1 fix above) but there is no autodoc page.

**Fix:** Add two new RST files under `docs/dev_guide/api/`:

`docs/dev_guide/api/config.rst`:
```rst
======
config
======

.. automodule:: metadata_tools.config
   :members:
   :undoc-members:
   :show-inheritance:
```

`docs/dev_guide/api/task_list_support.rst`:
```rst
=================
task_list_support
=================

.. automodule:: metadata_tools.task_list_support
   :members:
   :undoc-members:
   :show-inheritance:
```

Add both to the `toctree` in `docs/dev_guide/api/api.rst`.

---

## 3. Cross-reference completeness (`doc_python`)

**Finding C1 (Critical) — already documented above.** Three `:func:` cross-references in
`dev_guide_support_subsystem.rst` resolve to functions that don't exist in the referenced
module (`metadata_tools.common`). This is the most severe documentation defect because
it causes `sphinx-build -n` failures.

No other unresolved cross-references were found. All other `:func:`, `:class:`,
`:mod:`, `:data:` roles resolve to real objects. `nitpick_ignore_regex` in `conf.py`
correctly suppresses third-party symbols that lack inventories.

---

## 4. README (`doc_readme`)

**PASS — largely compliant.** All required sections are present in order: title, badges,
introduction, features, installation, quick start, documentation, contributing, links.
The `<!-- start-after-point -->` marker is correctly placed and consumed by
`docs/index.rst`. The Quick Start examples use the correct `metadata-index GO_0xxx ...`
console-script syntax (consistent with `pyproject.toml`).

**Finding L1 (Low) — Section title `Licensing` should be `License`.**
`doc_readme` §8 specifies `## License` as the final section title. The README uses
`## Licensing`.

**Evidence:** `README.md` (search for `## Licensing`).

**Fix:** Rename `## Licensing` → `## License`.

---

## 5. User guide (`doc_user_guide`)

**Finding C2 (Critical) — Installation section describes non-existent per-host scripts.**
`docs/user_guide/user_guide_installation.rst:139-154` states:

> "The package does not install console scripts. Each collection has its own set of
> runnable entry-point scripts in its host directory under
> `src/metadata_tools/hosts/<HOST>/`. Because those scripts import their configuration
> as top-level modules (`import host_config`, `import index_config`, `import
> geometry_config`), they resolve **only when the current working directory is the host
> directory**. Always `cd` into the host directory first:
>
>     cd src/metadata_tools/hosts/GO_0xxx
>     python GO_0xxx_index.py ..."

This is the opposite of the truth. `pyproject.toml:116-123` declares seven console
scripts installed by `pip install`:

```toml
[project.scripts]
metadata-index            = "metadata_tools.cli.index:main"
metadata-geometry         = "metadata_tools.cli.geometry:main"
metadata-cumulative       = "metadata_tools.cli.cumulative:main"
metadata-index-cloud      = "metadata_tools.cli.index_cloud:main"
metadata-geometry-cloud   = "metadata_tools.cli.geometry_cloud:main"
metadata-cumulative-cloud = "metadata_tools.cli.cumulative_cloud:main"
metadata-task-list        = "metadata_tools.cli.task_list:main"
```

These scripts take `HOST_ID` as the first positional argument and resolve host config
via the config registry — they work from any directory. The `cd` workaround is not
needed.

**Evidence:** `docs/user_guide/user_guide_installation.rst:139-154`,
`pyproject.toml:116-123`, `src/metadata_tools/cli/` (all entry points).

**Fix:** Replace the "Running the programs" section (lines 137-154) with:

```rst
Running the programs
====================

Installing the package registers seven console scripts. Each takes ``HOST_ID``
(e.g. ``GO_0xxx``) as its first argument and can be run from any directory:

.. code-block:: text

   metadata-index HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry HOST_ID [options] metadata_tree output_tree
   metadata-cumulative HOST_ID [options] cumulative_dir

   metadata-index-cloud HOST_ID [options] ...
   metadata-geometry-cloud HOST_ID [options] ...
   metadata-cumulative-cloud HOST_ID [options] ...
   metadata-task-list HOST_ID tree_dir --output FILE

A quick smoke test for GO_0xxx:

.. code-block:: bash

   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" GO_0017
   metadata-geometry GO_0xxx "$RMS_METADATA/GO_0xxx/" "$RMS_METADATA_TEST/GO_0xxx/" \
       GO_0017 --first 5

See the per-program chapters for the full option reference.
```

**Finding H6 (High) — All user guide example sections use old-style `python <HOST>_*.py` syntax.**
`docs/user_guide/user_guide_examples.rst:7,21,24-25,28,31,45-49` instructs users to
`cd src/metadata_tools/hosts/GO_0xxx` and run `python GO_0xxx_index.py ...`. No such
scripts exist in the installed package. The same pattern appears in:

- `user_guide_index.rst:5-10` ("Each host ships an index program named `<HOST>_index.py`")
- `user_guide_geometry.rst` (references `<HOST>_geometry.py`)
- `user_guide_cumulative.rst` (references `<HOST>_cumulative.py`)
- `user_guide_cloud.rst` (references `*_cloud.py` counterparts in the host directory)

**Fix:** Replace all occurrences of `python <HOST>_<stage>.py ...` with the
`metadata-<stage> <HOST_ID> ...` console-script form. The `cd src/...` step must be
removed. The cloud guide should reference `metadata-index-cloud`, `metadata-geometry-cloud`,
and `metadata-cumulative-cloud` instead of per-host `*_cloud.py` scripts.

Example replacement for `user_guide_index.rst:5-10`:

```rst
The ``metadata-index`` command generates the supplemental index table and its PDS3
label for every volume in a tree, by reading each data product's PDS3 label. Under
the hood it calls :func:`~metadata_tools.index_support.process_index`. It can be
run from any directory:

.. code-block:: text

   metadata-index HOST_ID [options] volume_tree metadata_tree output_tree
```

---

## 6. Developer guide (`doc_dev_guide`)

**Finding H7 (High) — `dev_guide_layout.rst` source tree is missing core modules.**
`docs/dev_guide/dev_guide_layout.rst:28-43` lists the source tree but omits:

- `cli/` — the entire CLI entry-point package (7 modules), which is now the primary
  user-facing interface to the tool
- `task_list_support.py` — task file generation used by all cloud entry points
- `config.py` — the host config registry used by every CLI module
- `_version.py` — generated by `setuptools_scm`

Additionally, line 32 shows `index_support.py` as a file, but `index_support` is now
a package (`index_support/__init__.py`, `process.py`, `table.py`, `key_fns.py`).

**Evidence:** `ls src/metadata_tools/` (files present: `cli/`, `task_list_support.py`,
`config.py`, `_version.py`; `index_support/` is a directory).

**Fix:** Update the main source-tree layout block in `dev_guide_layout.rst` to:

```text
src/
  metadata_tools/         # the importable engine (public package)
    __init__.py           # package docstring and version
    common.py             # Table base class, global logger, and CLI args
    config.py             # host config registry (set_host / get_*_config)
    task_list_support.py  # task file generation for cloud workers
    index_support/        # IndexTable and process_index() (package)
      __init__.py
      process.py
      table.py
      key_fns.py
    geometry_support/     # geometry engine (package)
    cumulative_support.py # cumulative table concatenation
    label_support.py      # PDS3 label generation from templates
    cli/                  # installed console-script entry points
      index.py            # metadata-index
      geometry.py         # metadata-geometry
      cumulative.py       # metadata-cumulative
      index_cloud.py      # metadata-index-cloud
      geometry_cloud.py   # metadata-geometry-cloud
      cumulative_cloud.py # metadata-cumulative-cloud
      task_list.py        # metadata-task-list
      _host.py            # shared host-directory injection helpers
    columns/              # geometry column definitions (body/ring/sky/sun)
    bodies.py             # builds the oops Body registry
    util.py               # path, text, time, and math utilities
    defs.py               # constants (body names, ring radii, paths)
    _version.py           # version string (auto-generated by setuptools_scm)
    templates/            # shared PDS3 label-template fragments
    hosts/                # per-collection configuration
      GO_0xxx/            # Galileo SSI host (the reference example)
```

Also update the `common.py` inline description to say "Table base class, global logger,
and CLI args" (removing "task plumbing" which has moved to `task_list_support.py`).

**Finding M2 (Medium) — `dev_guide_conventions.rst:32` contradicts `ruff format` truth.**
`docs/dev_guide/dev_guide_conventions.rst:32-33` states:

> "The project does not run `ruff format` as a gate; `ruff check` is the linter."

This is incorrect. Both `scripts/run-all-checks.sh:383-384` and
`docs/dev_guide/dev_guide_environment.rst:102,123` confirm that `ruff format --check
src tests` IS run as part of the quality gate. The conventions chapter is wrong;
the environment chapter is correct.

**Evidence:** `scripts/run-all-checks.sh:383-384` (`python -m ruff format --check src tests`),
`dev_guide_environment.rst:102` (`ruff format --check src tests` in the quality-gate list),
`dev_guide_conventions.rst:32-33`.

**Fix:** Change `dev_guide_conventions.rst:32-33` to:

```rst
Maximum line length is 100. Code is formatted with ``ruff format`` (single quotes;
see ``pyproject.toml [tool.ruff.format]``); both ``ruff format --check`` and
``ruff check`` run in CI and as part of ``scripts/run-all-checks.sh``.
```

Do not change `dev_guide_environment.rst` — it is correct.

---

## 7. How-to articles (`doc_how_to`)

**Finding L2 (Low) — No standalone how-to articles.**
`doc_how_to` expects standalone, action-oriented articles with prerequisites, numbered
steps with exact expected results, and troubleshooting. The user guide appendix
(`user_guide_examples.rst`) covers end-to-end workflows but as embedded prose, not
structured how-to articles.

This is a minor gap; the material exists in the right place for most users.

**Fix (optional):** Extract 2–3 key workflows from `user_guide_examples.rst` into a
`docs/how_to/` directory:
- `how_to_generate_supplemental_index.rst`
- `how_to_run_gcp_pipeline.rst`
- `how_to_add_new_host.rst`

Each article must have: action-oriented title, 1–3 sentence intro, "Prerequisites"
section, numbered steps with exact results, "Troubleshooting" section, and "See also"
cross-links to the user guide chapters.

---

## 8. Diagrams and figures

**PASS.** A Mermaid workflow diagram appears in `user_guide_overview.rst` and a Mermaid
class diagram appears in `dev_guide_architecture.rst`. The `sphinxcontrib.mermaid`
extension is configured (`mermaid_output_format = 'raw'`).

**Note:** After fixing C2 and H7 above, verify that the architecture diagram's mention
of `SunTable` matches the actual code state (it is in `geometry_support/tables.py` and
`geometry_support/__init__.py`'s `__all__` but commented out in `suite.py:176`). The
existing critique (H4 in the prior version) noted this as a potential architecture
diagram inconsistency; confirm the current state of `suite.py:176` before acting.

---

## 9. Change discipline and consistency (`doc_python`)

**Finding M3 (Medium) — `CONTRIBUTING.md` uses `make html` for docs build.**
`CONTRIBUTING.md` instructs contributors to build docs with `cd docs && make html`,
which runs without `-W` and does not catch warnings. The canonical build command is
`scripts/read-docs.sh` (applies `-W`, opens browser) or equivalently `sphinx-build -W
-b html docs docs/_build`.

**Evidence:** `CONTRIBUTING.md` (search for `make html`).

**Fix:** Replace `cd docs && make html` with `scripts/read-docs.sh`. Add:
"The `scripts/run-all-checks.sh` script runs all quality gates (lint, type-check,
tests, docs, and markdown) and is the canonical pre-push check."

**Finding M4 (Medium) — `CONTRIBUTING.md` commit message example does not follow Conventional Commits.**
The project mandates Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) per
`dev_guide_conventions.rst`. The `CONTRIBUTING.md` example (`git commit -m "Add
feature: description of your changes"`) does not follow this format.

**Fix:** Replace the example with:
```
feat: add ring-plane geometry for GO_0xxx
```
Add a pointer to the Conventional Commits specification and to
`docs/dev_guide/dev_guide_conventions.rst`.

**Finding L3 (Low) — `pyproject.toml` comment contradicts shipped `py.typed`.**
`pyproject.toml:78-79` contains the comment:

> "py.typed is intentionally NOT declared: the package is not yet fully annotated, so
> advertising it as typed would mislead downstream type checkers."

But `pyproject.toml:82` includes `"py.typed"` in `package-data`, and the file
`src/metadata_tools/py.typed` exists. PEP 561 dictates that if `py.typed` ships in
the wheel, downstream type checkers will treat the package as fully typed. The comment
is factually wrong.

**Evidence:** `pyproject.toml:78-79,82`, `src/metadata_tools/py.typed` (file exists).

**Fix:** Remove the misleading comment. If `py.typed` is intentionally shipped, replace
with:
```toml
# py.typed ships PEP 561 inline type information to downstream type-checkers
```
If it should NOT be shipped, remove it from `package-data` and delete the file.

---

## Recommended priorities

Ordered by impact. Items 1–2 are blocking (they produce wrong output for users or break
the `-n` sphinx build).

1. **C1 — Fix stale cross-references in `dev_guide_support_subsystem.rst`** (~5 min).
   Change `:func:`~metadata_tools.common.add_task``, `write_task_file`, `task_source`
   to their correct locations in `metadata_tools.task_list_support`. Then run
   `sphinx-build -W -n -b html docs /tmp/sphinx-out` and verify zero warnings.

2. **C2 — Rewrite the "Running the programs" section of `user_guide_installation.rst`**
   (~20 min). Remove the false "no console scripts" paragraph and replace it with the
   correct `metadata-index HOST_ID ...` console-script form. Update all example sections
   that use `python GO_0xxx_*.py` to use console scripts instead.

3. **H1 — Replace stale `__init__.py` module docstring** (~10 min). The entire package
   docstring is stale; rewrite it as a concise Google-style description referencing the
   console scripts and the three-stage pipeline.

4. **H2–H3 — Add module docstrings to `geometry_support` package and its 9 submodules**
   (~15 min). Insert one-sentence `"""..."""` docstrings after each `#` banner. Zero
   behavior change; instant improvement to autodoc API pages.

5. **H7 — Update `dev_guide_layout.rst` source tree** (~10 min). Add `cli/`,
   `task_list_support.py`, `config.py`, and fix `index_support.py` → `index_support/`.

6. **H4–H5 — Add `main()` docstrings; fix `Args:` → `Parameters:` in `_host.py`**
   (~10 min). One-line docstrings on the 7 `main()` functions; change `Args:` to
   `Parameters:` in `_host.py:173`.

7. **H6 — Update all user guide example sections** (~15 min). Replace every
   `python GO_0xxx_*.py` invocation with the equivalent `metadata-<stage> GO_0xxx ...`
   console script.

8. **M1 — Add API pages for `config` and `task_list_support`** (~5 min). Two new RST
   files; add them to the `api.rst` toctree.

9. **M2 — Fix `dev_guide_conventions.rst` `ruff format` claim** (~2 min). Change the
   sentence to say `ruff format --check` IS run as a gate.

10. **M3–M4 — Fix `CONTRIBUTING.md`** (~5 min). Replace `make html`; fix commit example.

11. **L1 — Rename README `## Licensing` → `## License`** (~1 min).

12. **L3 — Fix `pyproject.toml` `py.typed` comment** (~2 min).

---

## Prompt for an AI agent to fix the documentation

You are fixing documentation issues in the `rms-metadata-tools` Python package. The
repository root is the working directory. Source code is under `src/metadata_tools/`;
Sphinx docs are under `docs/`. Rules are in `.cursor/rules/doc_*.mdc`. Do not change
any production code behavior — only docstrings, documentation files, comment text, and
CI/script configuration are in scope.

**Verification gate (MUST pass before reporting success):**
```sh
sphinx-build -W -n -b html docs /tmp/sphinx-out
```
Zero warnings and zero errors required. Run this LAST, after all changes.

---

### Fix 1 — Stale cross-references in dev_guide_support_subsystem.rst (Critical)

**File:** `docs/dev_guide/dev_guide_support_subsystem.rst`

Read the file. Find the `common` section that mentions cloud-task plumbing. It currently
cross-references `:func:`~metadata_tools.common.add_task``,
`:func:`~metadata_tools.common.write_task_file``, and
`:func:`~metadata_tools.common.task_source``.

Verify: run `grep -n "add_task\|write_task_file\|task_source" src/metadata_tools/common.py`
and confirm these return nothing (they don't exist in `common.py`).

Verify: run `grep -n "def add_task\|def write_task_file\|def task_source\|def make_task\|def task_generator\|def scan_volumes\|def write_task_file" src/metadata_tools/task_list_support.py`
to see what the actual function names are.

Then edit the bullet in `dev_guide_support_subsystem.rst` to reference the correct
module and correct function names from `task_list_support.py`. Remove the claim from
the `common.py` description that it contains cloud-task plumbing.

---

### Fix 2 — Rewrite "Running the programs" in user_guide_installation.rst (Critical)

**File:** `docs/user_guide/user_guide_installation.rst`

Read the file. The section starting "Running the programs" (around line 137) currently
says "The package does not install console scripts" and tells users to `cd` into the
host directory and run `python GO_0xxx_index.py`. This is completely wrong.

Read `pyproject.toml:116-123` to see the actual installed console scripts:
`metadata-index`, `metadata-geometry`, `metadata-cumulative`, `metadata-index-cloud`,
`metadata-geometry-cloud`, `metadata-cumulative-cloud`, `metadata-task-list`.

Replace the "Running the programs" section entirely with:

```rst
Running the programs
====================

Installing the package registers seven console scripts. Each takes ``HOST_ID``
(e.g. ``GO_0xxx``) as its first argument and can be run from any working
directory:

.. code-block:: text

   metadata-index HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry HOST_ID [options] metadata_tree output_tree
   metadata-cumulative HOST_ID [options] cumulative_dir

   metadata-index-cloud HOST_ID [options] ...
   metadata-geometry-cloud HOST_ID [options] ...
   metadata-cumulative-cloud HOST_ID [options] ...
   metadata-task-list HOST_ID tree_dir --output FILE

See the per-program chapters for the full option reference.
```

---

### Fix 3 — Replace stale `__init__.py` module docstring (High)

**File:** `src/metadata_tools/__init__.py`

Read the file. The module docstring (lines 4-84) is completely stale: it references
`<collection>_index.py` scripts that don't exist, uses `####` RST headers inside a
docstring (invalid Google style), and references `geometry_support.py` as a file
(it's now a package with the format dict in `geometry_support/formats.py`).

Replace the entire content between the triple-quote delimiters with:

```python
"""PDS Ring-Moon Systems Node metadata table generator.

``rms-metadata-tools`` generates PDS3 index, geometry, and cumulative metadata
tables (and their PDS3 labels) for planetary science data collections. Each table
row holds metadata for one data file (e.g. an image).

Three stages run in order for each collection:

1. **Index** — supplemental index columns sourced from PDS labels
   (``metadata-index HOST_ID ...``).
2. **Geometry** — geometric quantities computed from SPICE via ``oops``
   (``metadata-geometry HOST_ID ...``).
3. **Cumulative** — per-volume table concatenations across a volume tree
   (``metadata-cumulative HOST_ID ...``).

Per-collection configuration lives in
``src/metadata_tools/hosts/<HOST>/`` (e.g. ``GO_0xxx/`` for Galileo SSI).
See the user guide for setup and usage, and the developer guide for adding a
new host.
"""
```

---

### Fix 4 — Add module docstrings to geometry_support package and submodules (High)

For each file listed below, read the file, then insert a one-sentence `"""..."""`
module docstring immediately after the `################################################################################`
banner block and before the first `import` statement.

- **`src/metadata_tools/geometry_support/__init__.py`** →
  ```python
  """Geometry table generation engine: body, ring, sky, sun, and inventory tables."""
  ```

- **`src/metadata_tools/geometry_support/bodies_select.py`** →
  ```python
  """Body and system selection utilities for geometry table generation."""
  ```

- **`src/metadata_tools/geometry_support/masks.py`** →
  ```python
  """Pixel mask construction for excluded regions in geometry table rows."""
  ```

- **`src/metadata_tools/geometry_support/prep.py`** →
  ```python
  """Row preparation: assembles formatted geometry strings for one observation."""
  ```

- **`src/metadata_tools/geometry_support/formatting.py`** →
  ```python
  """Low-level column formatters that convert backplane values to fixed-width strings."""
  ```

- **`src/metadata_tools/geometry_support/formats.py`** →
  ```python
  """Master format dictionaries (FORMAT_DICT, ALT_FORMAT_DICT) for geometry columns."""
  ```

- **`src/metadata_tools/geometry_support/record.py`** →
  ```python
  """Record class: per-observation state for geometry table generation."""
  ```

- **`src/metadata_tools/geometry_support/tables.py`** →
  ```python
  """Geometry table subclasses: BodyTable, RingTable, SkyTable, InventoryTable, SunTable."""
  ```

- **`src/metadata_tools/geometry_support/suite.py`** →
  ```python
  """Suite class: coordinates all geometry tables for one data file or volume."""
  ```

- **`src/metadata_tools/geometry_support/process.py`** →
  ```python
  """Top-level entry point process_tables() for geometry table generation."""
  ```

---

### Fix 5 — Update dev_guide_layout.rst source tree (High)

**File:** `docs/dev_guide/dev_guide_layout.rst`

Read the file. The main source tree block (starting with `src/`) is missing `cli/`,
`task_list_support.py`, `config.py`, and `_version.py`. It also shows
`index_support.py` as a file when it is now a package.

Run `ls src/metadata_tools/` and `ls src/metadata_tools/cli/` to see the current
directory contents. Then update the `.. code-block:: text` block for `src/` to include:
- `config.py` (with inline description: `# host config registry`)
- `task_list_support.py` (with inline description: `# task file generation for cloud workers`)
- `_version.py` (with inline description: `# auto-generated by setuptools_scm`)
- `cli/` package with all seven entry point modules and `_host.py`
- `index_support/` as a directory with `__init__.py`, `process.py`, `table.py`, `key_fns.py`

Also update the `common.py` inline description from "Table base class, global logger,
task plumbing" to "Table base class, global logger, and CLI args" (the task plumbing
moved to `task_list_support.py`).

---

### Fix 6 — Add docstrings to CLI main() functions; fix Args: in _host.py (High)

For each file below, read it, find `def main() -> None:`, and add a one-line docstring
as the first statement in the body:

- `src/metadata_tools/cli/index.py` → `"""Entry point for the ``metadata-index`` console script."""`
- `src/metadata_tools/cli/geometry.py` → `"""Entry point for the ``metadata-geometry`` console script."""`
- `src/metadata_tools/cli/cumulative.py` → `"""Entry point for the ``metadata-cumulative`` console script."""`
- `src/metadata_tools/cli/task_list.py` → `"""Entry point for the ``metadata-task-list`` console script."""`
- `src/metadata_tools/cli/index_cloud.py` → `"""Entry point for the ``metadata-index-cloud`` console script."""`
- `src/metadata_tools/cli/geometry_cloud.py` → `"""Entry point for the ``metadata-geometry-cloud`` console script."""`
- `src/metadata_tools/cli/cumulative_cloud.py` → `"""Entry point for the ``metadata-cumulative-cloud`` console script."""`

Also in `src/metadata_tools/cli/_host.py`: find `def run_cloud_worker(` and its
docstring. Change `Args:` → `Parameters:` to comply with the Google-style rule.

---

### Fix 7 — Update all user guide example sections (High)

Read each file listed below. Replace every instance of:
- `cd src/metadata_tools/hosts/GO_0xxx` → remove this line (not needed)
- `python GO_0xxx_index.py ...` → `metadata-index GO_0xxx ...`
- `python GO_0xxx_geometry.py ...` → `metadata-geometry GO_0xxx ...`
- `python GO_0xxx_cumulative.py ...` → `metadata-cumulative GO_0xxx ...`
- `<HOST>_index.py` in prose → `metadata-index HOST_ID`
- `<HOST>_geometry.py` in prose → `metadata-geometry HOST_ID`
- `<HOST>_cumulative.py` in prose → `metadata-cumulative HOST_ID`
- `*_cloud.py` counterparts in the host directory → the corresponding console scripts

Files to update:
- `docs/user_guide/user_guide_examples.rst` (all example blocks)
- `docs/user_guide/user_guide_index.rst` (introductory paragraph and synopsis)
- `docs/user_guide/user_guide_geometry.rst` (introductory paragraph and synopsis)
- `docs/user_guide/user_guide_cumulative.rst` (introductory paragraph and synopsis)
- `docs/user_guide/user_guide_cloud.rst` (cloud variant references)

---

### Fix 8 — Add API pages for config and task_list_support (Medium)

Create `docs/dev_guide/api/config.rst`:
```rst
======
config
======

.. automodule:: metadata_tools.config
   :members:
   :undoc-members:
   :show-inheritance:
```

Create `docs/dev_guide/api/task_list_support.rst`:
```rst
=================
task_list_support
=================

.. automodule:: metadata_tools.task_list_support
   :members:
   :undoc-members:
   :show-inheritance:
```

Read `docs/dev_guide/api/api.rst` and add both new pages to its `toctree`.

---

### Fix 9 — Fix ruff format claim in dev_guide_conventions.rst (Medium)

**File:** `docs/dev_guide/dev_guide_conventions.rst`

Find the "Python style and typing" section. It currently says:
> "The project does not run `ruff format` as a gate; `ruff check` is the linter."

Verify: run `grep "ruff format" scripts/run-all-checks.sh` to confirm `ruff format
--check` IS run.

Change the sentence to:
```rst
Maximum line length is 100. Code is formatted with ``ruff format`` (single
quotes; see ``[tool.ruff.format]`` in ``pyproject.toml``); both
``ruff format --check`` and ``ruff check`` run as CI gates and in
``scripts/run-all-checks.sh``. Annotate every parameter and return value
(including ``-> None``); ``mypy`` runs in strict mode. Use modern generic
syntax (``list[str]``, ``X | None``). Docstrings are Google style with a
``Parameters:`` section, wrapped at 90 columns.
```

---

### Fix 10 — Fix CONTRIBUTING.md (Medium)

**File:** `CONTRIBUTING.md`

1. Find `cd docs && make html` and replace with:
   ```sh
   scripts/read-docs.sh
   ```
   After the command, add:
   "The `scripts/run-all-checks.sh` script runs all quality gates (lint, type-check,
   tests, docs, and markdown) and is the canonical pre-push check."

2. Find the example commit message (it currently uses a non-Conventional-Commits format
   like `"Add feature: description"`). Replace with:
   ```
   feat: add ring-plane geometry support for GO_0xxx
   ```
   And add a note: "Follow the Conventional Commits specification. See
   `docs/dev_guide/dev_guide_conventions.rst` for this project's commit types and
   50-character subject-line rule."

---

### Fix 11 — Rename README section Licensing → License (Low)

**File:** `README.md`

Find `## Licensing` and change to `## License`.

---

### Fix 12 — Fix py.typed comment in pyproject.toml (Low)

**File:** `pyproject.toml`

Find the comment near the `package-data` section that says `py.typed is intentionally
NOT declared`. Verify that `py.typed` IS listed in `package-data` and that
`src/metadata_tools/py.typed` exists (`ls src/metadata_tools/py.typed`).

Replace the misleading comment with:
```toml
# py.typed ships PEP 561 inline type information to downstream type-checkers
```

---

### After all fixes — verification checklist

1. `sphinx-build -W -n -b html docs /tmp/sphinx-out` — **must pass with zero warnings**.
2. `grep -rn "Args:" src/metadata_tools/` — **must return no results** (all docstrings
   use `Parameters:`).
3. `grep -n "python GO_0xxx_" docs/user_guide/` — **must return no results**.
4. `grep -n "does not install console scripts" docs/user_guide/` — **must return no results**.
5. `grep -n "add_task\|write_task_file\|task_source" docs/` — **must return no results**
   (or only in correct `task_list_support` context).
6. `grep -n "make html" CONTRIBUTING.md` — **must return no results**.
