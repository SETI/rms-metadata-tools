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
source of truth** for what CI runs; keep the two in sync (one deliberate exception:
`pip-audit` queries the PyPI advisory database, so it runs in CI only):

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
mypy src tests                            # mypy is strict (see pyproject [tool.mypy])
pytest                                    # config in pyproject: pythonpath=src, -n auto
pytest --cov=src                          # with coverage and its 90% gate (as the script/CI run it)
pytest tests/test_index.py                # single file
pytest tests/test_index.py::test_supplemental_index_common   # single test
scripts/read-docs.sh                      # build docs (warnings = errors) and open in browser
```

**The default test run needs no environment variables.** Only the archive-backed tier
(`-m requires_archive`) needs `RMS_METADATA` and `RMS_VOLUMES` (paths to the metadata and
volume trees, read in `tests/archive_support.py`); without `RMS_METADATA` those tests skip
with a message. Host-specific tests
live under `tests/hosts/<HOST>/` (e.g. `tests/hosts/GO_0xxx/`); like the holdings-backed
top-level tests they carry the `requires_archive` marker and are excluded from the default run.

## Architecture

**Generic engine vs. per-host config.** `src/metadata_tools/` holds host-agnostic machinery;
each supported collection gets a directory under `src/metadata_tools/hosts/<HOST>/` (e.g.
`GO_0xxx/` for Galileo SSI) containing its configuration modules and label templates.

Core engine modules:

- `index_support/` — `IndexTable` (`table.py`), `process_index()`/`get_args()` (`process.py`),
  and the built-in `key__<NAME>` functions (`key_fns.py`); builds supplemental index tables.
- `geometry_support/` — geometry table generation: `process.py` (entry point), `suite.py`
  (`Suite`), `record.py` (`Record`), `tables.py` (the table classes), `prep.py`, `masks.py`,
  `formatting.py`, `bodies_select.py`, `formats.py` (the host's SCLK-resolved mission
  table), and `label_schema.py`, which reads each table's full column schema — label
  metadata and computation spec alike — from its label template.
- `cumulative_support.py` — walks a volume tree and concatenates per-volume tables.
- `label_support.py` — generates PDS3 `.lbl` labels from templates using `rms-pdstemplate`;
  strips `#` comment lines, expands format references, lowers the column grammar, and strips the spec keywords so they
  never reach a shipped label.
- `column_grammar.py` — the definition/stub column grammar shared by the template read and
  write paths, including format-dictionary expansion and the write-time lowering to plain
  COLUMN objects.
- `config.py` — the host config registry (`set_host()` / `get_*_config()`).
- `task_list_support.py` — task-file generation for cloud/Worker runs.
- `common.py` — `Table` base class, the global `PdsLogger`, and the shared argument parser.
- `util.py`, `defs.py` — utilities and constants (body lists, ring radii, paths).

**Console entry points** (`src/metadata_tools/cli/`) take `HOST_ID` as the first argument and
dispatch to the appropriate engine:

- `metadata-index HOST_ID ...` / `metadata-index-worker ...` / `metadata-index-cloud ...`
- `metadata-geometry HOST_ID ...` / `metadata-geometry-worker ...` / `metadata-geometry-cloud ...`
- `metadata-cumulative HOST_ID ...` / `metadata-cumulative-worker ...` / `metadata-cumulative-cloud ...`
- `metadata-task-list HOST_ID TREE [--output FILE]` (default output `./tasks.json`)

