# Documentation Critique Report

**Generated:** 2026-07-13
**Scope:** README, docs/ (user guide, developer guide, how-tos), docstrings, Sphinx setup
**Rules applied:** `doc_python.mdc`, `doc_readme.mdc`, `doc_user_guide.mdc`, `doc_dev_guide.mdc`, `doc_how_to.mdc` — all five rule files are present and applied.

---

## Executive summary

The documentation is in excellent overall shape. The Sphinx build passes with zero warnings under both `-W` (warnings-as-errors) and `-n` (nitpicky). The README has all nine required sections with the Sphinx-inclusion marker, the user guide is comprehensive with nine well-structured chapters, and the developer guide covers all required chapters including a class diagram, per-subsystem prose, an extending recipe, and autodoc API reference pages. Public source modules and most functions/classes have Google-style docstrings.

**Main gaps:**

1. **`CONTRIBUTING.md` is materially stale** — references PEP 8 instead of ruff/mypy, gives the wrong docs-build command, omits Conventional Commits, and uses a non-existent example type. (§9, §6)
2. **`dev_guide_layout.rst` documents a cloud layout that no longer exists** — lists `generate_startup_scripts.py`, pre-generated `gcp_*_startup.sh`, and `gcp_*_startup.tail.sh`, none of which are present; startup scripts are now generated at runtime by `_host.py`. (§9, §6)
3. **`_host.py` uses `Args:` not `Parameters:`** in two long docstrings, violating the Google-style rule in `doc_python.mdc`. (§2)
4. **`columns/` package constants are undocumented** and two public functions have only one-line summaries with no `Parameters:`/`Returns:` sections. (§2)

**High-priority fixes:** §9 (stale `CONTRIBUTING.md`), §9 (stale cloud layout in layout docs), §2 (`Args:` → `Parameters:` in `_host.py`).
**Nice-to-have:** `pipx` install note in `user_guide_installation.rst`, docstring completeness in `columns/`, `source_suffix` format in `conf.py`.

---

## 1. Documentation system and build

**Single source tree:** All docs live under `docs/` with a single `conf.py`. Build outputs (`_build/`) are not committed. ✓

**`conf.py` extensions:** Autodoc, viewcode, napoleon, intersphinx, sphinxcontrib.mermaid, and myst_parser are all enabled. The source root is on `sys.path` via `sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))`. The version is injected from `metadata_tools.__version__`. Heavy optional runtime imports (`oops`, `polymath`, `cspyce`, etc.) are mocked via `autodoc_mock_imports`. Host config modules (`host_config`, `index_config`, `geometry_config`) are also mocked for autodoc, which is correct because they are plugin-injected at runtime. ✓

**Build cleanliness:** `sphinx-build -W -n -b html docs <out>` succeeds with **zero warnings**. ✓

**Minor — `source_suffix` format:** `conf.py` assigns `source_suffix = ['.rst', '.md']` (a list), which triggers a "Converting…" informational message in the Sphinx output. This is harmless but should be updated to the current dict form:
```python
source_suffix = {'.rst': 'restructuredtext', '.md': 'restructuredtext'}
```
File: `docs/conf.py`.

**Prose conventions:** Prose in the narrative docs uses American spelling and avoids time-anchored language in guide chapters. One borderline case: `_host.py::resolve_task_file` docstring says "kept for backwards compatibility" — this is framing that anchors the function to a past state. The docs built from this file will render that framing in the API reference. Remove the backward-compatibility note from the docstring; it belongs in a commit message.

---

## 2. Docstrings and API reference

**Coverage — engine modules:** All public modules (`common.py`, `config.py`, `index_support/`, `geometry_support/`, `cumulative_support.py`, `label_support.py`, `task_list_support.py`, `util.py`, `defs.py`, `bodies.py`) have module-level docstrings, and every public function and class has a docstring with `Parameters:`/`Returns:` sections. ✓

