# Documentation Critique Report

**Generated:** 2026-06-15
**Scope:** `README.md`, `CONTRIBUTING.md`, `docs/` (`index.rst`, `module.rst`, `contributing.rst`, `code_of_conduct.md`, `conf.py`, `Makefile`, `make.bat`), in-source docstrings, the `AAREADME.txt` archive doc, and Sphinx setup.
**Rules applied:** `doc_python.mdc`, `doc_readme.mdc`, `doc_user_guide.mdc`, `doc_dev_guide.mdc`, `doc_how_to.mdc` (all present, so all areas critiqued). The build could not be executed here (no Python on PATH); build findings below are determined statically and should be confirmed by running the build.

## Executive summary

The documentation is **skeletal and will not build clean under `-W`**. There is no user guide, no developer guide, and no how-to articles — only a README (with `TODO` placeholders), a near-empty API stub (`module.rst` autodocs only the top-level package docstring), and two include-only pages that are not in any `toctree`. Several issues will hard-fail `sphinx-build -W`:

- **Broken include of a deleted file:** `docs/code_of_conduct.md` and `CONTRIBUTING.md` reference `CODE_OF_CONDUCT.md`, which has been **deleted** from the repo (`git status` shows `D CODE_OF_CONDUCT.md`). The `{include} ../CODE_OF_CONDUCT.md` will fail.
- **Orphan pages:** `contributing.rst` and `code_of_conduct.md` are in no `toctree` (only `module` is) → "document isn't included in any toctree" warnings.
- **Short title underlines** in `index.rst` → docutils "Title underline too short" warnings.
- **Empty API reference:** `module.rst` does not recurse into submodules, so none of the public modules (`util`, `index_support`, `geometry_support`, …) appear in the generated reference.
- **Content placeholders:** README "Features" says "is TODO"; `pyproject` `description`/`keywords` are `TODO`.

Because the package also cannot be installed (`dependencies = ["TODO"]`, see `code_critique.md` §8/§10), ReadTheDocs' `pip install . [docs]` step will itself fail. **Build health: red.**

High-priority: restore/repoint the Code of Conduct include, put every page in a `toctree`, make the API reference recurse, and fix the README placeholders — then make `-W` (and ideally `-n`) pass.

## 1. Documentation system and build (`doc_python`)

- **Finding (Critical):** Build fails on a missing include. `docs/code_of_conduct.md` does `{include} ../CODE_OF_CONDUCT.md`, and `contributing.rst` slices `CONTRIBUTING.md` around a `CODE_OF_CONDUCT.md` reference, but `CODE_OF_CONDUCT.md` was deleted. **Evidence:** `docs/code_of_conduct.md:3-6`, `contributing.rst:6-15`, `git status: D CODE_OF_CONDUCT.md`. **Fix:** Either restore `CODE_OF_CONDUCT.md` at repo root or remove the Code-of-Conduct page and the `contributing.rst` split that depends on it (and the `## Code of Conduct` section in `CONTRIBUTING.md`).
- **Finding (High):** Orphan documents. `index.rst:10-14` `toctree` contains only `module`; `contributing` and `code_of_conduct` are never referenced, producing "not included in any toctree" warnings (fatal under `-W`). **Fix:** Add `contributing` and `code_of_conduct` (and future guide pages) to the `toctree`.
- **Finding (High):** Title-underline warnings. `index.rst` underlines (`====...`) are shorter than their title text on lines 3-4 and 16-17. **Fix:** Extend underlines to at least the title length.
- **Finding (High):** No `autodoc_mock_imports`. The library modules import heavy/uninstallable deps (`oops`, `cspyce`, `julian`, …) and, worse, import **top-level host modules** (`import host_config`, `import index_config`, `import geometry_config`) that are not importable from the package root. If `module.rst` is ever made to autodoc submodules, autodoc will raise `ImportError`. **Evidence:** `conf.py` (no `autodoc_mock_imports`), `index_support.py:15-16`, `geometry_support.py:20`. **Fix:** Add `autodoc_mock_imports = ["oops","cspyce","julian","polymath","vicar","fortranformat","cloud_tasks","pdstable","pdsparser","pdstemplate","pdslogger","filecache","host_config","index_config","geometry_config"]` (or restructure host imports) before recursing the API ref.
- **Finding (Medium):** Build is not nitpicky. `doc_python` requires clean under both `-W` and `-n`; CI runs only `sphinx-build -W` (`run-tests.yml`) and `run-all-checks.sh` uses `make html SPHINXOPTS="-W"`. **Fix:** Add `-n` to the doc build (and `nitpick_ignore` only for genuinely external symbols).
- **Finding (Low):** `suppress_warnings = ['myst.header']` (`conf.py:52`) hides heading-level warnings from the CONTRIBUTING split; once the split is simplified this suppression should be removed so real heading issues surface.

