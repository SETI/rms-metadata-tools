# Test Suite Critique Report

**Generated:** 2026-07-15
**Scope:** `tests/` (all files, including `conftest.py`, `columns/conftest.py`,
and `tests/hosts/GO_0xxx/`), plus the pytest/coverage configuration in
`pyproject.toml` and the pytest invocation in `scripts/run-all-checks.sh` and
`.github/workflows/run-tests.yml`.
**Rules applied:** `python_testing.mdc` (primary), `python.mdc`, `logging.mdc`,
`filecache.mdc`.

## Executive summary

This is a strong, disciplined test suite. It is hermetic by default (SPICE/oops
and the `$RMS_METADATA` holdings tree are stubbed or gated behind markers),
parallel-safe (`-n auto`, `pytest-randomly` installed), and asserts precise
values rather than mere existence. Configuration is exemplary: `testpaths`,
`--strict-markers`, `--strict-config`, `filterwarnings = ["error"]`, and a
registered `markers` table are all present (`pyproject.toml`
`[tool.pytest.ini_options]`). Exception tests consistently assert on message
content via `pytest.raises(..., match=...)`.

**Main gaps / high-priority fixes:**

- **Coverage is measured over a reduced denominator.** `cli/*`, `hosts/*`, and
  `bodies.py` are excluded from coverage (`pyproject.toml`
  `[tool.coverage.run] omit`). `cli/_host.py` (442 lines) is heavily tested by
  `tests/test_cli_host.py` yet its coverage is not counted, and the CLI `main()`
  dispatchers and worker `Task.__call__` callables are untested. The stated 90%
  target therefore measures only the host-agnostic engine, not the whole
  importable surface.
- **Heavy testing through private names.** Many tests import and drive `_`-prefixed
  internals (`_get_range_mod360`, `_ninety_percent_gap_degrees`,
  `_resolve_dict_ref`, `_create_index`, `_cat_rows`, `_index_one_value`,
  `_format_*`, `_strip_cloud_args`). Justified where there is no public wrapper,
  but it couples tests to implementation.
- **A few stale/duplicated test comments and some missing edge cases**
  (empty-input and boundary cases for `_format_column`, `sclk_split_count`,
  `add_by_base` carry chains).

Everything below is a **report only** — no test files were modified.

## 1. Return values and assertions

Strong overall. Tests assert exact values, exact lengths, and exact structures:

- Exact string outputs: `tests/test_index_support.py:38`
  (`'"IO        "'`), `tests/test_geometry_formatting.py:20`
  (`'  28.648,  57.296'`), `tests/test_geometry_prep.py:58`.
- Exact lengths for collections: `tests/test_cumulative_support.py:121`
  (`len(calls) == 8`), `tests/test_geometry_prep.py:69` (`len(rows[0]) == 3`).
- Exact dict shapes: `tests/test_geometry_tables.py:147-148`
  (`{'NULL_VALUE': -999., 'VALID_MINIMUM': 0, 'VALID_MAXIMUM': 360}`).

Minor: a handful of assertions check only membership/existence where an exact
value is knowable — e.g. `tests/test_common.py:123` (`('stdout',) in handlers`)
and `tests/test_geometry_tables.py:172` asserts qualifier order but not that
exactly four tables exist beyond the list comparison (the list comparison does
fix it). These are acceptable.

## 2. Success and failure conditions

Both paths are well covered for the engine:

- Success + failure for `_index_one_value` (builtin key, config key, raw label,
  missing→null, None→null, None-without-null→`ValueError`):
  `tests/test_index_support.py:143-194`.
- `inventory` success, SPICE-CKINSUFFDATA (clears pointing), and
  non-SPICE-error-propagates: `tests/test_geometry_constructors.py:25-60`.
- `Suite.__init__` early-return, multiple-index `RuntimeError`, and full build:
  `tests/test_geometry_constructors.py:165-198`.

**Gaps:**

- **CLI entry points (`main()`) are untested.** No test drives
  `metadata_tools.cli.index:main` (or geometry/cumulative/worker/cloud/task_list
  `main`), the argv-length guards (`sys.exit('Usage: ...')`), or the worker
  `_IndexTask/_GeometryTask/_CumulativeTask.__call__` callables. Because `cli/*`
  is omitted from coverage this is invisible. Add at least: a `main()` no-args
  `SystemExit` test per entry point, and one `__call__` test per worker task
  (monkeypatching the engine `process_*`).