**Coverage — CLI modules:** All entry-point modules (`cli/index.py`, `cli/geometry.py`, `cli/cumulative.py`, `cli/index_cloud.py`, `cli/geometry_cloud.py`, `cli/cumulative_cloud.py`, `cli/index_worker.py`, `cli/geometry_worker.py`, `cli/cumulative_worker.py`, `cli/task_list.py`) have module docstrings with usage examples. The `main()` functions have one-liner docstrings. The worker task classes (`_IndexTask`, `_GeometryTask`, `_CumulativeTask`) have one-liner class docstrings. ✓

**Issue — `_host.py` uses `Args:` instead of `Parameters:`:**
Two functions in `src/metadata_tools/cli/_host.py` use `Args:` in their docstrings, violating the Google-style requirement in `doc_python.mdc` (which mandates `Parameters:` not `Args:`):
- `build_startup_script` (line ~130): uses `Args:` header
- `dispatch_cloud_run_if_config` (line ~185): uses `Args:` header

These are the two longest, most detailed docstrings in the CLI package. Fix: rename the `Args:` section heading to `Parameters:` in both.

**Issue — `columns/` package constants are undocumented:**
The four constant dicts/lists in the `columns/` subpackage that define the geometry column catalog are undocumented:
- `columns/body.py`: `BODY_COLUMNS`, `BODY_COLUMN_NAMES`, `BODY_TILE_COLUMNS`, `BODY_TILE_COLUMN_NAMES` — no inline docstrings
- `columns/ring.py`: `RING_COLUMNS`, `RING_COLUMN_NAMES` — no inline docstrings
- `columns/sky.py`: `SKY_COLUMNS`, `SKY_TILES` — `SKY_TILES` has only a `###TODO: not tested...` comment embedded in production code; no docstring
- `columns/sun.py`: `SUN_COLUMNS`, `SUN_COLUMN_NAMES` — no inline docstrings

**Issue — thin docstrings in `columns/body.py`:**
`get_body_summary_dict` and `get_body_detailed_dict` have only one-line summaries with no `Parameters:` or `Returns:` sections. Both take a body-name argument and return a column-definition dict; readers of the API reference have no way to know the return structure or the expected `body` argument format without reading the source.

**Issue — `###TODO: not tested...` comment in `columns/sky.py`:**
The `SKY_TILES` constant has an embedded `###TODO` comment in production code. This should be converted to a GitHub issue and removed from the source.

**`FORMAT_DICT` / `ALT_FORMAT_DICT` in `geometry_support/formats.py`:**
These module-level dicts use trailing string literals after their definitions as informal "docstrings". While this renders as regular text in the API reference, they are not callable-level docstrings recognized by autodoc. The module docstring is present and adequate; the trailing literals are a non-standard pattern but do not break the build. (Low priority.)

**API-reference coverage:** The `docs/dev_guide/api/` directory contains one page per top-level package/subpackage, each using `automodule` with `:members:`, `:undoc-members:`, and `:show-inheritance:`. The `cli/` package is excluded from autodoc (it is also excluded from coverage), which is acceptable because it is documented in the user guide. The `hosts/` subpackage is also excluded. ✓

---

## 3. Cross-reference completeness

**Build under nitpicky mode:** `sphinx-build -n` passes with zero unresolved cross-references. ✓

**`nitpick_ignore_regex` entries:** `docs/conf.py` suppresses a list of unresolvable symbols from third-party packages (`oops.*`, `polymath.*`, `pdslogger.*`, etc.). All entries are documented with inline comments explaining that these are third-party symbols with no stubs. The project owns none of these symbols, so the ignores are appropriate. ✓

**Cross-reference style in narrative prose:** The developer-guide and user-guide chapters use `:class:`, `:func:`, `:meth:`, `:mod:`, `:data:`, and `:doc:` roles consistently in the sections reviewed. No bare `ClassName` or `module.symbol` text was found in cross-reference positions. ✓

---

## 4. README

**Format and inclusion:** `README.md` is Markdown with a `<!-- start-after-point -->` marker at line 27 so that the badge block is excluded from the Sphinx-rendered version. There is a single top-level title. ✓

