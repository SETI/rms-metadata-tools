# Codebase analysis: rms-metadata-tools

**Generated:** 2026-06-15
**Scope:** entire repository — all of `src/metadata_tools/` (core engine, `column/`, `hosts/GO_0xxx/`), packaging/config files, CI workflows, and GCP/cloud scripts. Every Python source file was read in full; `.lbl` templates, `*.db`, `*_tasks.json`, `cprofile.txt`, and `log.txt` were inspected as committed artifacts.
**Authoritative rules:** `.cursor/rules/python.mdc`, `filecache.mdc`, `logging.mdc`, `dependency_management.mdc`, `environment.mdc`, `security.mdc`, `git_workflow.mdc`.

## Summary

The package is functional for its one wired-up host (Galileo SSI) but is **not in a releasable state** and violates many of its own `.cursor/rules`. Three issues are critical and should be fixed before anything else: (1) `pyproject.toml` declares `dependencies = ["TODO"]`, which makes `pip install .` / `pip install -e ".[dev]"` impossible — this breaks CI, ReadTheDocs, and any PyPI install; (2) `ruff check src tests` reports **293 errors**, so the lint gate that `environment.mdc` calls the single source of truth is red; (3) the dynamically `exec()`-ed `column/COLUMNS_*.py` files and the `'detailed'` geometry path reference names that do not exist (`col.RING_SUMMARY_DETAILED`, `col.BODY_SUMMARY_DETAILED`, `col.BODYX`), which are latent `AttributeError`s. Pervasive secondary problems: builtin shadowing (`format`, `id`, `type`, `dict`, `min`, `max`), no type annotations anywhere, `print()`/`dbprint()` in library code, exception-based control flow, and committed runtime artifacts.

Top priorities: **fix packaging metadata so the package installs**, **get the lint/type gate green**, and **fix the broken dynamic-exec / detailed-geometry code paths**.

---

## Status update (2026-06-15, branch `ai_rewrite`)

The analysis above is the original point-in-time review. Progress since:

**Resolved**

- **§8 (Critical) packaging deps** — `dependencies = ["TODO"]` replaced with the real
  runtime requirements; `description`/`keywords` filled in; `requirements-cloud.txt` merged
  into a `cloud` optional-dependencies group and removed; `requirements.txt` reduced to
  `-e .[dev,cloud]`. `pip install -e ".[dev,cloud]"` works in a clean venv; pyroma rates the
  metadata 10/10.
- **§10 (High) committed runtime artifacts** — the `metadata-*-job.db` SQLite files,
  `cprofile.txt`, etc. under `hosts/GO_0xxx/` were removed from version control.
- **§1 (High) exec()-loaded columns / §3 F821** — `column/COLUMNS_*.py` are now a real
  `metadata_tools/columns/` package (`ring/body/sky/sun.py`) with explicit imports; the
  `exec()` loop is gone and the `BODIES` oops registry moved to `metadata_tools/bodies.py`.
  The package `__init__` re-exports the same names explicitly (no `import *`). **All 40 F821
  errors are resolved**; the assembled column data is unchanged (the move was byte-identical).
- **§10 (Critical) packaging data** — **fully resolved**. The column `.py` files already shipped
  (because `columns/` is a real package); `[tool.setuptools.package-data]` now also declares
  `templates/*.lbl` for the `metadata_tools` and `hosts.GO_0xxx` packages, so all 12 `.lbl`
  templates appear in both the wheel and the sdist (verified via `python -m build` + zip/tar
  inspection). The dangling `py.typed` package-data entry (which named a non-existent marker
  file — see §3) was removed rather than faked, since the package is not yet fully annotated.
  pyroma still rates the metadata 10/10.
- **§7 / §9 (High) detailed-geometry `AttributeError`s** — **resolved**. `Record.__init__` in
  `geometry_support.py` now selects `col.RING_DETAILED_DICT` / `col.BODY_DETAILED_DICT` on the
  detailed path (the `*_SUMMARY_DETAILED` names never existed) and substitutes `defs.BODYX`
  (not the non-existent `col.BODYX`). Confirmed `level` is only ever `'summary'`/`'detailed'`.
  Summary-path output is unchanged. Added `tests/test_geometry_columns_contract.py`: a hermetic
  AST guard asserting every `col.<NAME>` in `geometry_support` is exported by the `columns`
  package `__all__` — it reproduced the original failure and blocks regressions, with no SPICE
  import. (The `eval()` in `util.replace` and the broader `BODYX` placeholder mechanism remain
  open — only the bad attribute references were fixed.)
