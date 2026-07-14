# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`rms-metadata-tools` (package `metadata_tools`) generates PDS3 **index**, **geometry**, and
**cumulative** metadata tables — and their PDS3 labels — for planetary science data
collections, a product of the PDS Ring-Moon Systems Node (SETI). Each table row holds
metadata for one data file (e.g. an image). It is published on PyPI and documented on
ReadTheDocs.

There are three table kinds, generated in this order for a collection:

1. **Index** (`*_index.py`) — supplemental index files: extra columns added to a project's
   corrected index file, sourced from PDS labels (or derived via `key__<NAME>` functions).
2. **Geometry** (`*_geometry.py`) — geometric quantities (body/ring/sky/sun) computed from
   SPICE via `oops`, written as summary (and optionally detailed) tables.
3. **Cumulative** (`*_cumulative.py`) — concatenations of the per-volume tables across a
   whole volume tree.

## Common commands

The toolchain assumes a virtualenv at `./venv` (override with `VENV` / `VENV_PATH`).

```sh
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"          # dev tooling (ruff, mypy, pytest, sphinx, ...)
```

Run all quality gates (lint, type-check, tests, sphinx, markdown) — this is the **single
source of truth** for what CI runs; keep the two in sync:

```sh
scripts/run-all-checks.sh                 # everything, parallel
scripts/run-all-checks.sh -s              # sequential (easier to read failures)
scripts/run-all-checks.sh -c              # code checks only
scripts/run-all-checks.sh --pytest        # one check; also --ruff-check --mypy --sphinx ...
scripts/run-all-checks.sh -w 1            # serial pytest workers
```

Individual tools (run from repo root, inside the venv):

```sh
ruff check src tests
ruff format --check src tests
mypy src tests                            # mypy is strict (see pyproject [tool.mypy])
pytest                                    # config in pyproject: pythonpath=src, -n auto, --cov
pytest tests/test_index.py                # single file
pytest tests/test_index.py::Test_Index_Common::test_supplemental_index_common   # single test
scripts/read-docs.sh                      # build docs (warnings = errors) and open in browser
```

**Tests require environment variables** `RMS_METADATA` and `RMS_VOLUMES` (paths to metadata
and volume trees); the top-level `tests/` suite reads them at import time via
`tests/archive_support.py` and will fail to collect without them. Host-specific tests
live under `tests/hosts/<HOST>/` (e.g. `tests/hosts/GO_0xxx/`); like the holdings-backed
top-level tests they carry the `requires_archive` marker and are excluded from the default run.

## Architecture

**Generic engine vs. per-host config.** `src/metadata_tools/` holds host-agnostic machinery;
each supported collection gets a directory under `src/metadata_tools/hosts/<HOST>/` (e.g.
`GO_0xxx/` for Galileo SSI) containing its configuration modules and label templates.

Core engine modules:

- `index_support.py` — `IndexTable` and `process_index()`; builds supplemental index tables.
- `geometry_support.py` — geometry table generation. Contains `FORMAT_DICT`, the master map
  from column name to formatting/units/null/range/link metadata.
- `cumulative_support.py` — walks a volume tree and concatenates per-volume tables.
- `label_support.py` — generates PDS3 `.lbl` labels from templates using `rms-pdstemplate`.
- `columns.py` / `column/COLUMNS_*.py` — geometry column definitions. `columns.py`
  dynamically `exec()`s every `COLUMNS_{BODY,RING,SKY,SUN}.py` to register backplane columns.
- `common.py` — `Table` base class, the global `PdsLogger`, and cloud-task plumbing.
- `util.py`, `defs.py` — utilities and constants (body lists, ring radii, paths).

**Console entry points** (`src/metadata_tools/cli/`) take `HOST_ID` as the first argument and
dispatch to the appropriate engine:

- `metadata-index HOST_ID ...` / `metadata-index-cloud HOST_ID ...`
- `metadata-geometry HOST_ID ...` / `metadata-geometry-cloud HOST_ID ...`
- `metadata-cumulative HOST_ID ...` / `metadata-cumulative-cloud HOST_ID ...`
- `metadata-task-list HOST_ID TREE --output FILE`