**Required sections (in order):**
1. Title ✓
2. Grouped status badges (release, test, docs, coverage, PyPI, commits, issues, PRs, license, DOI) ✓
3. Introduction ✓
4. Features ✓
5. Installation (Python versions, prerequisites, install command) ✓
6. Quick start ✓
7. Documentation link + local build ✓
8. Contributing link ✓
9. License ✓

All nine required sections are present in order. ✓

**Content quality:** The quickstart examples reference `$RMS_VOLUMES` and `$RMS_METADATA` environment variables, which are defined in the user guide. The README points to the user guide for details. Badge claims match the `pyproject.toml` metadata. ✓

---

## 5. User guide

**Layout:** Lives under `docs/user_guide/` with a landing page (`user_guide.rst`) and nine chapter files using the `user_guide_` prefix. ✓

**Required content coverage:**
- Introduction and workflow overview: `user_guide_overview.rst` ✓
- Installation (Python versions, install commands, prerequisites, env vars, directory layout): `user_guide_installation.rst` ✓
- Index stage: `user_guide_index.rst` ✓
- Geometry stage: `user_guide_geometry.rst` ✓
- Cumulative stage: `user_guide_cumulative.rst` ✓
- Cloud and worker scripts: `user_guide_cloud.rst` ✓
- Configuration: `user_guide_configuration.rst` ✓
- Examples: `user_guide_examples.rst` ✓
- Host appendix: `user_guide_appendix_hosts.rst` ✓

**Issue — no `pipx` install instruction:** `user_guide_installation.rst` documents `pip install rms-metadata-tools` but does not mention `pipx`. The `doc_user_guide.mdc` rule requires the guide to show `pipx` for packages that install command-line programs system-wide. Since `rms-metadata-tools` installs ten console scripts, a `pipx` install note is appropriate.

**Command-line program documentation (`user_guide_cloud.rst`):** The cloud page documents all worker options (`--task-file`, `--num-simultaneous-tasks`) and all cloud-only overrides (`--create-startup-file`, `--startup-template`, `--oops-resources`, `--service-account`, `--debug-branch`) with descriptions. The task-list script is documented in detail with both scan and explicit modes and the JSON schema. ✓

**API usage section:** The package exposes an importable surface (`metadata_tools`), but the user guide does not include an "API usage" section. This is a mild gap per `doc_user_guide.mdc`, though the package is primarily a CLI tool and users are unlikely to call the engine directly.

---

## 6. Developer guide

**Layout:** Lives under `docs/dev_guide/` with a landing page and API reference under `docs/dev_guide/api/`. All chapters use the `dev_guide_` prefix. ✓

**Required chapters present:**
- Introduction: `dev_guide_introduction.rst` ✓
- Repository layout: `dev_guide_layout.rst` ✓
- Environment setup: `dev_guide_environment.rst` ✓
- Architecture/class hierarchy: `dev_guide_architecture.rst` with Mermaid `classDiagram` ✓
- Per-subsystem chapters: index, geometry, cumulative, support subsystems ✓
- Extending: `dev_guide_extending.rst` ✓
- Conventions: `dev_guide_conventions.rst` ✓
- API reference: `dev_guide/api/` with one page per subpackage ✓

**Architecture diagram:** `dev_guide_architecture.rst` contains a Mermaid `classDiagram` showing the `Table` hierarchy and key relationships. The diagram is followed by narrative prose. Cross-references inside the diagram block are absent (correct per rule). ✓

**Issue — `dev_guide_layout.rst` documents a stale cloud layout:**
`dev_guide_layout.rst` describes the `cloud/` directory as containing:
```
cloud/generate_startup_scripts.py     # regenerates gcp_*_startup.sh from tail fragments
cloud/GO_0xxx/
  gcp_*_startup.sh                   # GCP instance start-up scripts (generated)
  gcp_*_startup.tail.sh              # host-specific command fragments (edit these)
```

None of these files exist. The actual `cloud/GO_0xxx/` directory contains only `gcp_*_config.yml` files and `tasks.json`. GCP startup scripts are now generated at runtime by `_host.py::build_startup_script`, not stored in the repo. The layout chapter needs to be updated to reflect the current cloud layout and to document the runtime generation approach.