Each entry point calls `load_host(host_id)` (strips `HOST_ID` from `sys.argv`, validates the
host directory) and `set_host(host_id)` (registers that host's config modules) before invoking
the engine. Cloud variants accept `cloud_tasks` options; `--config` defaults to
`cloud/<HOST>/gcp_<type>_config.yml` (source checkout only) and `--task-file` to
`./tasks.json` when those files exist. GCP instance startup scripts are generated at
dispatch time from the packaged template `src/metadata_tools/cli/gcp_common_startup.sh`;
only the `gcp_*_config.yml` machine/queue configs live in `cloud/<HOST>/`.

**Per-host directory** (`src/metadata_tools/hosts/<HOST>/`) contains config modules and templates:

- `host_config.py`, `index_config.py`, `geometry_config.py` — host-specific settings and
  optional override hooks (e.g. `key__<NAME>(label_path, label_dict)` to compute an index
  column; backplane functions for geometry).
- `host_init.py` — initializes the host's `oops` host module (side-effect import).
- `templates/` — PDS3 label templates (`host_defs.lbl`, `*_supplemental_index.lbl`,
  `*_{body,ring,sky,sun}_summary.lbl`); shared template fragments are in
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
and `templates/`. See "Adding a new host" in the developer guide
(`docs/dev_guide/dev_guide_extending.rst`).

**Geometry columns are defined entirely by the label templates**, in the definition/stub
grammar of `column_grammar.py`: each computed column is one `COLUMN_DEFINITION` object —
carrying the shared label metadata (FORMAT hence width/print format, UNIT hence unit
conversion, NULL_CONSTANT, valid range, OVERFLOW_FORMAT) and the computation spec
(`BACKPLANE_KEY` and `MASK` as Python literals parsed with `ast.literal_eval`, the
`'bodyx'` token substituted per body at run time; `LINK_FN`/`LINK_ID` naming a postprocess function and its column group) —
and the shared lead-in DESCRIPTION — followed by one `COLUMN_STUB` object per value,
carrying its NAME, its own per-value DESCRIPTION (appended to the definition's at write
time), and any override; a single-valued column is simply a plain COLUMN carrying its
own spec keywords. Group size is the stub count. Instead of spelling out its format
keywords, any column block may state `COLUMN_FORMAT = "<entry>"`, naming an
`OBJECT = COLUMN_FORMAT` entry in the **format dictionary**
(`src/metadata_tools/templates/column_formats.lbl`, `$INCLUDE`d by each shared fragment);
a keyword the block states itself wins over the entry's, and one-off formats stay inline.
`expand_format_references` substitutes the entries first on both the read and write paths.
`geometry_support/label_schema.py` parses and
validates it all loudly at table construction; the write path lowers every group to plain
COLUMN objects (`merge_column_definitions`), so shipped labels never carry the grammar.

**Adding a geometry column:** the column set is collection-independent and lives in the
shared fragments in `src/metadata_tools/templates/`, which every host's summary template
`$INCLUDE`s. (1) add a COLUMN_DEFINITION plus its COLUMN_STUB object(s) — or a plain
COLUMN for a single value — to the shared fragment for its table kind, referring to a
format-dictionary entry by `COLUMN_FORMAT` when its format is a common one, (2) add the
backplane function if the quantity is new, (3) update tests (column counts are pinned).
Removing a column is likewise a fragment-only edit — the computation travels with the
definition. A host that must differ shadows a fragment with its own copy in its
`templates/` directory. (See "Adding a geometry column" in
`docs/dev_guide/dev_guide_extending.rst`.)

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
- **Python style:** max line length 100, hand-formatted house style (**single quotes**, aligned
  continuation lines, `#===` separators; never run `ruff format`), type-annotate
  everything (mypy strict), Google-style docstrings. See `python.mdc` / `python_testing.mdc`.
- **Tests:** pytest only (new tests should not be `unittest.TestCase`), independent/parallel-safe,
  assert precise values (`pytest.approx` for floats), ≥90% coverage target.
- **Git:** Conventional Commits (`feat:`, `fix:`, `docs:`, ...), 50-char imperative subject. Work on
  `feature/<name>` or `bugfix/<name>` branches; merge to `main` via PR (squash). See `git_workflow.mdc`.
- **Dependencies:** declared in `pyproject.toml`; tool config consolidated there (no `.flake8`,
  `.coveragerc`, etc.). Runtime dependencies are fully declared in `[project].dependencies`;
  `requirements.txt` is `-e .[dev,cloud]` (a dev-environment convenience, not the canonical list).