- **§1 (High) module size** — **resolved**. `geometry_support.py` (1654 lines) was split into a
  `geometry_support/` package of ten modules, every file < 500 lines (largest is `record.py` at
  ~300): `formats.py` (FORMAT_DICT/ALT_FORMAT_DICT/MISSION_TABLE), `masks.py`
  (`construct_excluded_mask`, config-free), `formatting.py` (`formatted_column`/`circle_coverage`,
  config-free), `prep.py` (`prep_row`/`append_body_prefix`), `bodies_select.py`
  (`inventory`/`select_bodies`/`get_system`/`get_primary`/`obs_excluded`), `record.py`
  (the `Record` class), `tables.py` (the five table classes), `suite.py` (`Suite`), and
  `process.py` (`get_args`/`process_tables`). The five state-light helpers became module-level
  free functions (directly unit-testable without a SPICE-backed `Record`); `Record` keeps the
  orchestration methods. The public import surface is unchanged — `import
  metadata_tools.geometry_support as geom` still exposes `FORMAT_DICT`, `Record`, the table
  classes, `Suite`, `get_args`, `process_tables` via the package `__init__`. The extraction was
  mechanical and output-preserving: `FORMAT_DICT`/`ALT_FORMAT_DICT` are byte-identical and the
  latent correctness bugs (`prep_row` target reuse, `construct_excluded_mask` dead branch) were
  **moved verbatim**, not fixed, so the change is reviewable as pure structure. Verified by the
  hermetic import smoke test (`len(FORMAT_DICT) == 52`, all public names present), the updated
  `tests/test_geometry_columns_contract.py` (now globs every module in the package), and a net
  ruff reduction (68 → 28 findings, no new finding categories) across the extracted code. See
  `plans/plan1_split_geometry_support.md`.
- **§1 (cont.) all engine modules now < 500 lines** — **resolved**. Beyond the
  `geometry_support` split, the two other oversized modules were split mechanically
  (output-preserving, public import surface unchanged): `util.py` (802 →
  `util.py` ≈420 + `util_ranges.py` + `util_textfiles.py`, re-exported) and
  `index_support.py` (623 → `index_support.py` ≈450 + `index_formats.py`, the five
  pure column/format statics moved to free functions). `find src/metadata_tools
  -name '*.py' | xargs wc -l` confirms every file is now < 500 lines.
- **§4 (Critical) the suite now exercises the library** — **resolved**. A hermetic
  unit layer (`tests/conftest.py` import shim + 16 test modules) imports and calls
  the engine with no SPICE kernels and no `$RMS_METADATA`/`$RMS_VOLUMES`. `pytest`
  reaches **93.1%** coverage of the host-agnostic engine (`fail_under = 90` now
  genuinely met, where it was ~0% before). The SPICE/GCP-only seams
  (`hosts/*`, `bodies.py`) are excluded from the denominator with documented
  `omit` entries; SPICE-bound constructors are covered via monkeypatching, not
  blanket pragmas. Ten code defects are pinned by tests (four as strict `xfail`
  asserting intended behavior, the rest as characterization tests) — see
  `critiques/final_report.md` for the full list and `plans/plan2_test_suite.md`.
- **§2/§3 — partially**: `util.replace`/`replacement_dict`/`replacement_fn` are now
  type-annotated and the `dict` builtin shadowing in them is fixed; mypy is clean on the new
  `columns`/`bodies` package and its tests.
- **§4 — partially**: new hermetic pytest tests (`tests/test_util_replace.py`,
  `tests/columns/`) import and exercise library code (templating helpers + column assembly) —
  the first real `src/` coverage. A SPICE-gated `integration` marker was added and excluded
  from the default run.
- **Dev tooling** — bandit/vulture enabled with config; the unused IPython reference removed;
  author/maintainer set to Joe Spitale.

**Still open (deliberately out of scope of the changes so far)**

