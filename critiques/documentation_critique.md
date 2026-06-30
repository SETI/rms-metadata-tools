# Documentation Critique Report

**Generated:** 2026-06-29
**Scope:** `README.md`, `CONTRIBUTING.md`, `docs/` (all RST/MD/conf files), `pyproject.toml`
documentation-adjacent sections, and all `src/metadata_tools/` module/class/function
docstrings. Rules applied: `.cursor/rules/doc_python.mdc`, `.cursor/rules/doc_readme.mdc`,
`.cursor/rules/doc_user_guide.mdc`, `.cursor/rules/doc_dev_guide.mdc`,
`.cursor/rules/doc_how_to.mdc`, `.cursor/rules/documentation.mdc`.

Verification runs performed:
- `sphinx-build -W -b html docs /tmp/sphinx-out-W` → **PASSED, zero warnings**
- `sphinx-build -n -b html docs /tmp/sphinx-out-n` → **PASSED, zero warnings**
- Grep: `Args:` in docs/src → none (all `Parameters:`)
- Grep: time-anchored phrases (`currently`, `now`, `recently`) → none
- Grep: `print(` in `src/metadata_tools/` → none

---

## Executive summary

The documentation is in excellent shape after the `ai_rewrite` overhaul (PR #116). Both
Sphinx builds pass with zero warnings. User and developer guides are comprehensive,
cross-references use correct Sphinx roles throughout, and all engine module docstrings
follow the `Parameters:` convention. No time-anchored language or stray `print()` calls
were found.

Ten issues remain, none build-breaking:

- **High (3):** Nine `geometry_support` submodules lack module-level docstrings (autodoc
  shows blank descriptions); a stale reference in `__init__.py` points to the old
  monolithic `geometry_support.py`; `SunTable` is documented in the architecture diagram
  and narrative but is commented out of the live code path.
- **Medium (4):** `dev_guide_environment.rst` claims CI runs `ruff format --check` (it does
  not); this directly contradicts `dev_guide_conventions.rst`; CI does not run
  `sphinx-build -n`; `CONTRIBUTING.md` uses `make html` instead of `scripts/read-docs.sh`
  and has a non-Conventional-Commits example commit message.
- **Low (3):** README section title `Licensing` should be `License` per rule; no standalone
  how-to articles (examples are in the user guide appendix, not a dedicated how-to section);
  `pyproject.toml` comment says `py.typed` is "NOT declared" but it is shipped.

All fixes are surgical. None require structural changes to the docs.

---

## 1. Documentation system and build (`doc_python`)

**PASS — both `-W` and `-n` builds produce zero warnings.** The Sphinx configuration is
thorough: all required extensions are present (`autodoc`, `napoleon`, `viewcode`,
`intersphinx`, `myst_parser`, `sphinxcontrib.mermaid`); `napoleon_google_docstring = True`
and `napoleon_use_param = True` are set; `nitpick_ignore_regex` covers the third-party
symbols that lack inventories, with implicit justification; the `oops` import shim allows
headless autodoc builds; and the `<!-- start-after-point -->` marker in `README.md` is
correctly consumed by `docs/index.rst`.

**Finding M1 (Medium) — CI does not run `sphinx-build -n`.**
`doc_python` §2 requires the build to pass both `-W` and `-n`. The CI workflow
`.github/workflows/run-tests.yml` only runs `sphinx-build -W`. The `-n` (nitpicky)
pass catches unresolved cross-references that `-W` misses. As of this review the `-n`
build passes locally, but the gate is not enforced in CI.

**Fix:** Add `sphinx-build -n -b html docs /tmp/sphinx-out-n` (or `-W -n` combined)
to the `lint` job in `run-tests.yml`, and add the same flag to `scripts/run-all-checks.sh`.

---

## 2. Docstrings and API reference (`doc_python`)

**Finding H1 (High) — `geometry_support` package `__init__.py` has no module docstring.**
`src/metadata_tools/geometry_support/__init__.py` contains only a `#`-style banner comment.
`ast.get_docstring()` returns `None`; autodoc renders a blank description for the
`metadata_tools.geometry_support` module page.

**Evidence:** `src/metadata_tools/geometry_support/__init__.py:1-3` (only `#` banner,
no `"""..."""`).

**Fix:** Add a one-paragraph `"""..."""` module docstring immediately below the banner,
e.g.:
```python
"""Geometry table generation for metadata_tools.

Computes geometric quantities (body, ring, sky, sun) from SPICE via ``oops``
and writes them as PDS3 summary (and optionally detailed) CSV tables.
"""
```

**Finding H2 (High) — Nine `geometry_support` submodules lack module-level docstrings.**
The following files have only `#`-style banner headers; none have a `"""..."""` module
docstring, so autodoc generates blank module descriptions for all of them:

| File | Banner text |
|---|---|
| `geometry_support/bodies_select.py` | Body selection utilities |
| `geometry_support/masks.py` | Pixel mask construction |
| `geometry_support/prep.py` | Row preparation |
| `geometry_support/formatting.py` | Column formatting |
| `geometry_support/formats.py` | FORMAT_DICT and ALT_FORMAT_DICT |
| `geometry_support/record.py` | Record class |
| `geometry_support/tables.py` | Table subclasses |
| `geometry_support/suite.py` | Suite class |
| `geometry_support/process.py` | process_geometry() entry point |

**Fix:** Add a one-sentence `"""..."""` module docstring to each file. The existing banner
text is sufficient starting material. Example for `formats.py`:
```python
"""Master format dictionaries (FORMAT_DICT, ALT_FORMAT_DICT) for geometry columns."""
```

**Finding H3 (High) — `__init__.py` docstring contains a stale module reference.**
`src/metadata_tools/__init__.py:81` reads:

> "Add a row to the format dictionary in ``geometry_support.py``"

`geometry_support` is now a package; the format dictionary lives in
`geometry_support/formats.py`. The stale path appears in the public-facing package
docstring rendered on the API reference page.

**Evidence:** `src/metadata_tools/__init__.py:81`.

**Fix:** Change the reference to `:mod:`metadata_tools.geometry_support.formats`` (or
``geometry_support/formats.py``).

---

## 3. Cross-reference completeness (`doc_python`)

**PASS.** All narrative prose in the user guide and developer guide uses proper Sphinx
cross-reference roles (`:class:`, `:meth:`, `:func:`, `:mod:`, `:attr:`, `:data:`)
where API symbols appear. Both `-W` and `-n` builds resolve all references with zero
warnings. Section titles that include class names (`IndexTable`, `Suite`, `Record and prep`)
are exempt from the "no bare API symbols in prose" rule per `doc_python` §5.

---

## 4. README (`doc_readme`)

**Largely compliant.** The README has all required sections in the required order:
Title, Badges, Introduction, Features, Installation, Quick Start, Documentation,
Contributing, Links. Badges are comprehensive. The Quick Start has runnable examples.
The `<!-- start-after-point -->` marker is correctly placed after the badge block.

**Finding L1 (Low) — Section title `Licensing` should be `License`.**
`doc_readme` §8 specifies `**License**` as the final section title. The README uses
`## Licensing`.

**Evidence:** `README.md` (search for `## Licensing`).

**Fix:** Rename `## Licensing` → `## License`.

---

## 5. User guide (`doc_user_guide`)

**PASS.** The user guide is comprehensive and well-structured. All required sections are
present:

- `user_guide_overview.rst` — pipeline overview with a Mermaid workflow diagram
- `user_guide_installation.rst` — setup, env vars (`$RMS_METADATA`, `$RMS_VOLUMES`,
  `$RMS_METADATA_TEST`), supported Python versions
- `user_guide_index.rst`, `user_guide_geometry.rst`, `user_guide_cumulative.rst` —
  per-table-type chapters, each with complete CLI option documentation
- `user_guide_configuration.rst` — host config model, override hooks
- `user_guide_cloud.rst` — GCP distribution
- `user_guide_examples.rst` — end-to-end workflow examples
- `user_guide_appendix_hosts.rst` — per-host appendix

All cross-references use correct Sphinx roles. Every documented CLI option traces back
to the argparse definitions.

---

## 6. Developer guide (`doc_dev_guide`)

**Largely compliant.** Architecture, class diagram (Mermaid), per-subsystem chapters,
and an "extending" recipe are all present.

**Finding H4 (High) — `SunTable` documented but commented out of the live code path.**
`docs/dev_guide/dev_guide_architecture.rst` includes `SunTable` in:
- The Mermaid class diagram (lines 53, 80)
- The narrative prose (line 120)

But `src/metadata_tools/geometry_support/suite.py:176` has `#SunTable(...)` commented
out, and `src/metadata_tools/cumulative_support.py` does not include `SunTable` in its
`tables` list.

Readers who follow the dev guide's "how to add a new host" recipe will think `SunTable`
is an available, tested table type.

**Fix (option A — preferred if SunTable is intentionally deferred):** Remove `SunTable`
from the class diagram and narrative in `dev_guide_architecture.rst`, and add a note
in the extending chapter that sun-geometry support is planned but not yet implemented.

**Fix (option B — if SunTable is ready but accidentally disabled):** Uncomment
`SunTable(...)` in `suite.py:176` and add it to `cumulative_support.py`'s `tables` list,
then update and validate tests.

**Finding M2 (Medium) — `dev_guide_environment.rst` claims `ruff format --check` runs in CI.**
`docs/dev_guide/dev_guide_environment.rst:123` lists the CI lint checks as including
`ruff format --check`. The actual CI workflow (`.github/workflows/run-tests.yml`) does
**not** run `ruff format --check` — the lint job runs only `ruff check`, `mypy`, `bandit`,
`vulture`, `sphinx-build -W`, and `pymarkdown`.

This contradicts `docs/dev_guide/dev_guide_conventions.rst:32-33`, which correctly states:
"The project does not run `ruff format` as a gate; `ruff check` is the linter."

**Evidence:** `.github/workflows/run-tests.yml` (lint job steps) vs.
`dev_guide_environment.rst:123` vs. `dev_guide_conventions.rst:32-33`.

**Fix:** Remove `ruff format --check` from the CI check list in
`dev_guide_environment.rst:123` so that it matches both the actual CI configuration and
the conventions chapter. (Alternatively, add `ruff format --check` to CI and to
`scripts/run-all-checks.sh` if the team wants to enforce formatting as a gate — in that
case update `dev_guide_conventions.rst:32-33` to match.)

---

## 7. How-to articles (`doc_how_to`)

**Finding L2 (Low) — No standalone how-to articles.**
`doc_how_to` expects standalone, task-focused articles with action-oriented titles,
prerequisites, numbered steps, expected results, and troubleshooting. The user guide
appendix (`user_guide_examples.rst`) covers end-to-end workflows, but these are embedded
in the user guide rather than structured as independent how-to articles with the required
sections.

This is a minor gap — the material exists, just not in the prescribed form.

**Fix:** Optionally extract 2–3 key workflows from `user_guide_examples.rst` into a
dedicated `docs/how_to/` directory with the `doc_how_to`-required structure:
- `how_to_generate_supplemental_index.rst`
- `how_to_generate_geometry_tables.rst`
- `how_to_run_gcp_pipeline.rst`

Or, if the team prefers, add a how-to landing page that cross-links to the relevant
sections of the user guide, satisfying the navigational intent of the rule.

---

## 8. Diagrams and figures

**PASS.** A Mermaid workflow diagram appears in `user_guide_overview.rst` and a Mermaid
class diagram appears in `dev_guide_architecture.rst`. Both render in the Sphinx build
(verified — zero warnings). The `sphinxcontrib.mermaid` extension is correctly configured.

**Note:** The class diagram needs updating per Finding H4 (remove or mark `SunTable`
as unimplemented).

---

## 9. Change discipline and consistency (`doc_python`)

**Finding M3 (Medium) — `CONTRIBUTING.md` uses `make html` for docs build.**
`CONTRIBUTING.md` instructs contributors to build docs with `cd docs && make html`.
The canonical build command documented in `dev_guide_environment.rst` and in
`scripts/read-docs.sh` is `scripts/read-docs.sh` (which applies `-W` and opens the
browser). Contributors following `CONTRIBUTING.md` will get a build without `-W` and
will not catch warnings.

**Evidence:** `CONTRIBUTING.md` (search for `make html`).

**Fix:** Replace `cd docs && make html` with `scripts/read-docs.sh` (or the equivalent
`sphinx-build -W -b html docs docs/_build`) and add a note that `scripts/run-all-checks.sh`
runs all gates including docs.

**Finding M4 (Medium) — CONTRIBUTING.md commit message example does not follow Conventional Commits.**
The project mandates Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) per
`.cursor/rules/git_workflow.mdc` and `dev_guide_conventions.rst`. `CONTRIBUTING.md`
shows an example commit message that does not follow this format.