## 2. Docstrings and API reference (`doc_python`, `doc_dev_guide`)

- **Finding (High):** The API reference is effectively empty. `module.rst` only does `.. automodule:: metadata_tools` with `:members:`; since `__init__.py` exposes only `__version__`, the reference renders just the package docstring. None of `util`, `common`, `defs`, `columns`, `label_support`, `index_support`, `geometry_support`, `cumulative_support` appear. **Evidence:** `module.rst`, `__init__.py:86-89`. **Fix:** Add per-module `automodule` directives (or `:recursive:` autosummary) for every public module, with `:members: :undoc-members: :show-inheritance:`.
- **Finding (High):** Docstring format is `Args:`, but `doc_python` mandates Google style with **`Parameters:`**. Every docstring in the codebase uses `Args:`. **Evidence:** e.g. `index_support.py:30`, `util.py:22`, `common.py:26`. **Fix:** Convert `Args:`→`Parameters:` (Napoleon supports it; keep `Returns:`/`Raises:`).
- **Finding (High):** Many docstrings are wrong/copy-pasted (will mislead generated docs). **Evidence:** `index_support.py:108-115` ("existing geometry tables" inside the *index* `create`); `common.py:122-123` ("Name of volume_tree arg" repeated for metadata/output; "bostrl"); `geometry_config.py:159-168` (`meshgrid` doc lists args in wrong order, says "Returns: None" but returns a meshgrid); `host_config.py`/`geometry_config.py` `get_volume_id` say "Returns: None" but return a str; `index_config.py:199-208, 230-239` describe the wrong field. **Fix:** Rewrite each to match actual behavior so a black-box test could be written from it (`doc_python`).
- **Finding (Medium):** Missing class docstrings. The geometry table classes have their docstring placed *before* the `class` statement (a no-op), so `InventoryTable`/`SkyTable`/`SunTable`/`RingTable`/`BodyTable` have none. **Evidence:** `geometry_support.py:1066-1067, 1101-1102, …` (also raised in `code_critique.md` §6). **Fix:** Move the string inside the class body.
- **Finding (Low):** `:special-members:` plus broad `:exclude-members:` in `module.rst` is fragile; prefer documenting only the intended public surface.

## 3. Cross-reference completeness (`doc_python`)

- **Finding (Medium):** Narrative prose references code objects as plain text/inline literals rather than Sphinx roles. **Evidence:** README and `__init__.py` docstring mention `from_index()`, `key__<NAME>()`, `index_config.py`, `body_summary.lbl`, `host_config.py` without `:func:`/`:meth:`/`:mod:` roles. **Fix:** Once the API ref exists, use roles (`:func:`, `:meth:`, `:mod:`) so references resolve and link; verify under `-n`.
- **Finding (Low):** No stale `:doc:`/`:ref:` targets today (few cross-refs exist), but `contributing.rst`'s `:doc:` to `code_of_conduct` will break with the deleted CoC (§1).

## 4. README (`doc_readme`)

- **Finding (High):** Placeholder content. `README.md:33` "`rms-metadata-tools` is TODO"; the install section's pip block is commented out; there is no real quickstart with runnable commands. **Evidence:** `README.md:31-33, 64-81`. **Fix:** Write the Features section; provide a runnable quickstart (the three-stage `*_index.py`→`*_geometry.py`→`*_cumulative.py` workflow with example paths and required `RMS_*` env vars).
- **Finding (Medium):** Metadata claims don't match packaging. The README badges/links advertise PyPI, but `pyproject` `description`/`keywords`/`dependencies` are `TODO` and the package cannot install (`code_critique.md` §8). **Fix:** Reconcile the README with real packaging metadata before publishing.
- **Finding (Medium):** The README documents the **directory/host-extension procedure** (good) but omits the required environment variables (`RMS_METADATA`, `RMS_VOLUMES`, the `gs://` trees used in the GCP scripts) and the supported Python versions in the install section. **Fix:** Add a prerequisites subsection (Python ≥ the agreed minimum, env vars, expected input/output tree layout).
- **Finding (Low):** `doc_readme` expects an inclusion marker so host-only badges are excluded from rendered docs; the marker exists (`<!-- start-after-point -->`, used by `index.rst`). Good — keep it.

## 5. User guide (`doc_user_guide`)