- **§7 / §9** — the `eval()` in `util.replace` and the `BODYX` placeholder mechanism are
  unchanged. The columns refactor deliberately preserved the existing tuple data
  representation, so these are untouched. (The latent
  `col.RING_SUMMARY_DETAILED`/`BODY_SUMMARY_DETAILED`/`col.BODYX` `AttributeError`s are now
  fixed — see Resolved above.)
- **§9** — the remaining correctness bugs are **not fixed**, but are now **pinned by tests**
  (no production code changed): `_get_null_value` `continue`-vs-`break`, `append_txt_file`
  double-write, `add_by_base` carry, and `obs_excluded` short-circuit are strict `xfail`
  tests; `_prep_row` last-column override, `construct_excluded_mask` dead branch, and a newly
  found `prep_row` tuple-tiles `TypeError` are characterization tests. `_create_index`
  `unused`/loop-scope remains latent (its walk is exercised for coverage but the single-close
  intersection is not yet asserted). Full catalog in `critiques/final_report.md`.
- **§1** — `geometry_support.py` split into a `geometry_support/` package is **done** (see
  Resolved above). The companion hermetic-test-suite plan (≥90% coverage with no SPICE/holdings)
  is in `plans/plan2_test_suite.md`.
- **Testing/tooling (improved)** — the default test run is now hermetic: `pytest` deselects the
  `integration` (SPICE/oops) and new `requires_archive` (`$RMS_METADATA` holdings) markers, and
  `scripts/run-all-checks.sh -i/--integration` opts those back in. `unittester_support` no longer
  reads env vars at import, so collection succeeds without the holdings tree. The hermetic unit
  layer added since (see Resolved §4 above) now brings engine coverage to 93.1%, above the
  configured `fail_under = 90`.
- **§3** — the rest of the library remains unannotated; mypy is not green repo-wide.
- **§2** — builtin shadowing in other `util.py`/`geometry_support.py` functions (`id`,
  `format`, `type`, …) and the remainder of the original 293 ruff errors persist (the 40 F821
  are fixed).

---

## 1. Structure and layout

- **Finding (High):** The `column/COLUMNS_*.py` files masquerade as importable modules (each has top-of-file `import` statements) but are actually loaded via `exec(open(file).read())` in `columns.py:26-28`. They depend on names injected by the exec'ing namespace (`BODIES`, `np`, `util`) that they never import themselves. **Evidence:** `columns.py:24-28`; `ruff check src/metadata_tools/column --select F821` reports 40 undefined-name errors (`COLUMNS_BODY.py:85 BODIES`, `COLUMNS_RING.py:132 np`, `COLUMNS_RING.py:95 util`). **Suggestion:** Convert these into real modules: add the missing `import numpy as np`, `import metadata_tools.util as util`, and an explicit `from metadata_tools.columns import BODIES` (or pass `BODIES` in as a function argument), then replace the `exec()` loop with normal imports or an explicit registry function. This removes the F821 errors and makes the data analyzable by mypy/ruff.
- **Finding (High):** Module size. `geometry_support.py` is 1654 lines, exceeding the 1000-line cap in `python.mdc` §2. **Evidence:** `geometry_support.py`. **Suggestion:** Split into e.g. `geometry/record.py` (the `Record` class), `geometry/tables.py` (`InventoryTable`/`SkyTable`/`SunTable`/`RingTable`/`BodyTable`/`Suite`), and `geometry/formats.py` (`FORMAT_DICT`/`ALT_FORMAT_DICT`).
- **Finding (Medium):** Host config modules are imported as **top-level** modules (`import host_config`, `import index_config`, `import geometry_config`) rather than package-qualified, so code only works when CWD is the host directory. **Evidence:** `index_support.py:15-16`, `geometry_support.py:20`, `GO_0xxx_index.py:31`. **Suggestion:** This is an intentional plugin pattern, but document it explicitly and consider an import shim that adds the host dir to `sys.path` in one place rather than relying on the user's CWD and scattered `sys.path.append('')` calls (`*_cloud.py:24-25`).
- **Finding (Medium):** Dead/commented-out code throughout. **Evidence:** `geometry_support.py:520, 1191-1196, 1359-1362, 1481-1489`; `geometry_config.py:209-225`; `COLUMNS_*` commented column rows; `index_config.py:109, 222, 240`. **Suggestion:** Delete; rely on git history. `python.mdc` §4 forbids history/cruft comments.
- **Finding (Medium):** `get_volume_id()` is duplicated verbatim in `host_config.py:22-33` and `geometry_config.py:177-188`. **Evidence:** both files. **Suggestion:** Define once (e.g. in `host_config`) and have `geometry_config` import it (DRY, `python.mdc` §2).