- `dispatch_cloud_run_if_config` (the YAML-injection + subprocess dispatch in
  `cli/_host.py:242-358`) is untested; only `build_startup_script`,
  `resolve_host_paths`, `pop_argv_*`, `_strip_cloud_args`, and the two task-file
  context managers are covered (`tests/test_cli_host.py`). Consider a test that
  monkeypatches `subprocess.Popen` and `yaml`.

## 3. Consistency

- **Naming** is consistent and descriptive (`test_<subject>_<condition>`), e.g.
  `test_inventory_missing_ckernel_clears_pointing`,
  `test_create_cumulative_indexes_uses_args_exclude_over_parameter`.
- **Structure** mirrors the source tree well: `tests/columns/` for the columns
  package, `tests/hosts/GO_0xxx/` for host tests, and one `test_util_*.py` per
  concern.
- **Assertion style** is uniform (bare `assert` with precise expected values).
- Minor inconsistency: the top-level engine tests are flat modules
  (`test_geometry_record.py`, etc.) while the `columns/` tests are a subpackage
  with a dedicated `conftest.py`; this is appropriate, not a defect.

## 4. Completeness (coverage map)

| Module / area | Tested behaviors | Notable gaps |
|---|---|---|
| `util` (paths/text/sclk/math/angles) | Broad: `test_util_math`, `test_util_names`, `test_util_range_mod360`, `test_util_replace`, `test_util_textfile` | `_get_range_mod360` `width>1` smoothing path (see code critique §9); `sclk_format_count` where field count < format fields |
| `common` (`Table`, args, logger) | `test_common.py` | `Table.write` label `table_type` when `level is None` (inventory) — partially via geometry tests |
| `config` | `test_config.py` full | — |
| `index_support` | `test_index_support.py` extensive | full `IndexTable.create` glob/pattern-skip combinations |
| `geometry_support` (masks/prep/record/tables/suite/formatting/formats/bodies_select/process) | Very thorough hermetic coverage | detailed-level Sun path (`SunTable` unused); `SKY_TILES` detailed tiling (`###TODO: not tested`, `columns/sky.py:55`) |
| `cumulative_support` | `test_cumulative_support.py` | — |
| `task_list_support` | `test_task_list.py` full | — |
| `cli/_host` | `test_cli_host.py` extensive for pure helpers | `dispatch_cloud_run_if_config`, `run_cloud_worker` |
| `cli/*` `main()` + worker tasks | **none** | all |
| `label_support` | `test_label_support.py` | — |
| `bodies` | integration-only (`tests/columns/test_columns_integration.py`) | excluded from hermetic coverage by design |
| host `index_config`/`geometry_config` key functions | none hermetic (only `requires_archive`) | `key__start_time`, `key__stop_time`, `key__spacecraft_clock_*`, `key__on_chip_mosaic_flag`, `_event_tai` are pure and unit-testable but untested |

**Highest-value additions:** the GOSSI `key__*` functions in
`hosts/GO_0xxx/index_config.py` are pure label→value transforms (no SPICE) and
could be unit-tested hermetically with a fake `label_dict`; today they are only
indirectly exercised by the `requires_archive` tier.

## 5. Redundancy

Very little. A few near-duplicate pairs are intentional (min vs. max, arg vs.
env, ssh vs. non-ssh): e.g. `tests/test_cli_host.py:159-424` has many
`build_startup_script` variants. These could be parametrized (see §9) but each
asserts a distinct behavior, so they are not true duplicates. No
delete-me duplicates found.

## 6. Parallel execution

- **Isolation is good.** Global config state is installed once at import via
  `tests/conftest.py::_install_fakes()` and per-test overrides use `monkeypatch`
  (auto-reverting). `test_config.py` clears the registry with `monkeypatch.setattr`
  and relies on teardown restore.
- `sys.argv` is always mutated via `monkeypatch.setattr(sys, 'argv', ...)`
  (`test_cli_host.py` throughout), so it reverts — safe under `-n auto`.