Each entry point calls `load_host(host_id)` (strips `HOST_ID` from `sys.argv`, validates the
host directory) and `set_host(host_id)` (registers that host's config modules) before invoking
the engine. Cloud variants also accept `cloud_tasks` options (`--config`, `--task-file`, etc.);
GCP dispatch is paired with `cloud/<HOST>/gcp_*_config.yml` and `cloud/<HOST>/gcp_*_startup.sh`.

**Per-host directory** (`src/metadata_tools/hosts/<HOST>/`) contains config modules and templates:

- `host_config.py`, `index_config.py`, `geometry_config.py` — host-specific settings and
  optional override hooks (e.g. `key__<NAME>(label_path, label_dict)` to compute an index
  column; backplane functions for geometry).
- `host_init.py` — initializes the host's `oops` host module (side-effect import).
- `templates/` — PDS3 label templates (`host_defs.lbl`, `*_supplemental_index.lbl`,
  `*_{body,ring,sky}_summary.lbl`); shared template fragments are in
  `src/metadata_tools/templates/`.

**Config registry:** the generic engine never imports a host's config modules directly (see
issue #112). Entry points call `metadata_tools.config.set_host(host_id)` once, which
eagerly package-qualified-imports `metadata_tools.hosts.<host_id>.{host_config,index_config}`;
`geometry_config` (and the `host_init` side effect it carries — SPICE initialization and
backplane column registration) is imported lazily, on the first `get_geometry_config()` call,
so index and cumulative stages never pay the SPICE startup cost. Engine code reads the active
host via `get_host_config()` / `get_index_config()` / `get_geometry_config()`. This works from
any current working directory — no `sys.path` manipulation is involved. A host's own
`index_config.py`/`geometry_config.py` should cross-reference sibling config modules with a
package-qualified or relative import (e.g. `from metadata_tools.hosts.GO_0xxx import
host_config`), not a bare `import host_config`.

**Adding a new host:** copy an existing `hosts/<HOST>/` directory and edit the config modules
and `templates/`. See the README "Generating New Metadata Tables" section.

**Adding a geometry column:** (1) add a definition to the relevant `column/COLUMNS_*.py`,
(2) add the backplane function, (3) add a `FORMAT_DICT` row in `geometry_support.py`, (4) add
the column description to the host's summary label template, (5) update tests. (See the comment
block at the top of `geometry_support.py`.)

## Conventions (from `.cursor/rules/`)

These `.cursor/rules/*.mdc` files are authoritative coding standards (most are `alwaysApply`).
Read the relevant rule before non-trivial work. Highlights:

- **Paths — `rms-filecache` (`FCPath`):** all file paths go through `FCPath`, which transparently
  handles local and remote (`gs://`, `s3://`, ...) storage. Never downcast `FCPath` to `Path`/`str`
  to "simplify"; normalize inputs with `FCPath(x)` at function boundaries. For libraries needing a
  real local file use `fcpath.retrieve()` / `fcpath.get_local_path()` + `fcpath.upload()`. Prefer
  try/except `FileNotFoundError` over `exists()` pre-checks. Never `mkdir` through `FCPath`
  (including log dirs). See `filecache.mdc`.
- **Logging — `rms-pdslogger`:** use `pdslogger.PdsLogger` (the global one via `common.get_logger()`),
  never the stdlib `logging` module or bare `print()` in library code. Use `with logger.open(header):`
  for sections and `%`-style deferred formatting (`logger.info('to %s', path)`), not f-strings, in
  log calls. See `logging.mdc`.
- **Python style:** max line length 100, `ruff format` with **single quotes**, type-annotate
  everything (mypy strict), Google-style docstrings. See `python.mdc` / `python_testing.mdc`.
- **Tests:** pytest only (new tests should not be `unittest.TestCase`), independent/parallel-safe,
  assert precise values (`pytest.approx` for floats), ≥90% coverage target.
- **Git:** Conventional Commits (`feat:`, `fix:`, `docs:`, ...), 50-char imperative subject. Work on
  `feature/<name>` or `bugfix/<name>` branches; merge to `main` via PR (squash). See `git_workflow.mdc`.
- **Dependencies:** declared in `pyproject.toml`; tool config consolidated there (no `.flake8`,
  `.coveragerc`, etc.). NOTE: `pyproject.toml` runtime `dependencies` are still `"TODO"`; the actual
  runtime requirements currently live in `requirements.txt` / `requirements-cloud.txt`.