**`CONTRIBUTING.md` stale content (impacts developer guide cohesion):**
`CONTRIBUTING.md` is referenced from both the root README and the developer guide. It contains several outdated items:
1. References "PEP 8" compliance instead of the project's actual tools (ruff check, ruff format, mypy).
2. Documents `cd docs && make html` as the docs-build command instead of `scripts/read-docs.sh`.
3. Does not mention Conventional Commits (the `feat:`, `fix:`, `docs:`, … prefixes required by `git_workflow.mdc`).
4. A code example uses `NDArrayFloatType`, which is not a type defined anywhere in this project. The example should use an actual project type.

---

## 7. How-to articles

No dedicated how-to articles exist in the `docs/` tree. The `user_guide_examples.rst` chapter serves an examples purpose but is written as a guide chapter rather than as a structured how-to article per `doc_how_to.mdc` (action-oriented title, numbered steps with observed results, prerequisites, troubleshooting, related material).

For the task-oriented workflows that users are likely to perform — for example, "Add a geometry column", "Run geometry generation on GCP", "Add a new host" — converting or supplementing the relevant chapters with how-to articles following the `doc_how_to.mdc` structure would significantly improve discoverability and usability. The extending chapter (`dev_guide_extending.rst`) already contains a recipe structure that is close to the how-to format.

This is a gap but is a lower priority than the stale-content issues above.

---

## 8. Diagrams and figures

**Architecture diagram:** The Mermaid `classDiagram` in `dev_guide_architecture.rst` renders cleanly in the Sphinx build (sphinxcontrib.mermaid is enabled in `conf.py`). ✓

**No figure `alt` text noted as missing:** Mermaid diagrams do not use image `alt` text in the same way as inline images; the surrounding narrative prose provides context. The one class diagram is immediately followed by prose that walks the class hierarchy. ✓

**No other figures or images were found** in the docs tree — the documentation is prose-and-diagram-only. This is appropriate given the nature of the package.

---

## 9. Change discipline and consistency

**`CONTRIBUTING.md` vs. current toolchain (already detailed in §6):** The contributing guide is materially inconsistent with the current development toolchain. It should be updated to match `scripts/run-all-checks.sh`, ruff, mypy, and Conventional Commits.

**`dev_guide_layout.rst` vs. actual `cloud/` layout (already detailed in §6):** The annotated cloud directory tree describes a pre-generation workflow that no longer exists. The layout chapter and any cross-references to startup-script files need to be replaced with prose describing the runtime-generation model in `_host.py`.

**`_version.py` comment claims py.typed is NOT declared; `pyproject.toml` ships it:**
`pyproject.toml` line 82-84 comment: "py.typed is intentionally NOT declared: the package is not yet fully annotated, so advertising it as typed would mislead downstream type checkers." Yet line 85 includes `py.typed` in `[tool.setuptools.package-data]`. If the `py.typed` marker file does not exist in the source tree, this is harmless (setuptools skips missing files). If it does exist, it is shipped and the comment is factually wrong. The comment should be corrected to match the actual intent and state of the marker file. (Note: this is in `pyproject.toml`, not in the `docs/` tree, but it produces incorrect information in the developer guide if the layout chapter describes the package structure.)

**`util.py` `### move to utilities` comments:** Multiple `### move to utilities` inline comments throughout `util.py` indicate acknowledged technical debt. These are code comments, not documentation, but they represent stale intent that should be either executed (move the code) or removed (accept the current location). They do not directly affect the documentation build.

**Console scripts count consistency:** `user_guide_installation.rst` and the developer guide both refer to "ten console scripts", which matches `pyproject.toml` `[project.scripts]`. ✓

---

## Recommended priorities