- **Finding (High):** **There is no user guide.** `doc_user_guide` expects a `user_guide/` subdirectory with a landing page + `toctree`, a workflow overview, installation/setup (versions, env vars, input/output layout), the full configuration model, and a **per-command-line-program reference**. None exists. **Evidence:** `docs/` contains only `index.rst`, `module.rst`, `contributing.rst`, `code_of_conduct.md`. **Fix:** Create `docs/user_guide/` covering: the index→geometry→cumulative pipeline; setup and `RMS_*` env vars; and a reference for each host CLI (`GO_0xxx_index.py`, `_geometry.py`, `_cumulative.py` and the `_cloud.py` variants) documenting every argument. The argument help already lives in the script header comments and `com.get_common_args`/`get_args` — lift it into the guide and keep it in sync with the parsers.
- **Finding (Medium):** The argument documentation that does exist (script header comments, e.g. `GO_0xxx_geometry.py:1-43`) is not rendered anywhere in the docs and can drift from the actual `argparse` definitions. **Fix:** Document options from the parsers (`common.py:113-160`, `index_support.get_args`, `geometry_support.get_args`, `cumulative_support.get_args`) including defaults and the structured `*_tasks.json` schema the cloud workers consume.

## 6. Developer guide (`doc_dev_guide`)