- `pytest-randomly` is installed (dev group), so order-dependence would surface.
- **`run-all-checks.sh` uses `--dist loadscope`** to keep each module on one
  worker (`run-all-checks.sh:419`), sensibly avoiding cross-module time/fixture
  interference. Note the default CI/`pyproject` run uses plain `-n auto` without
  `loadscope`; the suite still passes because tests are properly isolated.
- One thing to watch: `test_util_math.py::test_range_of_n_angles_is_deterministic_when_seeded`
  calls `np.random.seed(0)` globally (`tests/test_util_math.py:127`). It is
  seeded so it is deterministic, but it mutates global NumPy RNG state; any
  later test in the same worker that (wrongly) depended on unseeded RNG could be
  affected. Currently no other test uses `np.random` for assertions, so this is
  safe — but prefer a local `np.random.default_rng(0)` if the helper is
  refactored.

## 7. Mocking and dependency isolation

- **Real objects where cheap:** `test_geometry_formatting.py` and
  `test_geometry_masks.py` use real `oops.Scalar`/`polymath.Boolean` (which work
  without kernels), exercising formatting honestly rather than mock-shaped
  (`tests/test_geometry_formatting.py:1-8` docstring states this intent). Good.
- **Fakes centralized in conftest:** `FakeBackplane`, `record_stub`,
  `silent_logger`, `exists_true`, `tmp_volume_tree` live in
  `tests/conftest.py`; the columns fakes in `tests/columns/conftest.py`. This
  matches `python_testing.mdc` §8.
- **Patch targets are correct** (patched where looked up), e.g.
  `monkeypatch.setattr(idx.process, 'IndexTable', ...)`
  (`tests/test_index_support.py:268`) and
  `monkeypatch.setattr(idx.process, '_create_index', ...)` (line 391).
- **Env isolation:** `build_startup_script` tests `delenv`/`setenv` the relevant
  vars every time (`test_cli_host.py:164-165` etc.), so they do not depend on
  the developer's real environment.
- Minor: several `silent_logger`/hand-rolled logger stubs use
  `types.SimpleNamespace(info=lambda ...)`; these return real `None`, so there is
  no MagicMock-truthiness hazard. Good.

## 8. Security and input validation

- Input-validation failure paths are tested where the engine validates:
  `_format_column` count mismatch → `ValueError` with message
  (`test_index_support.py:113-116`); `_resolve_dict_ref` rejects unknown module
  and unrecognized pattern (`test_util_replace.py:68-79`);
  `splitpath` raises when the split string is absent
  (`test_util_names.py:78-80`).
- No secrets appear in test data; task-file fixtures use synthetic volume IDs.
- Path-traversal is not directly relevant (paths are `FCPath`, values come from
  trusted PDS labels), so no gap here.

## 9. Parameterization

- **`@pytest.mark.parametrize` is not used anywhere in the suite.** Several
  clusters are prime candidates and would report each case separately:
  - `_format_value` char/real/int (`test_index_support.py:37-62`).
  - `_get_null_value` priority cases (`test_index_support.py:68-89`).
  - `build_startup_script` env-vs-arg-vs-default matrix
    (`test_cli_host.py:159-296`).
  - `get_system` satellite/planet/unknown (`test_geometry_record.py:99-111`).
  - `obs_excluded` regex/identifier/none (`test_geometry_record.py:117-156`).
  **Suggestion:** convert these copy-shaped bodies to `parametrize` with readable
  `ids`, per `python_testing.mdc` §6.
- **Boundary values:** `add_by_base` tests cover no-carry, single carry, and a
  chained carry, but not the max-base rollover for the real `SCLK_BASES`
  beyond a single tick (`test_util_math.py:22-29`). `sclk_split_count` does not
  test an all-alnum count with `delim=None` and no separators.

## 10. Async

- The only async code is `run_cloud_worker` (`cli/_host.py:406-443`, wraps
  `asyncio.run`). It is untested (see §2). Not otherwise applicable — the engine
  is synchronous.

## 11. Output and contract

- Return-shape contracts are asserted where defined: override dicts
  (`test_geometry_tables.py:147`), task dicts
  (`test_task_list.py:16-18`, exact `{'task_id':..., 'data':{...}}`), and row
  strings (`test_geometry_prep.py`).
- Exceptions are asserted with type **and** message (`match=`) consistently:
  `test_index_support.py:115,193`; `test_geometry_constructors.py:179`;
  `test_util_names.py:79`; `test_util_replace.py:71,78`.