**Fix:** Replace the example with a valid Conventional Commits example, e.g.:
```
feat: add ring-plane geometry for GO_0xxx
```
And add a brief pointer to the Conventional Commits specification or the
`dev_guide_conventions.rst` git section.

**Finding L3 (Low) — `pyproject.toml` comment contradicts shipped `py.typed`.**
`pyproject.toml:76-77` contains the comment:

> "py.typed is intentionally NOT declared"

But `pyproject.toml:79` includes `py.typed` in `package-data`, and the file
`src/metadata_tools/py.typed` exists. The file will be shipped to PyPI and discovered
by type checkers (PEP 561). The comment is wrong.

**Evidence:** `pyproject.toml:76-79`, `src/metadata_tools/py.typed`.

**Fix:** Remove the misleading comment. If `py.typed` is intentionally shipped (which
shipping it in `package-data` implies), the correct note would be:
```
# py.typed ships PEP 561 type information to downstream consumers
```

---

## Recommended priorities

1. **H1–H2 (geometry_support docstrings, ~15 min):** Add one-line `"""..."""` module
   docstrings to `geometry_support/__init__.py` and its nine submodules. Zero behavior
   change; instant improvement to generated API reference.

2. **H3 (stale `__init__.py` reference, 2 min):** Change `geometry_support.py` →
   `geometry_support/formats.py` in `src/metadata_tools/__init__.py:81`.