## 2. Best practices alignment

- **Finding (High):** Builtin shadowing is pervasive, violating `python.mdc` §1. `ruff` counts 13×A002 + 11×A001. **Evidence:** `format` as a variable in `geometry_support.py:405, 723-727, 912-925` and `index_support.py:299, 322, 351, 367-394`; `id` in `util.py:276` and `geometry_support.py:1020`; `type` in `common.py:24-38` and `util.py:63-83`; `dict` in `util.py:244-246, 251-262` and `geometry_config.py:196-207`; `min`/`max` in `unittester_support.py:51`. **Suggestion:** Rename to `fmt`, `obs_id`, `type_`/`index_type`, `mapping`, `min_val`/`max_val`.
- **Finding (High):** Library code prints to stdout/stderr instead of logging, violating `logging.mdc`. **Evidence:** `util.py:29` (`print(... file=sys.stderr ...)` in `dbprint`), and `common.py:229` calls `util.dbprint(...)` from `Table.write` — a debug line shipped in production. Many `print()` calls also live in tests. **Suggestion:** Delete `dbprint` and its call site; route any needed output through `com.get_logger()` with `%`-style deferred formatting per `logging.mdc` §2.
- **Finding (Medium):** Exception-based control flow instead of explicit checks (`python.mdc` §1). **Evidence:** `index_support.py:214-226` uses nested `try/except KeyError` / `except AttributeError` to look up key functions; `index_support.py:553-557` and `cumulative_support.py:74-77` use `try/except (IndexError|FileNotFoundError)` for normal flow. **Suggestion:** Use `globals().get(fn_name)` / `hasattr(config, fn_name)` and `list(...)` length checks.
- **Finding (Medium):** `raise FileNotFoundError(image_path)` without `from err` discards context (`python.mdc` §2; ruff B904). **Evidence:** `index_config.py:111-112`. **Suggestion:** `raise FileNotFoundError(image_path) from None` (intentional) or `from err`.
- **Finding (Medium):** `open()` without `encoding=` and bypassing `FCPath`. **Evidence:** `common.py:90` (`open(task_file, "w")`), `util.py:443` (`open(Path(filespec.as_posix()), "a")`). **Suggestion:** Use `FCPath(task_file).open("w")` / `fcpath.open("a")` per `filecache.mdc` §3c, or at minimum pass `encoding="utf-8"`.
- **Finding (Low):** `import math` inside a function body (`util.py:461`); imports not grouped/sorted (26×I001 from ruff). **Suggestion:** Move all imports to the top in the three sorted groups (`python.mdc` §2); run `ruff check --fix`.
- **Finding (Low):** `%`-formatting used where `python.mdc`/UP031 prefer f-strings for *non-logging* string building (20×UP031). **Evidence:** `index_support.py:94`, `common.py:32,38`, etc. **Suggestion:** Convert non-logging `%` formats to f-strings; keep `%`-style only inside `logger.*()` calls.

## 3. Types and static checks

- **Finding (High):** Essentially **no type annotations** in the core library, contradicting `python.mdc` §5 ("annotate all function/method parameters and return values") and the `[tool.mypy] strict = true` setting in `pyproject.toml`. **Evidence:** `util.py`, `common.py`, `index_support.py`, `geometry_support.py`, `cumulative_support.py` — only the `*_cloud.py` `process_task` functions are annotated. **Suggestion:** Add annotations module-by-module starting with public entry points (`process_index`, `process_tables`, `create_cumulative_indexes`, `get_args`) and the `Table`/`Record`/`Suite` constructors. Until then `mypy --strict src` cannot pass.
- **Finding (High):** `py.typed` is declared in packaging (`pyproject.toml [tool.setuptools.package-data] "metadata_tools" = ["py.typed"]`) but the marker file **does not exist**. **Evidence:** `ls src/metadata_tools/py.typed` → not found. **Suggestion:** Either create an empty `src/metadata_tools/py.typed` (only once the package is actually typed) or remove the declaration.
- **Finding (High):** `ruff check src tests` → **293 errors** (W291 51, F821 40, PT009 35, I001 26, E501 26, UP031 20, A002 13, W293 12, A001 11, F401 10, …). The lint gate is red, so CI's `lint` job fails. **Evidence:** ruff run, 2026-06-15. **Suggestion:** Triage in this order: auto-fix the 76 fixable (whitespace, import sort, `list()` comprehensions), fix F821 by de-`exec()`-ing the column files (§1), then the naming/format rules.
- **Finding (Medium):** Docstrings exist on most functions (good) but many are wrong or templated — see §9.