1. **Fix `CONTRIBUTING.md`** — update PEP 8 reference to ruff/mypy, replace the docs build command with `scripts/read-docs.sh`, add Conventional Commits guidance, replace the non-existent `NDArrayFloatType` example with an actual project type. This is the highest-impact fix because CONTRIBUTING.md is the first document a new contributor reads.
2. **Update `dev_guide_layout.rst` cloud layout** — remove the stale `generate_startup_scripts.py`, `gcp_*_startup.sh`, and `gcp_*_startup.tail.sh` entries; replace with a description of the runtime-generation model (`_host.py::build_startup_script`). Add the actual `cloud/GO_0xxx/gcp_*_config.yml` files and `tasks.json` to the layout.
3. **Fix `Args:` → `Parameters:` in `_host.py`** — rename the `Args:` section header to `Parameters:` in `build_startup_script` and `dispatch_cloud_run_if_config` to conform to the Google-style docstring requirement in `doc_python.mdc`.
4. **Add docstrings/improve thin docstrings in `columns/` package** — add `Parameters:`/`Returns:` to `get_body_summary_dict` and `get_body_detailed_dict`; add inline docstrings (as trailing `"""…"""` string literals after assignment, per the convention used in `defs.py`) to `BODY_COLUMNS`, `RING_COLUMNS`, `SKY_COLUMNS`, `SUN_COLUMNS`, and related constants; convert the `###TODO: not tested...` comment on `SKY_TILES` to a GitHub issue.
5. **Add `pipx` install note** to `user_guide_installation.rst`.
6. **Fix `source_suffix`** in `docs/conf.py` from list form to dict form to remove the implicit deprecation conversion.
7. **Remove backward-compatibility framing** from `_host.py::resolve_task_file` docstring.

---

## Prompt for an AI agent to fix the documentation