3. **H4 (SunTable in architecture, 10 min):** Decide intent. If deferred: remove
   `SunTable` from `dev_guide_architecture.rst` diagram and prose. If ready: uncomment it
   in `suite.py` and `cumulative_support.py`.

4. **M1–M2 (CI documentation accuracy, 10 min):** Fix `dev_guide_environment.rst:123`
   to remove `ruff format --check` from the listed CI steps; add `sphinx-build -n` to
   the CI lint job and to `scripts/run-all-checks.sh`.

5. **M3–M4 (CONTRIBUTING.md, 5 min):** Replace `make html` with `scripts/read-docs.sh`;
   fix the commit message example to use Conventional Commits format.

6. **L1 (README title, 1 min):** Rename `## Licensing` → `## License`.

7. **L2 (how-to articles, optional):** Extract or restructure workflow examples into
   `doc_how_to`-compliant standalone articles.

8. **L3 (py.typed comment, 1 min):** Remove or correct the misleading comment in
   `pyproject.toml:76-77`.

---

## Prompt for an AI agent to fix the documentation

You are fixing documentation issues in the `rms-metadata-tools` Python package. The
package lives at `src/metadata_tools/`; Sphinx docs are under `docs/`. Rules are in
`.cursor/rules/doc_*.mdc`. Do not change any production code behavior — only docstrings,
documentation files, and CI/script configuration.