## 4. Testing

(Full detail in `tests_critique.md`.) Summary for this report:

- **Finding (Critical):** The test suite does not exercise the library. `tests/test_*.py` only read pre-generated `.lbl` files from `$RMS_METADATA`; they never `import metadata_tools`. Coverage of `src/` is effectively ~0%, yet `pyproject.toml` sets `fail_under = 90` and `--cov=src`. **Suggestion:** Add unit tests that import and call the pure functions in `util.py` (`add_by_base`, `rebase`, `sclk_*`, `get_volume_glob`, `_get_range_mod360`) and the formatting logic in `index_support.py`.
- **Finding (High):** Host tests under `src/metadata_tools/hosts/GO_0xxx/tests/` are never collected (`testpaths = ["tests"]`), so they are dead. **Suggestion:** Decide whether host tests run in CI; if so add their path to `testpaths`.

## 5. Performance and resource use

- **Finding (Medium):** `module-level mutable global` `task_list = []` in `common.py:50`, mutated by `add_task()` and read by the `task_source()` generator. Not thread-safe and persists across calls. **Evidence:** `common.py:50-78`. **Suggestion:** Document single-threaded use, or encapsulate in a `TaskQueue` object passed explicitly (the cloud workers already pass `task_source=com.task_source`).
- **Finding (Low):** `meshgrids()` rebuilds the `MODE_SIZES` dict on every call (`geometry_config.py:124-135`). **Suggestion:** Hoist to a module constant.
- **Finding (Low):** `cumulative_support.py:158-181` issues eight nearly identical `_cat_rows(...)` calls. **Suggestion:** Drive from a list of `(TableClass, level)` tuples.

## 6. Maintainability and extensibility

- **Finding (High):** Two entry points diverge in behavior. `GO_0xxx_geometry.py:50-54` hardcodes `selection="S", exclude=['GO_0999']` while `GO_0xxx_geometry_cloud.py:44-50` reads `config.selection`/`config.exclude`. **Evidence:** both files vs. `geometry_config.py:18-19`. **Suggestion:** Have the local script read from `config` too, so local and cloud stay consistent.
- **Finding (Medium):** `*_cloud.py` access the private attribute `worker._data` (`GO_0xxx_index_cloud.py:66-68`, `GO_0xxx_geometry_cloud.py:78-80`). **Suggestion:** Use a public accessor from `rms-cloud-tasks`; relying on `_data` will break on upstream refactors.
- **Finding (Medium):** Class docstrings are misplaced. In `geometry_support.py:1066-1067, 1101-1102, 1131-1132, 1161-1162, 1201-1202` the `"""..."""` string sits **before** the `class` statement, so it is a no-op expression and the classes (`InventoryTable`, `SkyTable`, `SunTable`, `RingTable`, `BodyTable`) have **no docstring**. **Suggestion:** Move each string to the first line inside the class body.

## 7. Security and robustness