- **Finding (High):** **There is no developer guide.** `doc_dev_guide` expects a subdirectory with: repo-layout overview, environment setup (editable install, env vars, running entry points + smoke test, running tests with tiers/parallel/single-test, lint/type/format/docs commands and the `run-all-checks.sh` wrapper, CI/CD, release), an architecture/class diagram, per-subsystem chapters, and an "extending" recipe. None exists. **Evidence:** `docs/`. **Fix:** Create `docs/dev_guide/` with at least: an annotated layout; a class diagram for `Table`→`IndexTable`/`InventoryTable`/`SkyTable`/`SunTable`/`RingTable`/`BodyTable` and `Record`/`Suite`; the `column/` + `FORMAT_DICT` + label-template relationship; and a "How to add a new host" recipe (the README's host steps are a good seed). Document the critical CWD/`host_config` import convention.
- **Finding (Medium):** No class diagrams anywhere though `sphinxcontrib.mermaid` is enabled (`conf.py:38, 103`). **Fix:** Add at least one Mermaid class diagram in the dev guide.

## 7. How-to articles (`doc_how_to`)

- **Finding (Medium):** **No how-to articles exist.** `doc_how_to` expects task-focused articles (title, intro, prerequisites, numbered steps with commands and observed results, troubleshooting, links). **Evidence:** `docs/`. **Fix:** Add at least: "Generate a supplemental index for one volume," "Generate geometry tables," and "Run the pipeline on GCP with cloud_tasks" (the `*_cloud.py` headers and `gcp_*` files provide the raw material). Keep them consistent with the user guide and cross-link.

## 8. Diagrams and figures (`doc_how_to`, `doc_dev_guide`)

- **Finding (Medium):** No diagrams, despite the pipeline and class hierarchy being prime candidates and Mermaid being configured. **Fix:** Add a pipeline flow diagram (index→geometry→cumulative) and the class diagram from §6; verify they render in the build.

## 9. Change discipline and consistency (`doc_python`)

- **Finding (High):** Docs/metadata disagree with the code and with each other. README/PyPI claims vs. `TODO` packaging metadata; CoC page/`CONTRIBUTING.md` reference a deleted file; the README "Modifying table columns" steps reference `body_summary.lbl` while the actual templates are `body_summary_columns.lbl`/`GO_0xxx_body_summary.lbl`. **Evidence:** `README.md:126-129`, `src/metadata_tools/templates/`, `git status`. **Fix:** Audit every doc reference against current filenames and packaging; update README, CONTRIBUTING, and `docs/` in the same change.
- **Finding (Medium):** `CONTRIBUTING.md` contains a generic example function (`calculate_offset`) and a "Code of Conduct" section unrelated to this package; its testing/build instructions don't mention the `RMS_*` env vars or `scripts/run-all-checks.sh` as the canonical gate. **Fix:** Tailor CONTRIBUTING to this repo (point at `run-all-checks.sh`, env vars, the host-extension workflow) and remove the dead CoC reference.
- **Finding (Low):** Minor content errors in shipped templates that surface in generated labels, e.g. `GO_0xxx_supplemental_index.lbl` VOLUME_ID description "provides a unique for a PDS data volume" (missing word). **Fix:** Correct template prose.

## Recommended priorities

1. **Make the build pass under `-W`:** restore or remove the Code-of-Conduct include, add `contributing`/`code_of_conduct` (and new guides) to a `toctree`, fix the `index.rst` underlines, and add `autodoc_mock_imports`. (Also unblock ReadTheDocs by fixing `pyproject` `dependencies` — see `code_critique.md`.)
2. **Make the API reference real:** recurse `automodule` over all public modules, convert `Args:`→`Parameters:`, fix the misplaced class docstrings, and correct the copy-pasted/incorrect docstrings.
3. **Write the missing guides:** README features/quickstart, a user guide with per-CLI option references, a developer guide with a class diagram and the "add a host" recipe, and 2–3 how-to articles.

---

## Prompt for an AI agent to fix the documentation

> You are fixing the documentation of `rms-metadata-tools` (Sphinx docs under `docs/`, package `metadata_tools` under `src/`; rules in `.cursor/rules/doc_*.mdc`). **Do not change production code behavior.** When you rename or move a page or symbol, update every cross-reference, the README, and the guides in the same change. **Build gate:** the docs must build clean under BOTH `sphinx-build -W -b html docs docs/_build` and `sphinx-build -n -b html docs docs/_build` before you are done. (Note: `pip install .` currently fails because `pyproject.toml` has `dependencies = ["TODO"]`; if you cannot install the package, add `autodoc_mock_imports` and/or coordinate the packaging fix from `critiques/code_critique.md` so the build can run.)
>
> Tasks:
> 1. **Unbreak the build.** Decide with the maintainer whether to keep a Code of Conduct. If yes, restore `CODE_OF_CONDUCT.md` at repo root; if no, delete `docs/code_of_conduct.md`, remove the CoC `:doc:` reference and the second `include` slice in `docs/contributing.rst`, and drop the `## Code of Conduct` section from `CONTRIBUTING.md`. Add `contributing` and `code_of_conduct` (if kept) plus all new guide landing pages to the `toctree` in `docs/index.rst`. Lengthen the two short title underlines in `docs/index.rst`.
> 2. **Sphinx config (`docs/conf.py`).** Add `autodoc_mock_imports` for the heavy/uninstallable and host-level imports: `oops, cspyce, julian, polymath, vicar, fortranformat, cloud_tasks, pdstable, pdsparser, pdstemplate, pdslogger, filecache, host_config, index_config, geometry_config`. Add `-n` (nitpicky) to the documented build commands (and to `scripts/run-all-checks.sh` / `run-tests.yml`), adding `nitpick_ignore` only for genuinely external symbols. Remove `suppress_warnings = ['myst.header']` once the CONTRIBUTING split is simplified.
> 3. **API reference (`docs/module.rst`).** Replace the single top-level `automodule` with per-module `automodule` directives (or an autosummary with `:recursive:`) for `metadata_tools` and every public submodule (`util`, `common`, `defs`, `columns`, `label_support`, `index_support`, `geometry_support`, `cumulative_support`), each with `:members: :undoc-members: :show-inheritance:`.
> 4. **Docstrings (source).** Convert all `Args:` sections to `Parameters:` (Google/Napoleon). Fix the incorrect/copy-pasted docstrings called out in this report (`index_support.py` `create`; `common.py` `get_common_args`; `geometry_config.py` `meshgrid`; `get_volume_id` "Returns: None"; `index_config.py` `key__on_chip_mosaic_flag`/`key__compression_quantization_table_id`). Move the misplaced class docstrings in `geometry_support.py` inside their class bodies. (Docstring text only — no behavior change.)
> 5. **README & CONTRIBUTING.** Replace the `TODO` Features text with a real description; add a runnable Quickstart (index→geometry→cumulative with example paths and the required `RMS_METADATA`/`RMS_VOLUMES` env vars and supported Python versions); fix the "Modifying table columns" filenames to match the actual templates (`*_summary_columns.lbl` / `GO_0xxx_*_summary.lbl`). Tailor CONTRIBUTING to this repo: point to `scripts/run-all-checks.sh` as the gate, list the env vars, and reference the host-extension workflow.
> 6. **New guides (create under `docs/`).** `user_guide/` (landing + toctree): workflow overview, setup/env vars/input-output layout, configuration model, and a per-CLI reference for `GO_0xxx_index.py`, `_geometry.py`, `_cumulative.py`, and the `_cloud.py` variants documenting every argument (source the options from `common.get_common_args` and each module's `get_args`, plus the `*_tasks.json` schema). `dev_guide/` (landing + toctree): annotated layout, a Mermaid class diagram for `Table`/`Record`/`Suite` and the table subclasses, the `column/`+`FORMAT_DICT`+label-template relationship, the CWD/`host_config` import convention, and a "How to add a new host" recipe. Add 2–3 `how_to/` articles (single-volume index, geometry tables, GCP run) with numbered steps, expected results, and troubleshooting; cross-link them with the user guide.
> 7. **Diagrams.** Add a pipeline flow diagram and the class diagram using the already-enabled `sphinxcontrib.mermaid`; confirm they render.
>
> Verify by running both build commands above with zero warnings.
