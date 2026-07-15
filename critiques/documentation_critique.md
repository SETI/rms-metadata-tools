# Documentation Critique Report

**Generated:** 2026-07-15
**Scope:** `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, the whole
`docs/` tree (Sphinx: `conf.py`, `index.rst`, `user_guide/`, `dev_guide/`,
`dev_guide/api/`, `contributing.rst`, `code_of_conduct.md`), the docstrings in
`src/metadata_tools/`, and the two Sphinx build scripts (`docs/Makefile`,
`scripts/read-docs.sh`).
**Rules applied:** `doc_python.mdc` (foundation), `doc_readme.mdc`,
`doc_user_guide.mdc`, `doc_dev_guide.mdc`, `doc_how_to.mdc`, and the older
`documentation.mdc`. All are present. There are no how-to articles in the repo,
so the `doc_how_to.mdc` checklist is applied as an "absence" observation only.

## Executive summary

The documentation is unusually complete and well-organized for a package this
size: a marker-included `README`, a full user guide (overview, installation,
configuration, one chapter per command-line program, cloud runs, examples, a
hosts appendix), a full developer guide (introduction, layout, environment,
architecture with a Mermaid class diagram, per-subsystem chapters, an extending
recipe, conventions), and an autodoc API reference with a curated
`nitpick_ignore_regex` that deliberately does **not** suppress the package's own
symbols. Docstring coverage of the engine is essentially complete and
Google-style with `Parameters:`.

**Build health:** I could not execute `sphinx-build` in this review environment,
so the report is a static critique. The configuration is set up to pass under
both `-W` (warnings-as-errors) and `-n` (nitpicky): `conf.py` mocks `oops` and
the three host-config module names, and `nitpick_ignore_regex` covers the
untyped third-party stack. The most likely build risks are the stale
cross-references and code/doc mismatches listed below (a `:doc:` or option that
no longer matches the code will not fail the build, but a mistyped `:func:`
target would fail under `-n`).

**High-priority fixes** (accuracy, since inaccurate docs are worse than missing
docs):

1. **Task-file schema example contradicts the code** — the documented
   `task_id` prefix does not match what `make_task` produces.
2. **`metadata-task-list --output` documented as "Required" in scan mode** — it
   is optional there.
3. **`SunTable` is documented as a live table** (class diagram + prose) but is
   not wired into the pipeline.
4. **A single-test example references a non-existent test class** — repeated in
   both the developer guide and `CLAUDE.md`.
5. **`CONTRIBUTING.md` is generic boilerplate** that contradicts the project's
   own conventions (PEP 8 line length, non-Conventional-Commits example, an
   unrelated example function).

**Nice-to-have:** minor prose/consistency items (copyright/author mismatch,
one Zenodo placeholder badge, the CI-gate description drift, absence of how-to
articles).

## 1. Documentation system and build

- **Single source tree, correct config.** All docs live under `docs/` with one
  `conf.py`; `docs/_build/` is git-ignored (`.gitignore:75`). `conf.py` enables
  autodoc, napoleon, viewcode, intersphinx, `sphinxcontrib.mermaid`, and
  `myst_parser`; puts `../src` on `sys.path`; derives the version from
  `importlib.metadata`; and mocks `oops` plus `host_config`/`index_config`/
  `geometry_config` for headless autodoc (`docs/conf.py:14-125`). This satisfies
  `doc_python.mdc` §3.
- **Nitpick discipline is exemplary.** `nitpick_ignore_regex`
  (`conf.py:170-198`) ignores only third-party symbols with no inventory
  (filecache, pds*, oops, polymath, julian, cspyce, fortranformat, numpy typing,
  pytest) and carries a comment stating that package-owned symbols are
  deliberately *not* listed — exactly `doc_python.mdc` §3's requirement.
- **Prose conventions:** American spelling and single-space sentence spacing are
  followed in the `.rst`/`.md` files. No unicode smart quotes/arrows were seen in
  `.py` docstrings.
- **Finding (Low) — time-anchored phrasing in docstrings.** `doc_python.mdc` §2
  forbids "new/now/legacy" framing. A few docstrings/comments use present-moment
  framing, e.g. `config.py` and the architecture prose lean on "lazily … so
  stages never pay the SPICE cost" (acceptable, describes current behavior), but
  the `formats.py` FORMAT_DICT header note "Note null_value … are tracked … but
  not currently used to populate the label" uses "currently"
  (`geometry_support/formats.py:31-33`). **Suggestion:** reword to describe the
  current design without "currently".
- **Finding (Low) — `scripts/read-docs.sh` builds only under `-W`, not `-n`.**
  The convenience script runs `make html SPHINXOPTS="-W"` (`read-docs.sh:39`),
  while `run-all-checks.sh` correctly builds with `-W -n` (`run-all-checks.sh:493`)
  and CI runs `-W -n` (`run-tests.yml:48`). **Suggestion:** add `-n` to
  `read-docs.sh` so the local preview matches the gate.

## 2. Docstrings and API reference

- **Coverage:** every engine module, class, method, and function carries a
  Google-style docstring with `Parameters:` and `Returns:`/`Raises:` where
  applicable (verified across `common.py`, `config.py`, `util.py`,
  `index_support/*`, `geometry_support/*`, `columns/*`, `cumulative_support.py`,
  `label_support.py`, `task_list_support.py`, `bodies.py`, `defs.py`). This is a
  genuine strength.
- **API reference completeness:** the reference has a landing page with a
  `toctree` and one page per subpackage
  (`docs/dev_guide/api/{api,core,config,task_list_support,index_support,geometry_support,cumulative_support,columns}.rst`),
  each using `automodule` with `:members: :undoc-members: :show-inheritance:`.
  The `cli/*` package is intentionally excluded (documented as non-API in
  `dev_guide_layout.rst:104-108`), consistent with `doc_dev_guide.mdc` §6.
- **Finding (Low) — `index_support` submodules are not given their own autodoc
  pages.** `api/index_support.rst` documents only the package `__init__` (whose
  `__all__` re-exports `IndexTable`, `_create_index`, `get_args`, the key
  functions), whereas `api/geometry_support.rst` documents each submodule
  separately. Members reachable via `__all__` still render, but the
  method-level docstrings of `IndexTable` come through the re-export rather than
  a `table.py` page. **Suggestion:** for parity and to guarantee full method
  coverage, add per-submodule `automodule` blocks for `index_support.table`,
  `index_support.process`, and `index_support.key_fns` (mirroring the geometry
  page), or confirm the re-export renders every member under `-W`.
- **Finding (Low) — private-but-documented API.** `_create_index` is in
  `index_support.__all__` and thus in the public reference despite the leading
  underscore. It is genuinely internal (called only by `process_index`).
  **Suggestion:** either drop it from `__all__` (and the reference) or rename it
  without the underscore if it is meant to be public; today the leading
  underscore and `__all__` membership send mixed signals.

## 3. Cross-reference completeness

- **Roles are used correctly and thoroughly.** Narrative prose links code
  objects with `:func:`, `:class:`, `:meth:`, `:mod:`, `:data:` throughout the
  guides (e.g. `dev_guide_architecture.rst`, `dev_guide_geometry_subsystem.rst`,
  `user_guide_overview.rst`). Inline literals are reserved for CLI tokens, file
  paths, and env vars, per `doc_python.mdc` §5.
- **Finding (Medium) — potential stale/omitted cross-references tied to
  `SunTable`.** `dev_guide_architecture.rst:57-60` and the class-diagram block
  present `SunTable` as a live geometry table, and lines 120-132 describe "the
  five geometry tables"; because `SunTable` is not instantiated by `Suite`
  (see §6 and the code critique), this prose is misleading even though the
  `:class:` reference resolves. **Suggestion:** when the code question is
  settled, update the diagram and prose in the same change (`doc_python.mdc` §7).
- **Finding (Low) — bare symbol names in a couple of spots.** Most prose uses
  roles, but a few mentions of engine concepts appear as inline literals rather
  than roles, e.g. ``from_index`` / ``target_name`` / ``cleanup`` hooks in
  `user_guide_configuration.rst:55` and `dev_guide_extending.rst`. These are
  host-config *attributes* injected by plugin modules that autodoc mocks, so a
  `:func:` role would not resolve — inline literal is the pragmatic choice here.
  No action required, but note it is a deliberate exception, not an oversight.

## 4. README (`doc_readme.mdc`)

- **Format/inclusion:** Markdown with a single top-level title and the
  `<!-- start-after-point -->` marker after the badge block, so badges do not
  leak into the Sphinx build (`README.md:27`, included by `docs/index.rst:7-9`).
- **Required sections present and in order:** title, grouped badges,
  Introduction, Features, Installation (Python versions + prerequisites +
  `pip install`), Quick Start (one invocation per stage), Documentation (+ local
  build), Contributing, Links, License. Matches `doc_readme.mdc` §2.
- **Quickstart is runnable** as written (env-var-expanded paths, clearly
  symbolic), and every shipped program family is mentioned with a pointer to the
  user guide.
- **Finding (Low) — Zenodo DOI badge looks like a placeholder.** The badge URL
  is `https://zenodo.org/badge/rms-metadata-tools.svg` and links to
  `zenodo.org/badge/latestdoi/rms-metadata-tools` (`README.md:26`). Zenodo
  badges normally use a numeric record ID; a name-based path typically does not
  resolve. **Suggestion:** replace with the real numeric Zenodo badge or remove
  it until a DOI exists (`doc_readme.mdc` §3: "Verify all links resolve").
- **Finding (Low) — badge/version consistency.** The README badges are
  consistent with packaging metadata (PyPI name, Python versions, license,
  RTD/codecov). No mismatch found; recorded as a passing check.

## 5. User guide (`doc_user_guide.mdc`)

Layout, landing page + `toctree`, per-program chapters, configuration chapter,
and a hosts appendix are all present and correctly cross-linked (absolute
`:doc:` to `/dev_guide/...`, relative within the guide). Strong overall. Issues:

- **Finding (High) — task-file schema contradicts the code.**
  `user_guide_cloud.rst:262-283` shows task objects with
  `"task_id": "geometry-task-GO_0017"` and states "The `task_id` prefix
  identifies the stage that produced the file." But
  `task_list_support.make_task` always emits `f'task-{volume_id}'` with **no
  stage prefix** (`task_list_support.py:21-30`), and the committed example
  `cloud/GO_0xxx/tasks.json` confirms `"task_id": "task-GO_0001"`.
  **Suggestion:** change the example to `"task-GO_0017"` and delete the
  "prefix identifies the stage" sentence (or implement stage-prefixed IDs in
  code if that behavior is actually wanted).

- **Finding (High) — `metadata-task-list --output` is not required in scan
  mode.** `user_guide_cloud.rst:249-251` documents `--output FILE` as
  "Required. A bare filename is resolved against the host's directory." In scan
  mode the flag is **optional** and defaults to `tasks.json` in the cloud/host
  directory (`cli/task_list.py:40-47`). `--output` is required only in
  *explicit* mode (`task_list.py:59-63`). **Suggestion:** document `--output` as
  optional in scan mode (state the `tasks.json` default and the base directory)
  and required in explicit mode.

- **Finding (Medium) — CLI option coverage vs. the actual parser.**
  `doc_user_guide.mdc` §3 requires documenting *every* option. The cloud page
  documents `--config`, `--task-file`, `--use-spot`, and the cloud-only
  overrides, but the underlying `rms-cloud-tasks` `run`/`Worker` options
  (e.g. `--num-simultaneous-tasks`, `--use-spot`, and other cloud_tasks flags)
  are forwarded, not enumerated. The guide notes worker scripts "accept all
  options of their non-cloud counterpart, plus …" and lists the key ones, which
  is a reasonable summary for third-party-forwarded flags. **Suggestion:** add a
  one-line pointer to the `rms-cloud-tasks` documentation for the full forwarded
  option set, so the guide is explicit that those come from the dependency.

- **Finding (Low) — environment-variable table lists conventions only.**
  `user_guide_installation.rst:62-91` correctly explains the programs read no
  env var directly (paths are `$VAR`-expanded), and lists `RMS_VOLUMES` /
  `RMS_METADATA` / `RMS_METADATA_TEST` as conventions. Good; no change.

## 6. Developer guide (`doc_dev_guide.mdc`)

Layout, landing page ending with the API reference, required chapters
(introduction, annotated layout, environment setup incl. test tiers/CI/release,
architecture + class diagram, per-subsystem chapters, extending recipe,
conventions) are all present. Strong. Issues:

- **Finding (Medium) — class diagram and prose overstate `SunTable`.**
  `dev_guide_architecture.rst` includes `SunTable` in the `classDiagram` and
  describes it among the tables the `Suite` owns; `dev_guide_geometry_subsystem.rst:32`
  says the suite creates "an inventory table plus sky, ring, and body tables"
  (correctly omitting Sun) — so the two chapters disagree with each other, and
  the architecture chapter disagrees with the code (`Suite.add_tables` has
  `SunTable` commented out, `suite.py:178`). **Suggestion:** make the two dev-guide
  chapters consistent and align with the code decision (§ code critique):
  either drop `SunTable` from the diagram/prose or wire it in.

- **Finding (Medium) — non-existent single-test example (repeated).**
  `dev_guide_environment.rst:74` shows
  `pytest tests/test_index.py::Test_Index_Common::test_supplemental_index_common`,
  but `tests/test_index.py` defines module-level functions, not a
  `Test_Index_Common` class. The identical wrong example appears in
  `CLAUDE.md` ("Common commands"). **Suggestion:** replace with a real target,
  e.g. `pytest tests/test_index_support.py::test_format_value_real`, and fix
  `CLAUDE.md` in the same change.

- **Finding (Low) — CI-gate description drifts from the workflow.**
  `dev_guide_environment.rst:122-124` says the lint job runs
  "`ruff check`, `ruff format --check`, `mypy`, `bandit`, `vulture`, sphinx,
  pymarkdown", and `dev_guide_conventions.rst:33-35` says `ruff format --check`
  "is run by `scripts/run-all-checks.sh`". In fact `run-tests.yml` does **not**
  run `ruff format --check` (only `ruff check`), and `run-all-checks.sh` ships
  `ENABLE_RUFF_FORMAT=false` (`run-all-checks.sh:102`), so neither runs it; the
  script *does* enable `pyroma`, which CI does not run. **Suggestion:** describe
  the gates exactly as CI and the script run them (this pairs with the code
  critique's CI-reconciliation item; fix docs after the gates are reconciled).

- **Finding (Low) — layout tree omits the committed `*.db` files and lists
  `SunTable` in `tables.py`.** `dev_guide_layout.rst:71` lists
  `InventoryTable, SkyTable, SunTable, RingTable, BodyTable` for `tables.py`
  (accurate to the file) — fine — but the annotated tree does not mention the
  three committed `metadata-*.db` artifacts under `src/metadata_tools/` (which
  should be removed per the code critique). **Suggestion:** no doc change needed
  once the `.db` files are removed from the repo.

- **Strength:** the extending chapter gives concrete, correct skeletons for all
  three extension points (new host, index key function, geometry column) with
  registration details, satisfying `doc_dev_guide.mdc` §5.

## 7. How-to articles (`doc_how_to.mdc`)

- **Finding (Low) — no how-to articles exist.** `doc_how_to.mdc` is present, but
  there are no task-focused how-to pages; the user guide's "Examples" chapter
  (`user_guide_examples.rst`) partially fills this role (end-to-end run, smoke
  test, labels-only, Python API). **Suggestion:** optional. If the team wants
  how-tos, the obvious candidates are "How to add a new host" (a task-shaped
  version of `dev_guide_extending.rst`) and "How to run a GCP geometry job"; each
  should follow the `doc_how_to.mdc` structure (prerequisites, numbered steps
  with observed results, troubleshooting) and link to the existing reference
  chapters rather than duplicating them.

## 8. Diagrams and figures

- **Finding:** two Mermaid diagrams are used appropriately — a workflow
  `flowchart` in `user_guide_overview.rst:62-72` and a `classDiagram` in
  `dev_guide_architecture.rst:37-91`. `conf.py` sets
  `mermaid_output_format = 'raw'` for client-side rendering (no `mmdc` binary
  needed in CI), matching `doc_python.mdc` §3. The only issue is the class
  diagram's accuracy re `SunTable` (§6). No cross-references appear inside the
  diagram blocks, per `doc_python.mdc` §5. Good.

## 9. Change discipline and consistency

- **Finding (High) — `CONTRIBUTING.md` is generic boilerplate at odds with the
  project's own standards.** It tells contributors to "Follow PEP 8" (79-column
  implication) whereas the project uses 100 (`pyproject.toml`,
  `dev_guide_conventions.rst`); its worked example is an unrelated
  `calculate_offset(image, model)` with an undefined `NDArrayFloatType` type,
  not a `metadata_tools` example; its commit-message example
  `git commit -m "Add feature: description of your changes"` contradicts the
  Conventional Commits policy stated in `git_workflow.mdc` and
  `dev_guide_conventions.rst`; and it says to build docs with `cd docs && make
  html` (no `-W -n`) rather than the project's `scripts/read-docs.sh` /
  `run-all-checks.sh -d`. **Suggestion:** rewrite `CONTRIBUTING.md` to match the
  real conventions — line length 100, Conventional Commit subjects,
  `scripts/run-all-checks.sh` as the gate, the `-W -n` docs build, and a
  `metadata_tools`-relevant example (or simply point to
  `docs/dev_guide/dev_guide_conventions.rst` and
  `dev_guide_environment.rst` instead of restating a generic version).

- **Finding (Low) — copyright/author mismatch.** `docs/conf.py:66-68` sets
  `copyright = '2025, SETI Institute'` and `author = 'SETI Institute'`, while
  `pyproject.toml` lists the author as Joe Spitale (jspitale@seti.org) and the
  README/AAREADME attribute the work to the RMS Node at SETI. This is a
  cosmetic inconsistency, not wrong. **Suggestion:** align the Sphinx `author`
  with the packaging author or a consistent institutional attribution.

- **Finding (Low) — `CODE_OF_CONDUCT.md` has an unfilled placeholder.** The
  enforcement contact is `[INSERT CONTACT METHOD]` (`CODE_OF_CONDUCT.md:63`).
  **Suggestion:** fill in the real reporting contact.

- **Finding (Low) — stale `CLAUDE.md` dependency note.** (Also flagged in the
  code critique.) `CLAUDE.md` says `pyproject.toml` runtime `dependencies` are
  "TODO" and live in `requirements.txt`; both are now populated in
  `pyproject.toml`. **Suggestion:** update the note; `CLAUDE.md` is developer-
  facing documentation and should stay in sync.

- **Finding (Low) — minor template/prose typos (non-blocking).** The
  supplemental index template describes `VOLUME_ID` as "provides a unique for a
  PDS data volume" (missing "ID", `GO_0xxx_supplemental_index.lbl:47`) and the
  `ON_CHIP_MOSAIC_FLAG` description says values are `'YES'`/`'NO'` while
  `key__on_chip_mosaic_flag` returns `'Y'` (`GO_0xxx/index_config.py:227-259`).
  These live in shipped PDS labels, so they are user-facing. **Suggestion:** fix
  the wording; verify the flag's documented value set against what the key
  function emits.

## Recommended priorities

1. **Fix the code/doc contradictions in the cloud chapter** (§5): the task-file
   `task_id` example/claim and the `metadata-task-list --output` requirement.
2. **Resolve `SunTable` in the docs** (§3/§6) in lockstep with the code
   decision: correct the class diagram and the two dev-guide chapters so they
   agree with each other and the pipeline.
3. **Fix the non-existent single-test example** in
   `dev_guide_environment.rst:74` and `CLAUDE.md`, and reconcile the CI-gate
   description with what CI and `run-all-checks.sh` actually run.
4. **Rewrite `CONTRIBUTING.md`** to reflect the project's real conventions (line
   length, Conventional Commits, the check runner, the `-W -n` docs build).
5. **Housekeeping:** Zenodo badge, `[INSERT CONTACT METHOD]`, copyright/author,
   the `currently` wording, `read-docs.sh` `-n` flag, and the two template
   typos.

## Prompt for an AI agent to fix the documentation

> You are fixing the documentation of `rms-metadata-tools` per
> `critiques/documentation_critique.md`. Do not change production code behavior;
> you may edit `.rst`/`.md` docs, docstrings, `docs/conf.py`, `CONTRIBUTING.md`,
> `CODE_OF_CONDUCT.md`, `CLAUDE.md`, `scripts/read-docs.sh`, and the two
> user-facing template typos. Follow the present `.cursor/rules/doc_*.mdc`
> standards. **Build gate:** the docs MUST build clean under BOTH
> `sphinx-build -W -b html docs docs/_build` and
> `sphinx-build -n -b html docs docs/_build` before the work is considered done;
> when you rename or move any symbol/page, update every cross-reference to it in
> the same change.
>
> Apply, in priority order:
> 1. `docs/user_guide/user_guide_cloud.rst`: change the task-file example
>    `task_id` to `"task-GO_0017"` and remove the "prefix identifies the stage"
>    sentence (match `task_list_support.make_task` and
>    `cloud/GO_0xxx/tasks.json`). In the `metadata-task-list` section, document
>    `--output` as **optional** in scan mode (default `tasks.json` in the
>    cloud/host directory) and **required** in explicit mode, matching
>    `src/metadata_tools/cli/task_list.py`.
> 2. Reconcile `SunTable`: in `docs/dev_guide/dev_guide_architecture.rst` (class
>    diagram + prose) and `dev_guide_geometry_subsystem.rst`, make the two
>    chapters agree with each other and with whatever the code decision is
>    (`Suite.add_tables` currently omits `SunTable`). If the code removes
>    `SunTable`, remove it from the diagram and prose; if it wires it in, add it
>    consistently to both chapters.
> 3. `docs/dev_guide/dev_guide_environment.rst:74` and `CLAUDE.md`: replace the
>    `Test_Index_Common::test_supplemental_index_common` example with a real
>    target (e.g. `tests/test_index_support.py::test_format_value_real`). Correct
>    the CI-gate list in `dev_guide_environment.rst` and
>    `dev_guide_conventions.rst` to match what `.github/workflows/run-tests.yml`
>    and `scripts/run-all-checks.sh` actually run.
> 4. Rewrite `CONTRIBUTING.md` to reflect real conventions: line length 100,
>    Conventional Commit subjects, `scripts/run-all-checks.sh` as the quality
>    gate, the `-W -n` docs build, and a `metadata_tools`-relevant (or
>    reference-linked) example instead of `calculate_offset`.
> 5. Housekeeping: fix or remove the Zenodo badge in `README.md`; fill
>    `[INSERT CONTACT METHOD]` in `CODE_OF_CONDUCT.md`; align `author`/copyright
>    in `docs/conf.py`; add `-n` to `scripts/read-docs.sh`; reword the
>    "currently" note in `geometry_support/formats.py`; fix the `VOLUME_ID`
>    "unique for a PDS data volume" typo and verify the `ON_CHIP_MOSAIC_FLAG`
>    documented value set in `hosts/GO_0xxx/templates/GO_0xxx_supplemental_index.lbl`.
>
> After changes, run both Sphinx builds with zero warnings and skim the rendered
> user-guide cloud page and dev-guide architecture page to confirm accuracy.