**Verification gate:** after all changes, BOTH of these must pass with zero warnings:
```sh
sphinx-build -W -b html docs /tmp/sphinx-out-W
sphinx-build -n -b html docs /tmp/sphinx-out-n
```
Run these before reporting success.

**Issue 1 — Add module docstrings to `geometry_support` package (High)**

File: `src/metadata_tools/geometry_support/__init__.py`
Currently: only a `################################################################################` banner header, no `"""..."""` docstring.
Fix: Insert a module docstring immediately below the banner:
```python
"""Geometry table generation for metadata_tools.

Computes geometric quantities (body, ring, sky, sun) from SPICE via ``oops``
and writes them as PDS3 summary (and optionally detailed) CSV tables.
Submodules handle body selection, mask construction, row preparation, column
formatting, format dictionaries, the :class:`Record` and :class:`Suite`
classes, table subclasses, and the top-level :func:`process_geometry` entry
point.
"""
```

**Issue 2 — Add module docstrings to nine geometry_support submodules (High)**

Each of the following files has only a `#` banner and no `"""..."""` module docstring.
Add a single-line (or short) docstring to each:

- `src/metadata_tools/geometry_support/bodies_select.py` →
  `"""Body and system selection utilities for geometry processing."""`
- `src/metadata_tools/geometry_support/masks.py` →
  `"""Pixel mask construction for excluded regions in geometry tables."""`