## 12. Error handling and messages

- Distinct error conditions are distinguished by message content, not just type
  — e.g. `'column X: expected 3 values but got 2'`
  (`test_index_support.py:115`), `'No primary index for GO_0001'`
  (`test_index_support.py:339`), `'Null constant needed'` (line 193),
  `'index files'` (`test_geometry_constructors.py:179`).
- `bodies_select.inventory`'s two error branches (SPICE→clears pointing vs.
  other→propagates) are both asserted, including the *non*-effect on
  `pointing_available` (`test_geometry_constructors.py:47-60`). Excellent.

## 13. State and workflow

- Level/qualifier dispatch is tested (`Suite.add` routes by level,
  `test_geometry_tables.py:191-201`; `RingTable.add` only when
  `rings_present` and `primary`, lines 59-77).
- Null-linking postprocess transitions (both propagate and leave-alone) are
  tested (`test_geometry_record.py:66-84`).
- Idempotency/repeat-call behavior is not explicitly tested, but the engine's
  operations are file-producing rather than stateful transitions, so this is a
  minor gap. `task_generator` reusability *is* asserted
  (`test_task_list.py:41-44`).

## 14. Test data and fixtures

- **Fixture scope is appropriate:** function-scoped for mutable helpers
  (`fake_backplane`, `record_stub`), session-scoped only for the read-only
  standalone-loaded column modules (`tests/columns/conftest.py:40-55`). Good.
- **Cleanup:** all filesystem work uses `tmp_path`/`tmp_volume_tree`; nothing
  writes into the repo.
- **No autouse fixtures** — dependencies are explicit (requested by name). Good.
- **Conftest hierarchy** is correct: project-wide fakes at the root, columns-only
  loaders in `tests/columns/conftest.py`.
- Minor: `record_stub` builds a `Record` via `__new__` and sets arbitrary
  attributes — a powerful but implementation-coupled helper (§20). It is well
  documented (`conftest.py:145-160`).
- Realism: most test data is trivial (`'IO'`, `[0.5, 1.0]`). The formatting
  tests do exercise NaN/inf/overflow/masked realistically
  (`test_geometry_formatting.py:54-112`). Consider a Unicode/long-string case for
  `_format_column`'s string scrubbing (`test_index_support.py:119-123` covers
  whitespace/quotes but not multibyte).

## 15. Flakiness indicators

- **No wall-clock assertions.** ISO-time tests use fixed TAI inputs
  (`test_geometry_formatting.py:48-51`), not `datetime.now()`.
- **No network/filesystem-state dependence** in the default tier (all gated by
  `requires_archive`).
- **RNG:** the one Monte-Carlo helper is seeded (`test_util_math.py:127`); see
  §6 for the global-state caveat.
- **`filterwarnings = ["error"]`** means a stray warning fails the run — a
  strong anti-flakiness guard.

## 16. Regression and documentation

- Regression intent is documented inline where relevant, e.g.
  `test_build_startup_empty_startup_template_env_uses_default` carries a
  `"""Regression: GCP_STARTUP_TEMPLATE='' must not be passed to Path()."""`
  docstring (`test_cli_host.py:270-272`), and
  `test_geometry_columns_contract.py` explains the latent-`AttributeError` typos
  it guards. Good practice, though none reference an issue number.
- **Deprecation-warning tests:** none, because the package intentionally has no
  deprecated public API (`python.mdc` §2 forbids back-compat code). The one
  back-compat alias `resolve_task_file` (`cli/_host.py:89`) has no test and no
  `DeprecationWarning`; simplest fix is to remove it (see code critique).
- **`filterwarnings` config:** present and set to `error` — the recommended
  posture.

## 17. Other good practices

- **AAA structure** is followed; tests are short and single-purpose.
- **Minimal logic in tests:** small loops appear only in
  `test_geometry_columns_contract.py` (AST walking) and the `requires_archive`
  label loops, where they aid clarity.
- **Speed:** the hermetic suite avoids SPICE, so it is fast. The
  `requires_archive` tier uses `print()` and file walks
  (`tests/test_index.py`, `tests/test_geometry.py`,
  `tests/hosts/GO_0xxx/test_*.py`) — acceptable for an opt-in integration tier,
  though the `print()` calls add noise; consider `caplog`/`-s`-only output if
  those tiers are run in CI later.