- **Finding (High):** `eval()` on template-derived strings. **Evidence:** `util.py:210` (`lrep[i] = eval(lrep[i])` inside `replace()`), reachable from column definitions like `util.replacement_fn("defs.RING_SYSTEM_RADII", defs.BODYX)` (`COLUMNS_RING.py:94-96`). `security.mdc` flags `eval`. **Suggestion:** Replace with an explicit lookup (e.g. resolve `dict_name["key"]` via `getattr(defs, name)[key]`) rather than evaluating arbitrary expressions.
- **Finding (Medium):** `assert` used for runtime validation (disabled under `python -O`). **Evidence:** `index_support.py:232` (`assert value is not None, ...`) and `index_support.py:376` (`assert len(value) == count`). **Suggestion:** Raise explicit exceptions. Note also that line 232's assert is effectively dead — line 229-230 already replaces `None` with `nullval`.
- **Finding (Low):** GCP startup scripts embed a service-account email and personal bucket paths. **Evidence:** `gcp_index_config.yml:5`, `gcp_index_startup.sh:24-26`. Not secrets, but couples published code to one person's infra. **Suggestion:** Parameterize via env vars.

## 8. Dependencies and tooling

- **Finding (Critical):** `pyproject.toml` runtime dependencies are a placeholder: `dependencies = ["TODO"]` (line 11-12), plus `description`, `keywords`, and `[project.scripts]` are all `TODO`. This makes `pip install .` and `pip install -e ".[dev]"` fail (pip tries to resolve a package named `TODO`). **Evidence:** `pyproject.toml:8,12,21,89`; the real deps live only in `requirements.txt`/`requirements-cloud.txt`, contradicting `dependency_management.mdc` §1 (pyproject is the single source of truth). **Suggestion:** Move the real runtime deps (numpy, rms-oops, rms-filecache, rms-pdslogger, rms-julian, rms-pdsparser, rms-cloud-tasks, rms-pdstable, rms-vicar, rms-pdstemplate, rms-textkernel, fortranformat, cspyce, json-stream) from `requirements.txt` into `[project.dependencies]` with minimum versions; reduce `requirements.txt` to `-e .`.
- **Finding (Medium):** CI Python matrix (`run-tests.yml`: 3.10–3.13) matches `requires-python = ">=3.10"`, but `python.mdc` says "Minimum Python version 3.11" and `[tool.ruff] target-version = "py310"`. **Suggestion:** Reconcile the three; pick one minimum and apply it to `requires-python`, ruff `target-version`, and the rule text.
- **Finding (Medium):** `run-tests.yml` lint job runs `mypy src tests`, but the local `scripts/run-all-checks.sh` defaults `ENABLE_MYPY` inconsistently (the docstring says default false, the code sets it true) — and mypy cannot currently pass (§3). **Suggestion:** Make CI and the script enable exactly the same gates (`environment.mdc` §2), and don't enable mypy in CI until the code is annotated.
- **Finding (Low):** Stale tool config: `[tool.bandit]`/`[tool.vulture]` are commented out while `run-all-checks.sh` references them; `flake8` is still in `requirements.txt` though ruff replaces it. **Suggestion:** Remove `flake8`; keep the commented tool blocks only if intended to be enabled soon.

## 9. Technical debt and risk