- `src/metadata_tools/geometry_support/prep.py` →
  `"""Row preparation: assembles formatted geometry strings for one observation."""`
- `src/metadata_tools/geometry_support/formatting.py` →
  `"""Low-level column formatters that convert backplane values to fixed-width strings."""`
- `src/metadata_tools/geometry_support/formats.py` →
  `"""Master format dictionaries (FORMAT_DICT, ALT_FORMAT_DICT) for geometry columns."""`
- `src/metadata_tools/geometry_support/record.py` →
  `"""Record class: per-observation state for geometry table generation."""`
- `src/metadata_tools/geometry_support/tables.py` →
  `"""Geometry table subclasses (BodyTable, RingTable, SkyTable, InventoryTable)."""`
- `src/metadata_tools/geometry_support/suite.py` →
  `"""Suite class: coordinates all geometry tables for one data file."""`
- `src/metadata_tools/geometry_support/process.py` →
  `"""Top-level entry point process_geometry() for geometry table generation."""`

Insert each docstring immediately below the existing `#` banner (before the first import).

**Issue 3 — Fix stale reference in `__init__.py` docstring (High)**

File: `src/metadata_tools/__init__.py`, line 81
Current text: `"Add a row to the format dictionary in ``geometry_support.py``"`
Problem: `geometry_support` is now a package; the format dict is in `geometry_support/formats.py`.
Fix: Change to `"Add a row to the format dictionary in ``geometry_support/formats.py``"`
(or use `:mod:`metadata_tools.geometry_support.formats``).

**Issue 4 — Remove `SunTable` from architecture documentation (High)**

`SunTable` is listed in `docs/dev_guide/dev_guide_architecture.rst` in both the Mermaid
class diagram and the prose description, but `src/metadata_tools/geometry_support/suite.py:176`
has `#SunTable(...)` commented out and `src/metadata_tools/cumulative_support.py` does not
include `SunTable` in its `tables` list.

First, confirm by reading those files that `SunTable` is indeed commented out everywhere.

If confirmed:
- In `docs/dev_guide/dev_guide_architecture.rst`, find the Mermaid `classDiagram` block
  (around lines 53 and 80) and remove the `SunTable` node and its inheritance arrow.