- **Assertion messages:** the `requires_archive` tests append `, file` to
  assertions so a failure names the offending label — a nice touch
  (`tests/test_geometry.py:75`).

## 18. Code coverage

- **Target:** `fail_under = 90` (`pyproject.toml` `[tool.coverage.report]`);
  branch coverage is on (`[tool.coverage.run] branch = true`). `codecov.yml`
  also targets 90% project and patch.
- **Measurement:** the default `pytest` run measures coverage
  (`addopts = [... "--cov=src" ...]`) over the **whole suite** (good), but the
  **denominator is narrowed** by `omit = ["tests/*", "*/_version.py",
  "*/metadata_tools/bodies.py", "*/metadata_tools/hosts/*",
  "*/metadata_tools/cli/*"]`. The omit of `bodies.py` and `hosts/*` is
  justified (SPICE-only) and documented; the omit of **all of `cli/*`** hides
  `cli/_host.py`, which is 442 lines of testable, and largely tested, logic.
- **Recommendation:** stop omitting `cli/_host.py` (the only CLI module with
  branch-heavy, hermetic logic). Keep the SPICE/argv-driving `main()` shells
  excluded via targeted commented `# pragma: no cover` at the seam, as the omit
  comment already prescribes for "any other SPICE-only seam." Then add the §2
  tests so the real number reflects the CLI helpers.

## 19. Pytest markers and registration

- **Registered:** `integration` and `requires_archive` are both declared in
  `pyproject.toml` `markers` with descriptions.
- **`--strict-markers` and `--strict-config`** are enabled in `addopts`, so a
  marker typo fails fast. Excellent.
- **No `xfail`/`skip`/`skipif`** in the suite — nothing stale to audit.
- **Categorization:** the two-tier marker scheme (fast hermetic default vs.
  opt-in `integration`/`requires_archive`) is exactly the recommended pattern.

## 20. Test boundary (public API vs. internals)

- **Private-name imports are common:** tests exercise `util._get_range_mod360`,
  `util._ninety_percent_gap_degrees`, `util._resolve_dict_ref`,
  `idx._create_index`, `IndexTable._index_one_value`/`_format_*`/`_get_*`,
  `cum._cat_rows`, and `_host._strip_cloud_args`. Per `python_testing.mdc` §8 /
  critique-test-suite §20 this couples tests to implementation, but here it is
  largely justified: these functions carry non-trivial logic with no thin public
  wrapper, and testing only through `process_index`/`process_tables` would
  require SPICE or large fixtures. **Suggestion:** keep them, but where a public
  entry point already covers the behavior end-to-end (e.g. `_create_index` is
  reachable via `process_index`, tested at `test_index_support.py:389-399`),
  ensure the private-level test is adding a distinct assertion, not duplicating.
- **Over-mocking check:** the `Suite`/`Record` constructor tests
  (`test_geometry_constructors.py:103-124`) monkeypatch many collaborators
  (`get_primary`, `inventory`, `select_bodies`, `target_name`, `meshgrid`,
  `Backplane`, the body registry). This is necessary to run SPICE-bound
  constructors hermetically and the tests still assert real attribute outcomes
  (`record.primary`, `record.prefixes`, `record.dicts['ring'] is
  col.RING_SUMMARY_DICT`), so they test behavior, not the mock. Acceptable.

## 21. Logging assertions

- `caplog` is **not used**. Several code paths log at `warning`/`exception`
  levels whose emission is not asserted: `bodies_select.inventory`
  (`logger.warning` / `logger.exception`), `IndexTable._format_column`
  (`logger.warning("Invalid format...")`, "No second format", "Format error"),
  and `_create_index`'s "Unused columns" warning.
- The unused-columns *value* is asserted indirectly by capturing a fake logger's
  argument (`tests/test_index_support.py:268-279`), which is a reasonable
  substitute but bypasses level verification.
- **Suggestion:** add `caplog`-based tests for the `IndexTable._format_column`
  warning branches (feed a value incompatible with the Fortran format and assert
  a `WARNING`-level record with the expected substring), and for
  `bodies_select.inventory`'s SPICE-warning branch, to verify both message and
  level. Note `filterwarnings=["error"]` governs `warnings.warn`, not
  `PdsLogger` output, so logger branches need explicit `caplog` assertions.