```
You are a documentation engineer tasked with updating the documentation for the
`rms-metadata-tools` Python package (package `metadata_tools`). Your job is to
fix the issues identified in the documentation critique without changing any
production code behavior. Read the `.cursor/rules/doc_*.mdc` files before making
changes; they are the authoritative documentation standards.

Work from the repo root `/home/spitale/rms-/rms-metadata-tools/`.

**BUILD GATE:** The docs must build clean under BOTH of the following commands
before the work is considered done:
  source venv/bin/activate
  sphinx-build -W -n -b html docs /tmp/sphinx-out
(Both -W and -n must be passed together in the same build.)

**Do not change any production code** in `src/metadata_tools/` except for
docstrings in Python source files. Do not change tests. Do not change `pyproject.toml`
or `setup.py`. Do not change `.cursor/rules/` files.

When you rename or move any cross-referenced symbol or page, update every
reference to it in the same change (including toctrees, :doc:, :class:,
:func:, :meth:, :mod:, :attr:, :data:, and :ref: roles).

---

Fix the following issues in order of priority:

### Fix 1: Update CONTRIBUTING.md

File: `CONTRIBUTING.md`

The file is stale in these specific ways:
1. It references "PEP 8" compliance. Replace with the actual tools: ruff (for
   linting and formatting) and mypy (for type checking). The command to run all
   checks is `scripts/run-all-checks.sh`; individual tools are:
     ruff check src tests
     ruff format --check src tests
     mypy src tests
2. It documents `cd docs && make html` as the docs-build command. Replace with
   `scripts/read-docs.sh` (which builds with SPHINXOPTS=-W and opens the result).
3. It does not mention Conventional Commits. Add a section or note explaining
   that commit messages must use the Conventional Commits format:
   `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`, etc.
   The subject line must be 50 characters or fewer, imperative mood.
4. A code example uses the type `NDArrayFloatType` which does not exist in this
   project. Replace it with a type that is actually used in the codebase (for
   example `np.ndarray` or a type from `metadata_tools`).

---

### Fix 2: Update dev_guide_layout.rst cloud section

File: `docs/dev_guide/dev_guide_layout.rst`

The `cloud/` directory annotated tree describes a pre-generation workflow that
no longer exists. Specifically, these items are listed but do NOT exist in the
repository:
  cloud/generate_startup_scripts.py
  cloud/GO_0xxx/gcp_*_startup.sh
  cloud/GO_0xxx/gcp_*_startup.tail.sh

The ACTUAL current cloud/ directory layout is:
  cloud/
    gcp_common_startup.sh     # shared VM bootstrap template
    GO_0xxx/
      gcp_index_config.yml    # GCP machine/queue config for index stage
      gcp_geometry_config.yml # GCP machine/queue config for geometry stage
      gcp_cumulative_config.yml # GCP machine/queue config for cumulative stage
      tasks.json              # example/output task file

GCP startup scripts are now generated at runtime by
`metadata_tools.cli._host.build_startup_script` (called by the `*-cloud`
entry points and `--create-startup-file`). They are never stored in the repo.

Update the annotated directory tree in the cloud section to show the actual
files. Add a sentence explaining that startup scripts are generated at runtime
by the `*-cloud` console scripts and delivered to `cloud_tasks`; they can be
previewed with `--create-startup-file`.

---

### Fix 3: Fix Args: → Parameters: in _host.py docstrings

File: `src/metadata_tools/cli/_host.py`

The Google-style docstring standard (doc_python.mdc) requires `Parameters:`
not `Args:`. Two functions in this file use the wrong section header:

1. `build_startup_script` — change `Args:` to `Parameters:`
2. `dispatch_cloud_run_if_config` — change `Args:` to `Parameters:`

Do not change any other content in those docstrings. Only rename the section
header from `Args:` to `Parameters:`.

---

### Fix 4: Improve columns/ package docstrings

Files:
- `src/metadata_tools/columns/body.py`
- `src/metadata_tools/columns/ring.py`
- `src/metadata_tools/columns/sky.py`
- `src/metadata_tools/columns/sun.py`

4a. Add `Parameters:` and `Returns:` sections to `get_body_summary_dict` and
`get_body_detailed_dict` in `body.py`. Both functions take a `body` argument
(a string body name, e.g. "JUPITER") and return a dict mapping column name to
column definition. Document the argument type, the allowed values or format,
and the return type.

4b. Add inline docstrings (as trailing `"""..."""` string literals after the
assignment, following the same pattern used in `src/metadata_tools/defs.py`)
to these module-level constants:
- `BODY_COLUMNS` and `BODY_COLUMN_NAMES` in `body.py`
- `BODY_TILE_COLUMNS` and `BODY_TILE_COLUMN_NAMES` in `body.py`
- `RING_COLUMNS` and `RING_COLUMN_NAMES` in `ring.py`
- `SKY_COLUMNS` in `sky.py`
- `SKY_TILES` in `sky.py` (replace the ###TODO comment entirely; file a
  GitHub issue for the untested code if needed, then remove the comment)
- `SUN_COLUMNS` and `SUN_COLUMN_NAMES` in `sun.py`

Each docstring should be a single sentence describing what the constant
contains and how it is used.

---

### Fix 5: Add pipx install note to user_guide_installation.rst

File: `docs/user_guide/user_guide_installation.rst`

In the "Installation" section, after the `pip install rms-metadata-tools` code
block, add a note that `pipx` can be used to install the ten console scripts in
an isolated environment while making them available system-wide:

  pipx install rms-metadata-tools

Follow the existing code-block format in the file.

---

### Fix 6: Fix source_suffix in docs/conf.py

File: `docs/conf.py`

Change:
  source_suffix = ['.rst', '.md']
To:
  source_suffix = {'.rst': 'restructuredtext', '.md': 'restructuredtext'}

This removes the implicit deprecation conversion Sphinx performs on list-form
source_suffix values.

---

### Fix 7: Remove backward-compatibility framing from _host.py::resolve_task_file

File: `src/metadata_tools/cli/_host.py`

The `resolve_task_file` function's docstring ends with:
  "Alias for :func:`resolve_host_paths`; kept for backwards compatibility."

Remove the "kept for backwards compatibility" clause. The docstring should
simply say it is an alias for `resolve_host_paths`. The historical reason
belongs in git history, not the API reference.

---

After completing all fixes, run the build gate command:
  source venv/bin/activate && sphinx-build -W -n -b html docs /tmp/sphinx-out

The build must succeed with zero warnings. If it fails, resolve all warnings
before considering the work done.
```
