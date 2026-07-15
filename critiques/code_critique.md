# Codebase analysis: rms-metadata-tools (`metadata_tools`)

**Generated:** 2026-07-15
**Scope:** the whole repository — every file under `src/`, `tests/`, `docs/`,
`cloud/`, `scripts/`, `.github/`, and the root packaging/config files.
**Standards applied:** the `.cursor/rules/*.mdc` files present in the repo
(`python.mdc`, `python_testing.mdc`, `filecache.mdc`, `logging.mdc`,
`dependency_management.mdc`, `environment.mdc`, `security.mdc`,
`git_workflow.mdc`, the `doc_*.mdc` set). Where a finding reinforces or
contradicts a rule it is cited by filename.

---

## Summary

This is a well-structured, mature codebase. The engine/host-config split (issue
#112, `config.py`) is clean, the geometry engine has been decomposed from a
"god module" into a cohesive `geometry_support/` package, `FCPath` is used
consistently for path I/O, `PdsLogger` is used instead of `print`, and mypy runs
in strict mode with a well-curated Ruff rule set. The test suite is hermetic and
broad. The top three priorities are: (1) **shared mutable state mutated at
runtime** in `Record.__init__` (a real reentrancy/accumulation hazard), (2) a
cluster of **committed build artifacts and stale configuration/metadata**
(`*.db` files in `src/`, a stale `CLAUDE.md` note, CI vs. `run-all-checks.sh`
drift), and (3) **dead/unwired public API** (`SunTable`) plus a scatter of
aspirational `### move to utilities` TODO markers in `util.py`. None of these
block use; they are maintainability and correctness-risk items.

---

## 1. Structure and layout

- **Finding**: Module boundaries are clear and sizes are healthy. The former
  `geometry_support.py` "god module" is now a package of focused submodules
  (`process`, `suite`, `record`, `tables`, `prep`, `masks`, `formatting`,
  `formats`, `bodies_select`), each well under the 1000-line limit
  (`python.mdc` §2). **Evidence**: `src/metadata_tools/geometry_support/`.
  **Suggestion**: none — keep this decomposition.

- **Finding**: `util.py` is the largest module (793 lines) and is a grab-bag of
  unrelated helpers (path arithmetic, text I/O, SCLK parsing, a 700-element
  statistical lookup table, angle-range estimation). It is under the 1000-line
  cap but is the least cohesive module. **Evidence**:
  `src/metadata_tools/util.py`; the embedded `NINETY_PERCENT_RANGE_DEGREES`
  table (lines 600-701) and `range_of_n_angles` (lines 565-592) exist only to
  document/regenerate a constant. **Suggestion**: Consider splitting into
  `util/paths.py`, `util/textfile.py`, `util/sclk.py`, and `util/angles.py`
  (a package), grouping the cyclic-range machinery with its lookup table.

- **Finding**: Committed database artifacts live inside the source package.
  `src/metadata_tools/metadata-index-job.db`,
  `metadata-geometry-job.db`, and `metadata-cumulative-job.db` are tracked and
  were "modified" at the start of this session; they are `rms-cloud-tasks` job
  state, not source. **Evidence**: `git ls-files | grep '\.db$'`;
  `.gitignore` line 170 even lists `metadata-*.db` (which has no effect on
  already-tracked files). **Suggestion**: `git rm --cached` the three `.db`
  files and confirm the `.gitignore` rule keeps them out. They are excluded from
  the wheel (package-data only ships `py.typed` and `templates/*.lbl`), so this
  is repo hygiene, not a distribution bug — but they are noise and cause
  spurious diffs.

- **Finding**: `.vscode/settings.json` and `.cursor/settings.json` are
  byte-for-byte identical. **Evidence**: both files. **Suggestion**: acceptable
  duplication; if desired, keep one canonical copy and document the other as a
  mirror.

## 2. Best practices alignment

- **Finding (High) — shared mutable state mutated per-record.**
  `Record.__init__` mutates the *cached, module-level* column dictionaries and
  tile dictionaries when a targeted irregular moon is encountered:
  `self.dicts['body'][self.target] = ...` writes into
  `col.get_body_summary_dict()`'s cached dict, and
  `self.body_tile_dict[self.target] = ...` writes into `col.BODY_TILE_DICT[...]`.
  **Evidence**: `src/metadata_tools/geometry_support/record.py:99-106`;
  `self.dicts['body']` is `col.get_body_summary_dict()`
  (`record.py:54`), a cached singleton built in
  `src/metadata_tools/columns/body.py:100-111`; `self.body_tile_dict` is
  `col.BODY_TILE_DICT[self.primary]` (`record.py:71`), a module-level dict from
  `columns/body.py:142-146`. **Impact**: these caches accumulate target bodies
  across observations for the life of the process, and the mutation is not
  reentrant/thread-safe. **Suggestion**: build a per-`Record` copy
  (`dict(...)` / `copy.deepcopy` of the tile list) before inserting the target,
  or key an instance-local dict, so the shared cache is never written. Add a
  test that constructs two records with different irregular-moon targets and
  asserts the shared dict is unchanged.

- **Finding (Medium) — magic domain strings hardcoded in engine code.**
  Body names are embedded as literals in the generic (host-agnostic) engine:
  `"SATURN"`, `"SATURN_MAIN_RINGS"`, `"PLUTO"`, `"CHARON"` in
  `masks.construct_excluded_mask`, and `'SUN'` in `bodies_select.get_system`.
  **Evidence**: `src/metadata_tools/geometry_support/masks.py:64-88`;
  `src/metadata_tools/geometry_support/bodies_select.py:142`. This contradicts
  `python.mdc` §2 ("NEVER hardcode magic constants") and couples the generic
  engine to specific bodies. **Suggestion**: promote these to named constants in
  `defs.py` (e.g. `RING_SHADOWER_PRIMARIES`, `SATELLITE_COMPANIONS =
  {"PLUTO": ["CHARON"]}`) or make them host-configurable, and reference the
  constants.

- **Finding (Low) — backwards-compatibility shim present without request.**
  `resolve_task_file` is documented as "Alias for `resolve_host_paths`; kept for
  backwards compatibility." `python.mdc` §2 says "NEVER include
  backwards-compatibility code unless explicitly requested." **Evidence**:
  `src/metadata_tools/cli/_host.py:89-91`. **Suggestion**: if no caller uses it,
  remove it; `vulture` (already in the dev group) should flag it as unused.

- **Finding (Low) — `exists()`/`is_file()` pre-checks instead of EAFP.**
  `filecache.mdc` §4 prefers try/except `FileNotFoundError` over an existence
  pre-check before a read. `label_support.create` guards with
  `if not filepath.is_file(): return`, and `IndexTable.__init__` guards the
  primary label with `if not self.primary_index_label_path.exists(): raise`.
  **Evidence**: `src/metadata_tools/label_support.py:34`;
  `src/metadata_tools/index_support/table.py:83`. **Impact**: for remote
  backends these add a network round-trip; low severity because the very next
  step is local template rendering, not a second remote fetch. **Suggestion**:
  where the next action reads the file, restructure to try/except; where the
  answer itself is the point (label present or not), the check is legitimate.

- **Strength**: Logging follows `logging.mdc` — the global `PdsLogger` is used
  via `com.get_logger()`, deferred `%`-formatting is used in log calls, and no
  bare `print()` appears in library code (`src/metadata_tools/common.py:25-49`
  and call sites). Note the `.cursor/rules` `python.mdc` §2 line-33 wording
  ("use the `logging` module") is superseded by the project-specific
  `logging.mdc`, which the code correctly follows.

## 3. Types and static checks

- **Strength**: mypy is strict (`pyproject.toml` `[tool.mypy] strict = true`),
  with narrowly-scoped per-module `ignore_missing_imports` overrides for the
  untyped SPICE/PDS dependency stack and the plugin-injected host modules — no
  global exclusions, matching `python.mdc` §5. `py.typed` ships.

- **Finding (Low)**: Pervasive `Any` at the `oops`/`polymath` boundary is
  unavoidable (those libraries are untyped), but a few internal signatures
  propagate `Any` further than necessary (e.g. `record.py` attributes typed
  `Any`). **Evidence**: `geometry_support/record.py:37,70-71`. **Suggestion**:
  where a value is known to be a `polymath.Boolean`/`oops.Scalar`, annotate it
  as such (already imported) to tighten the internal contract; low priority.

- **Finding (Low)**: `Record.get_backplane_key`'s docstring is accurate, but a
  test comment claims the docstring says `Returns: None` — a stale note left in
  the test. **Evidence**: `tests/test_geometry_record.py:26` vs.
  `geometry_support/record.py:108-124`. **Suggestion**: delete the stale test
  comment (test-side, so not a production change).

## 4. Testing

See the companion `tests_critique.md` for the full test-suite audit. Engine-side
observations relevant here:

- **Strength**: The default suite is hermetic — SPICE/oops and the holdings tree
  are stubbed via `tests/conftest.py::_install_fakes` and gated behind the
  `integration` / `requires_archive` markers, both registered and excluded by
  default (`pyproject.toml` `addopts`, `markers`). `filterwarnings = ["error"]`
  is set, so new warnings fail the run.

- **Finding (Medium)**: Coverage omits `cli/*`, `hosts/*`, and `bodies.py` from
  the denominator (`pyproject.toml` `[tool.coverage.run] omit`). `cli/_host.py`
  is 442 lines of non-trivial argv/subprocess/startup-script logic that *is*
  exercised by `tests/test_cli_host.py`, yet its coverage is not counted, and
  the CLI `main()` dispatchers are untested. **Suggestion**: measure
  `cli/_host.py` (remove it from `omit` or add a targeted include) so its real
  coverage is visible; leave the SPICE-driving `main()` shells excluded with
  commented `# pragma: no cover` at the seam rather than a blanket file omit
  (the file already documents this intent in the omit comment).

## 5. Performance and resource use

- **Finding (Medium) — module-level mutable caches, no documented thread-safety.**
  Several lazily-initialized global caches exist: `bodies._BODIES`
  (`bodies.py:32`), `columns/body.py` `_BODY_SUMMARY_DICT`/`_BODY_DETAILED_DICT`
  (lines 96-97), `geometry_support/formats.py` `_mission_table_cache` (line 124),
  and the `defs._translations` global (line 34). **Evidence**: cited lines.
  **Impact**: fine for the current multiprocessing-`spawn` cloud model (each
  process re-imports), but the library documents no thread-safety guarantee and
  the lazy initializers are not guarded. Combined with the §2 finding
  (per-record mutation of these caches), concurrent use within one process would
  be unsafe. **Suggestion**: document that the engine is single-threaded per
  process, and/or guard the lazy initializers; at minimum fix the §2 mutation.

- **Finding (Low)**: `IndexTable.__init__` reads the entire primary index into
  memory via `pds_table(...).dicts_by_row()` and builds a full file list; and
  `cumulative_support._cat_rows` reads every per-volume table fully into a list
  before writing. **Evidence**: `index_support/table.py:87-95`;
  `cumulative_support.py:89-96`. **Impact**: acceptable for per-volume sizes;
  the cumulative concatenation could be large. **Suggestion**: only optimize if
  cumulative memory becomes a problem (stream append via `util.append_txt_file`).

- **Strength**: `geometry_config` (and its SPICE `host_init` side effect) is
  imported lazily on first `get_geometry_config()`, so the index and cumulative
  stages never pay SPICE startup cost (`config.py:115-136`). This is a
  deliberate, well-documented performance seam.

## 6. Maintainability and extensibility

- **Finding (Medium) — `SunTable` is public API but not wired into the
  pipeline.** `SunTable` is defined (`tables.py:83-107`), exported from
  `geometry_support.__all__`, and appears in the developer-guide class diagram,
  but `Suite.add_tables` and `Suite.get_overrides` have it commented out
  (`suite.py:161,178`), `cumulative_support.create_cumulative_indexes` does not
  list it (`cumulative_support.py:176-185`), and `Record` still builds `'sun'`
  column dicts that nothing consumes (`record.py:49-61`). **Evidence**: cited
  lines. **Impact**: dead-but-public surface; confusing for extenders and for
  the docs (see `documentation_critique.md`). **Suggestion**: decide whether Sun
  tables are a supported output. If yes, wire `SunTable` into `Suite` and
  cumulative and add a template/tests; if no, remove `SunTable` and the `'sun'`
  column plumbing (or clearly mark them experimental in one place).

- **Finding (Low) — aspirational TODO markers scattered in `util.py`.**
  Numerous `### move to utilities`, `### add to FCPath?`, and `### LIB` markers
  flag code the author intended to relocate. **Evidence**:
  `util.py:113,127,142,287,310,335,366,399,438`; `tests/archive_support.py:17,34`.
  **Suggestion**: convert to tracked issues or act on them; unlinked `###`
  markers are noise (`python.mdc` §4 discourages history/aspirational comments).

- **Finding (Low) — `SKY_TILES` is defined but untested and flagged.**
  `columns/sky.py:55` carries `###TODO: not tested...`, and detailed sky tiling
  is not exercised. **Suggestion**: either test the detailed-sky path or note it
  as unsupported.

- **Strength**: The extension model is genuinely pluggable: a new host is a
  directory of config modules resolved by `set_host`, with no `sys.path` tricks
  (`config.py`, `cli/_host.py`), and the geometry column/format/label/test
  recipe is documented at the top of `formats.py` and in the dev guide.

## 7. Security and robustness

- **Strength**: `subprocess` use is safe — `shell=False`, argv built from this
  process only, with `# nosec` annotations and rationale
  (`cli/_host.py:347-349`); `bandit` runs in CI and in `run-all-checks.sh`. No
  `eval`/`exec` of user data; the former `eval`-of-column-reference was replaced
  by the explicit `_resolve_dict_ref` allow-list (`util.py:172-188`).

- **Finding (Low) — no `pip audit` / Dependabot.** `security.mdc` §2 and
  `dependency_management.mdc` §5 call for `pip audit` in CI and automated
  dependency-update tooling. **Evidence**: `.github/workflows/run-tests.yml`
  runs ruff/mypy/bandit/vulture/sphinx/pymarkdown but not `pip audit`; there is
  no `.github/dependabot.yml`. **Suggestion**: add a `pip audit` step (or a
  dedicated audit workflow) and a Dependabot config.

- **Finding (Low) — `.env` auto-load executes at import.** `__init__.py` reads
  `../../.env` and `os.path.expandvars` + `setdefault`s each value at package
  import (`__init__.py:26-37`). It is guarded to a repo-root `.env` (git-ignored)
  and is convenient for the cloud workflow, but it means importing the library
  can silently populate environment defaults. **Suggestion**: document this
  behavior in the API docstring (it is only mentioned in the user guide) and
  consider gating it behind an opt-in for library consumers who do not want
  implicit env mutation.

## 8. Dependencies and tooling

- **Finding (Medium) — CI does not run exactly the `run-all-checks.sh` set.**
  `environment.mdc` §2/§3 require CI and the local runner to run the *same* set.
  Divergences: the script enables `pyroma` (`ENABLE_PYROMA=true`,
  `run-all-checks.sh:106`) but the CI `lint` job never runs pyroma; and the
  docs/`dev_guide_conventions.rst`/`dev_guide_environment.rst` claim
  `ruff format --check` "is run by scripts/run-all-checks.sh" while the script
  ships `ENABLE_RUFF_FORMAT=false` (`run-all-checks.sh:102`), so it is scheduled
  but disabled, and CI does not run it either. **Evidence**:
  `.github/workflows/run-tests.yml:30-52` vs. `scripts/run-all-checks.sh:101-108`.
  **Suggestion**: reconcile the three surfaces — either add `pyroma` (and, if
  intended, `ruff format --check`) to CI and enable them in the script, or drop
  them from the script; then fix the docs to match.

- **Finding (Low) — `requirements.txt` policy.** `dependency_management.mdc` §1
  says a kept `requirements.txt` should contain only `-e .`. This repo's file
  is `-e .[dev,cloud]` (a convenience for full-environment setup). **Evidence**:
  `requirements.txt`. **Impact**: minor; runtime deps are correctly declared in
  `pyproject.toml`. **Suggestion**: either reduce it to `-e .` or rename/comment
  it as a dev-environment convenience so its role is unambiguous.

- **Finding (Low) — PyPI publish uses token auth, not Trusted Publishers.**
  `publish_to_pypi.yml` authenticates with `secrets.PYPI_API_TOKEN` and does not
  set `permissions: id-token: write`. **Evidence**:
  `.github/workflows/publish_to_pypi.yml:35-37`. **Suggestion**: consider
  migrating to PyPI Trusted Publishers (OIDC) to remove the long-lived token;
  low priority since token auth is valid.

- **Strength**: Tool configuration is consolidated in `pyproject.toml` (ruff,
  mypy, pytest, coverage, bandit, vulture, pymarkdown, setuptools_scm) with no
  stale `.flake8`/`.coveragerc`/`setup.cfg`, matching
  `dependency_management.mdc` §6.

## 9. Technical debt and risk

- **Finding (Low) — stale `CLAUDE.md` note about dependencies.** `CLAUDE.md`
  states "`pyproject.toml` runtime `dependencies` are still `\"TODO\"`; the
  actual runtime requirements currently live in `requirements.txt`." This is no
  longer true: `pyproject.toml` `[project].dependencies` is fully populated and
  `requirements.txt` is just `-e .[dev,cloud]`. **Evidence**:
  `CLAUDE.md` "Conventions → Dependencies" note vs. `pyproject.toml:11-23`.
  **Suggestion**: update the note.

- **Finding (Low) — mixed smoothed/unsmoothed gap logic in
  `_get_range_mod360`.** The function computes `wdiffs = smooth(diffs, width)`
  "to remove noise from subsampling," but then locates the gap with
  `gap_index = np.argmax(diffs)` on the *unsmoothed* diffs and only reads the
  threshold value as `diff_max = wdiffs[gap_index]`. **Evidence**:
  `util.py:768-775`. **Impact**: the smoothing influences the confidence
  threshold but not gap *selection*, which may be intended but reads as a latent
  inconsistency; behavior is covered by tests only for `width=1`. **Suggestion**:
  confirm the intent in a comment, or use `np.argmax(wdiffs)` if the smoothed
  gap was meant to drive selection; add a `width>1` test either way.

- **Finding (Low) — `PathAction` normalizes only the volume positional.**
  `get_common_args` applies `action=PathAction` to `volume_arg` but not to
  `metadata_arg`/`output_arg`, so redundant-slash normalization is inconsistent
  across positional path arguments. **Evidence**: `common.py:104-115`.
  **Suggestion**: apply `PathAction` uniformly, or document that only the volume
  tree is normalized.

## 10. Packaging and distribution

- **Strength**: Metadata is complete — classifiers, `project.urls`
  (Homepage/Documentation/Repository/Source/Issues), Apache-2.0 license,
  `requires-python = ">=3.11"`, keywords, `py.typed`, and `setuptools_scm`
  single-source versioning. `packages.find` scopes to `src/`, and
  `package-data` ships `py.typed` and the `templates/*.lbl` fragments needed at
  runtime (`pyproject.toml:73-88`). `pyroma` runs locally to guard this.

- **Finding (Low)**: `requires-python = ">=3.11"` but the classifier declares
  only 3.11–3.13, and `[tool.ruff] target-version = "py311"` — all consistent;
  CI matrix is 3.11/3.12/3.13. No action. (Recorded as a positive consistency
  check.)

- **Finding (Low)**: The committed `*.db` artifacts (see §1) are the only
  distribution-hygiene smell; they are excluded from the wheel by `package-data`
  scoping but should not be in the repo.

---

## Recommended priorities

1. **Fix the shared-mutable-state mutation in `Record.__init__`** (§2, High):
   stop writing targeted moons into the cached `col.get_body_summary_dict()` /
   `col.BODY_TILE_DICT` dicts; use per-record copies. Add a regression test.
2. **Reconcile CI ↔ `run-all-checks.sh` ↔ docs** (§8, Medium) and add
   `pip audit`/Dependabot (§7): make the three check surfaces agree, then update
   the developer-guide claims about which gates run.
3. **Remove committed `*.db` artifacts and refresh stale notes** (§1, §9):
   `git rm --cached` the three job databases; update the `CLAUDE.md` dependency
   note.
4. **Resolve the `SunTable` dead-API question** (§6, Medium): wire it in or
   remove it (plus the unused `'sun'` column plumbing), and sync the docs.
5. **Make `cli/_host.py` coverage visible** (§4/§18) and clear the `util.py`
   TODO markers (§6).

---

## Prompt for an AI agent to apply these fixes

> You are fixing `rms-metadata-tools` (`metadata_tools`). Apply the findings in
> `critiques/code_critique.md` **without changing observable behavior except
> where a finding is a bug fix**. Follow the repo's `.cursor/rules/*.mdc`
> standards (Python 3.11+, line length 100, single-quote `ruff format`, mypy
> strict, Google-style docstrings with `Parameters:`, `FCPath` for all paths,
> `PdsLogger` for logging). Work on a `bugfix/` or `feature/` branch with
> Conventional Commit messages.
>
> Priority order:
> 1. In `src/metadata_tools/geometry_support/record.py:99-106`, stop mutating
>    the shared cached dicts (`col.get_body_summary_dict()` and
>    `col.BODY_TILE_DICT[...]`): build per-`Record` copies before inserting the
>    target body. Add a hermetic test that two records with different
>    irregular-moon targets leave the shared dicts unchanged.
> 2. Reconcile `.github/workflows/run-tests.yml` with
>    `scripts/run-all-checks.sh` so both run the same gate set; add a `pip audit`
>    step and a `.github/dependabot.yml`. Update the conflicting claims in
>    `docs/dev_guide/dev_guide_environment.rst` and `dev_guide_conventions.rst`.
> 3. `git rm --cached src/metadata_tools/metadata-*.db`; verify `.gitignore`
>    keeps them untracked. Update the stale dependency note in `CLAUDE.md`.
> 4. Decide `SunTable`'s status (`geometry_support/tables.py`,
>    `suite.py:161,178`, `cumulative_support.py:176-185`, `record.py:49-61`):
>    wire it in with template + tests, or remove it and the unused `'sun'`
>    column plumbing; sync `docs/dev_guide/dev_guide_architecture.rst`.
> 5. Promote the hardcoded body strings in
>    `geometry_support/masks.py` and `bodies_select.py` to named constants in
>    `defs.py`. Remove the `resolve_task_file` back-compat alias if unused.
>    Clear or ticket the `### move to utilities` markers in `util.py`.
>
> After each change, run `scripts/run-all-checks.sh` (or `ruff check`, `mypy src
> tests`, `pytest`) and ensure everything passes. Do not modify test
> expectations to hide a real defect.