## 22. Pytest configuration

- **`testpaths = ["tests"]`** is set — collection is scoped, fast, and avoids
  stray files.
- **`addopts`** includes `-n auto`, `--cov=src`, `--strict-markers`,
  `--strict-config`, and the default marker filter
  `-m "not integration and not requires_archive"`. Sensible defaults.
- **Plugins:** `pytest-xdist`, `pytest-cov`, and `pytest-randomly` are declared
  in the dev group and all used/beneficial. No unused-plugin startup cost noted.
- **No config conflict:** there is no `pytest.ini`/`setup.cfg`; the single
  source is `pyproject.toml`.
- **One consideration:** `addopts` hard-codes `-n auto`, so a single-test debug
  run still spawns xdist workers (tracebacks interleave). `run-all-checks.sh`
  offers `-w 1`; document `pytest -p no:xdist` / `-n0` for local debugging.

## 23. Snapshot and golden-file testing

- No snapshot library (`syrupy`) is used, and none is needed: the largest
  outputs asserted are single formatted rows and small override dicts, which
  read clearly as inline literals. The `requires_archive` tier effectively uses
  the on-disk PDS tables as golden inputs (read-only validation, not
  approve-and-forget snapshots). No change recommended.

---

## Prompt for an AI agent to fix the tests

> You are improving the `rms-metadata-tools` test suite per
> `critiques/tests_critique.md`. **Do not change production code**; only add or
> restructure tests and adjust test/coverage configuration. Preserve every
> currently passing behavior; only add/strengthen assertions and structure.
> Follow `.cursor/rules/python_testing.mdc` and `python.mdc` (type-annotate every
> test, `-> None`, precise-value assertions, `pytest.raises(..., match=...)` with
> message content, fixtures in the nearest `conftest.py`, no autouse).
>
> Context: the suite is hermetic and parallel-safe with `filterwarnings=["error"]`,
> `--strict-markers`, `--strict-config`, and two registered markers
> (`integration`, `requires_archive`) excluded by default.
>
> Tasks, in priority order:
> 1. **Coverage denominator (§18):** in `pyproject.toml` `[tool.coverage.run]`,
>    stop omitting `cli/_host.py` (keep the other `cli/*` `main()` shells excluded
>    via commented `# pragma: no cover` at the SPICE/argv seam if needed). Then
>    add tests so its counted coverage stays ≥90% overall.
> 2. **Untested behavior (§2):** add tests for each `cli/*` `main()` no-args
>    `SystemExit`, for the worker `_IndexTask/_GeometryTask/_CumulativeTask.__call__`
>    (monkeypatch the engine `process_*` and assert it is called with the task's
>    `volume_id`), and for `dispatch_cloud_run_if_config` (monkeypatch
>    `subprocess.Popen` and `yaml`).
> 3. **Host key functions (§4):** add hermetic unit tests for the pure
>    `key__*`/`_event_tai`/`_spacecraft_clock_*` functions in
>    `src/metadata_tools/hosts/GO_0xxx/index_config.py` using synthetic
>    `label_dict`s (mock `julian`/`vicar` where a file read would occur). Mark
>    them so they run in the default tier (they need no SPICE).
> 4. **Logging assertions (§21):** add `caplog` tests for the `warning` branches
>    of `IndexTable._format_column` and `bodies_select.inventory`, asserting both
>    the message substring and the log level.
> 5. **Parameterize (§9):** convert the copy-shaped clusters
>    (`_format_value`, `_get_null_value`, `build_startup_script`
>    env/arg/default matrix, `get_system`, `obs_excluded`) to
>    `@pytest.mark.parametrize` with readable `ids`.
> 6. **Housekeeping:** remove the stale comment at
>    `tests/test_geometry_record.py:26` (the docstring it references is correct);
>    add a `width>1` case to `test_util_range_mod360.py`; add a boundary case for
>    `add_by_base` chained carry over the real `SCLK_BASES`.
>
> After each change run the entire suite with coverage
> (`pytest tests/ --cov=src --cov-report=term-missing`) and confirm ≥90% and a
> clean, warning-free run.