- In the prose narrative (around line 120), remove the mention of `SunTable` from the
  list of active table classes.
- Add a note (one sentence) in the "Geometry subsystem" section of the dev guide stating
  that sun-geometry support (`SunTable`) is planned but not yet implemented in the active
  code path.

**Issue 5 — Fix `dev_guide_environment.rst` CI step list (Medium)**

File: `docs/dev_guide/dev_guide_environment.rst`, line ~123
Current text claims CI runs: `ruff check`, `ruff format --check`, `mypy`, `bandit`,
`vulture`, `sphinx-build -W`, `pymarkdown`.
Actual CI (`.github/workflows/run-tests.yml` lint job): `ruff check`, `mypy`, `bandit`,
`vulture`, `sphinx-build -W`, `pymarkdown` — does NOT run `ruff format --check`.
This directly contradicts `docs/dev_guide/dev_guide_conventions.rst:32-33` which correctly
says `ruff format` is not a CI gate.

Fix: Remove `ruff format --check` from the listed CI steps in `dev_guide_environment.rst`.
Do NOT change `dev_guide_conventions.rst` (it is correct).

**Issue 6 — Add `sphinx-build -n` to CI (Medium)**

File: `.github/workflows/run-tests.yml`
`doc_python` requires clean builds under both `-W` and `-n`. Currently only `-W` runs in CI.

Fix: In the `lint` job, after the `sphinx-build -W` step, add:
```yaml
- name: Build docs (nitpicky)
  run: sphinx-build -n -b html docs /tmp/sphinx-out-n
```

Also update `scripts/run-all-checks.sh`: wherever `sphinx-build -W` appears, either
combine the flags (`-W -n`) or add a second sphinx step.

Update `dev_guide_environment.rst` to list `sphinx-build -n` alongside `sphinx-build -W`.

**Issue 7 — Fix CONTRIBUTING.md docs build command (Medium)**

File: `CONTRIBUTING.md`
Find the line that says `cd docs && make html` and replace it with:
```sh
scripts/read-docs.sh
```
Add a sentence: "The `scripts/run-all-checks.sh` script runs all quality gates (lint,
type-check, tests, docs, and markdown) and is the canonical local check before pushing."

**Issue 8 — Fix CONTRIBUTING.md commit message example (Medium)**

File: `CONTRIBUTING.md`
Find the example commit message and verify it does not follow Conventional Commits format
(`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
Replace with a valid example:
```
feat: add ring-plane geometry support for GO_0xxx
```
Add a note: "Follow the Conventional Commits specification
(https://www.conventionalcommits.org). See the developer guide conventions chapter for
this project's commit types and 50-character subject-line rule."

**Issue 9 — Rename README section `Licensing` → `License` (Low)**

File: `README.md`
Find `## Licensing` and rename to `## License` (per `doc_readme` §8 which specifies
`**License**` as the section title).

**Issue 10 — Fix misleading `py.typed` comment in `pyproject.toml` (Low)**

File: `pyproject.toml`, lines 76-77
Current comment: "py.typed is intentionally NOT declared" (or similar)
Problem: `py.typed` IS included in `package-data` on line ~79 and the file
`src/metadata_tools/py.typed` exists. The comment is wrong.
Fix: Replace the comment with:
```toml
# py.typed ships PEP 561 inline type information to downstream type-checkers
```

**After all changes:**
1. Run `sphinx-build -W -b html docs /tmp/sphinx-out-W` — must pass with zero warnings.
2. Run `sphinx-build -n -b html docs /tmp/sphinx-out-n` — must pass with zero warnings.
3. Run `grep -r 'Args:' docs/ src/` — must return no results (all docstrings use `Parameters:`).
4. Confirm `CONTRIBUTING.md` no longer references `make html`.
5. Confirm `.github/workflows/run-tests.yml` now includes `sphinx-build -n`.