- **Finding (High):** Latent `AttributeError`s on the geometry `'detailed'` path. `Record.__init__` (`geometry_support.py:167-172`) references `col.RING_SUMMARY_DETAILED` and `col.BODY_SUMMARY_DETAILED`, but `COLUMNS_RING.py`/`COLUMNS_BODY.py` define `RING_DETAILED_DICT`/`BODY_DETAILED_DICT` (and `RING_SUMMARY_DICT`/`BODY_SUMMARY_DICT`) — the `*_SUMMARY_DETAILED` names do not exist. Likewise `geometry_support.py:215-216` uses `col.BODYX`, which is never defined in the `columns` namespace (only `defs.BODYX` exists). **Evidence:** grep of `col.` references vs. names defined in `column/`. **Suggestion:** Fix the names (`col.RING_DETAILED_DICT`, `col.BODY_DETAILED_DICT`, `defs.BODYX`) and add a test that constructs a detailed `Record` so the path is exercised.
- **Finding (High):** Logic bug in `IndexTable._get_null_value` (`index_support.py:291-295`): the loop assigns `nullval := old_lookup(key)` and `continue`s on truthy, so it returns the null value of the **last** matching key rather than the first; `continue` should be `break`. **Evidence:** lines 291-295. **Suggestion:** `break` on first truthy value.
- **Finding (High):** `_create_index` "unused columns" accumulation never works: `unused = None` is reset **inside** the per-directory `walk` loop (`index_support.py:536`), and `logger.close(force=True)` plus the task-file write are also inside the loop (lines 562-569). **Evidence:** indentation at 536/562-569. **Suggestion:** Initialize `unused` before the loop; move the close/write/warn after it.
- **Finding (Medium):** `_construct_excluded_mask` (`geometry_support.py:872-879`) has unreachable code: `if np.any(excluded): return excluded` precedes `if np.all(excluded): return True` (all-True implies any-True), and the `#!!!!` comment admits the gridless case is unhandled. **Suggestion:** Resolve the gridless-backplane TODO and remove the dead branch.
- **Finding (Medium):** `_prep_row` reuses the loop variable `target` as both the function parameter and a per-column local (`geometry_support.py:710`), and builds the `override` dict (lines 736-739) from whatever `null_value`/`valid_minimum`/`valid_maximum` happened to survive the last column iteration. **Suggestion:** Use distinct names and build the override per column.
- **Finding (High):** `add_by_base` (`util.py:284-301`) drops a carry. When the carry into a position plus that position's `(x_digit + y_digit) % base` equals `base`, the result digit is left equal to `base` and the extra carry is never propagated. **Evidence (reproduced):** `add_by_base([9,9],[0,1],[10,10])` returns `[0, 10, 0]`; the correct base-10 result is `[1, 0, 0]`. This feeds `_spacecraft_clock_stop_count_from_label` (`host_config.py:88`), so a stop SCLK can be malformed for exposures that land on a tick boundary. **Suggestion:** add the incoming carry before taking `% base`, or re-normalize digits in a final carry pass; add a unit test covering the chained-carry case.
- **Finding (Medium):** `append_txt_file` (`util.py:417-444`) writes the file when it doesn't exist (line 423-424) but does **not** `return`, then falls through and appends again — duplicating content on first write. **Evidence (reproduced):** appending `['lineA','lineB']` to a new path yields `lineA\nlineB\nlineA\nlineB\n`. **Suggestion:** `return` after the `write_txt_file` call.
- **Finding (Low):** Typo `'Mulitple index files found'` (`geometry_support.py:1279`) and many docstring typos (`messaage`, `degugging`, `occurence`, `exluded`, `dicstionary`, `corresopnding`).

## 10. Packaging and distribution

- **Finding (Critical):** Non-Python package data will be missing from the wheel. The runtime `exec()`-loads `column/COLUMNS_*.py` and reads `templates/*.lbl` and `hosts/*/templates/*.lbl`, but `[tool.setuptools.package-data]` lists only `py.typed`. **Evidence:** `pyproject.toml:` package-data block; `defs.py:12-13` (`COLUMN_DIR`, `GLOBAL_TEMPLATE_PATH`), `label_support.py`. **Suggestion:** Add `"*.lbl"` (and confirm `*.py` data) to package-data, or use `include-package-data = true` with a `MANIFEST.in`. Verify with `python -m build` then inspect the wheel.
- **Finding (High):** Generated runtime artifacts are committed under `hosts/GO_0xxx/`: `metadata-*-job.db` (SQLite), `metadata-*_in_queue_original.json`, `index_tasks.json`/`geometry_tasks.json`/`cumulative_tasks.json`, `cprofile.txt` (1161 lines of profiler output), `log.txt` (639 lines). **Evidence:** `git ls-files`. **Suggestion:** Remove from version control and add patterns to `.gitignore`; they would otherwise ship in the sdist.
- **Finding (Medium):** `[project.scripts]` is commented out (`pyproject.toml:89`), so there are no console entry points; users must run host scripts by path. **Suggestion:** Decide whether to expose CLIs and wire them up, or document the by-path invocation.
- **Finding (Low):** PyPI publish uses a long-lived `PYPI_API_TOKEN` (`publish_to_pypi.yml`). **Suggestion:** Prefer PyPI Trusted Publishers (OIDC) per modern packaging guidance.

## Recommended priorities

1. **Make the package installable and the gate green:** replace `dependencies = ["TODO"]` with real deps, add `*.lbl` to package-data, create/remove `py.typed`, then run `ruff check --fix` and triage the rest of the 293 errors (start by de-`exec()`-ing `column/`).
2. **Fix the latent correctness bugs:** the `*_SUMMARY_DETAILED`/`col.BODYX` names (detailed geometry), `_get_null_value` `break`, `_create_index` `unused`/loop-scope, and `append_txt_file` double-write.
3. **Add real unit tests + type annotations** so `--cov=src` (fail_under 90) and `mypy --strict` become meaningful, then remove committed runtime artifacts and delete `dbprint`/dead code.

