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
`tests/unittester_support.py` and will fail to collect without them. Host-specific tests
live under `tests/hosts/<HOST>/` (e.g. `tests/hosts/GO_0xxx/`); like the holdings-backed
top-level tests they carry the `requires_archive` marker and are excluded from the default run.

## Architecture

**Generic engine vs. per-host config.** `src/metadata_tools/` holds host-agnostic machinery;
each supported collection gets a directory under `src/metadata_tools/hosts/<HOST>/` (e.g.
`GO_0xxx/` for Galileo SSI) containing both its configuration and its runnable entry-point
scripts.

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

**Per-host directory** contains config modules + entry scripts + templates:

- `host_config.py`, `index_config.py`, `geometry_config.py` — host-specific settings and
  optional override hooks (e.g. `key__<NAME>(label_path, label_dict)` to compute an index
  column; backplane functions for geometry).
- `host_init.py` — initializes the host's `oops` host module (side-effect import).
- `<HOST>_{index,geometry,cumulative}.py` — local entry points (argparse CLIs; see each
  file's header comment for arguments and examples).
- `<HOST>_{index,geometry,cumulative}_cloud.py` — same work distributed via `rms-cloud-tasks`
  (GCP); paired with `gcp_*_config.yml` and `gcp_*_startup.sh`.
- `templates/` — PDS3 label templates (`host_defs.lbl`, `*_supplemental_index.lbl`,
  `*_{body,ring,sky}_summary.lbl`); shared template fragments are in
  `src/metadata_tools/templates/`.

**Critical import convention:** host entry scripts and `_cloud.py` workers import their config
as *top-level* modules — `import host_config`, `import index_config`, `import geometry_config`
— not as package-qualified imports. This only resolves when the **current working directory is
the host directory** (so it is on `sys.path`). Run host scripts from inside their `hosts/<HOST>/`
directory. Cloud workers add `sys.path.append('')` so the GCP instance can find `metadata_tools`.

**Adding a new host:** copy an existing `hosts/<HOST>/` directory, rename the scripts, and edit
the config modules and `templates/`. See the README "Generating New Metadata Tables" section.

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