---

## Prompt for an AI agent to apply these fixes

> You are working in the `rms-metadata-tools` Python repository (src-layout package `metadata_tools`, rules in `.cursor/rules/`). Apply the fixes below **without changing observable table/label output**. After each group, run `ruff check src tests` and (once types exist) `mypy src tests`; both must pass before you finish.
>
> 1. **Packaging (`pyproject.toml`):** Replace `dependencies = ["TODO"]` with the real runtime dependencies currently listed in `requirements.txt`/`requirements-cloud.txt` (numpy>=2.3, rms-oops, rms-filecache, rms-pdslogger, rms-julian, rms-pdsparser, rms-cloud-tasks, rms-pdstable, rms-vicar, rms-pdstemplate, rms-textkernel, fortranformat, cspyce, json-stream), each with a minimum version; reduce `requirements.txt` to `-e .`. Fill in `description` and `keywords`. Add `"*.lbl"` to `[tool.setuptools.package-data]."metadata_tools"`. Create an empty `src/metadata_tools/py.typed` only if you also annotate the package; otherwise remove the py.typed package-data entry. Reconcile the Python minimum across `requires-python`, `[tool.ruff] target-version`, and `python.mdc`.
> 2. **De-`exec()` the column files:** In `src/metadata_tools/column/COLUMNS_*.py`, add the imports each file actually uses (`import numpy as np`, `import metadata_tools.util as util`, `import oops`) and obtain `BODIES` explicitly (import from `metadata_tools.columns` or accept it as a parameter). Replace the `exec()` loop in `columns.py` with normal imports or an explicit registration function. Confirm `ruff --select F821 src` is clean.
> 3. **Correctness bugs:** (a) In `geometry_support.py` `Record.__init__`, change `col.RING_SUMMARY_DETAILED`→`col.RING_DETAILED_DICT`, `col.BODY_SUMMARY_DETAILED`→`col.BODY_DETAILED_DICT`, and `col.BODYX`→`defs.BODYX`. (b) In `index_support.py:_get_null_value`, change the `continue` to `break`. (c) In `index_support.py:_create_index`, move `unused = None` above the `for root … walk()` loop and move `logger.close(force=True)`, the task-file write, and the unused-columns warning to after the loop. (d) In `util.py:append_txt_file`, `return` immediately after calling `write_txt_file` when the file did not exist. (e) In `geometry_support.py:_prep_row`, rename the per-column reuse of `target` (line ~710) and build the `override` dict inside the column loop. Add or update a unit test for each.
> 4. **Rule compliance:** Remove `util.dbprint` and its call in `common.py:Table.write`; route any needed messages through `com.get_logger()` with `%`-style args. Rename builtin-shadowing names (`format`→`fmt`, `id`→`obs_id`, `type`→`type_`, `dict`→`mapping`, `min`/`max`→`min_val`/`max_val`). Replace `eval()` in `util.py:replace` with an explicit `getattr(defs, name)[key]` lookup. Replace runtime `assert`s in `index_support.py` with raised exceptions. Move `import math` to the top of `util.py`. Run `ruff check --fix` for whitespace/import-order/comprehension fixes.
> 5. **Hygiene:** `git rm` the committed runtime artifacts under `src/metadata_tools/hosts/GO_0xxx/` (`metadata-*-job.db`, `metadata-*_in_queue_original.json`, `*_tasks.json`, `cprofile.txt`, `log.txt`) and add matching patterns to `.gitignore`. Delete commented-out code blocks flagged in §1/§6.
> 6. **Types:** Add full annotations (params and return, including `-> None`) starting with the public entry points and the `Table`/`Record`/`Suite`/`IndexTable` constructors, until `mypy --strict src` passes.
>
> Do not alter the numeric/format constants in `FORMAT_DICT`/`ALT_FORMAT_DICT` or the column definition tuples except where item 3 requires a name fix. Preserve PDS3 label/table byte-for-byte output.
