# Test Suite Critique Report

**Generated:** 2026-06-15
**Scope:** `tests/` (`test_index.py`, `test_geometry.py`, `unittester_support.py`, `__init__.py`) plus the never-collected host tests under `src/metadata_tools/hosts/GO_0xxx/tests/`. No `conftest.py` exists.
**Authoritative rules:** `.cursor/rules/python_testing.mdc` (primary), `python.mdc`, `filecache.mdc`, `logging.mdc`.

## Executive summary

The test suite does **not test the code in this repository**. Every test reads pre-generated PDS3 `.lbl`/`.tab` files from the `$RMS_METADATA` directory tree and checks that `rms-pdstable`/`rms-pdsparser` can parse them and that values fall in range. No test ever imports `metadata_tools` or calls any function in `src/`. Consequently:

- **Coverage:** Effectively **~0% of `src/metadata_tools`**, despite `pyproject.toml` configuring `--cov=src` and `[tool.coverage.report] fail_under = 90`. The 90% target is not, and cannot be, met by the current tests, and coverage is not being measured over code that runs. This is the single most important gap.
- **Hermeticity:** Tests hard-depend on environment variables and on-disk data. `tests/unittester_support.py:9-10` reads `os.environ['RMS_METADATA']` and `os.environ['RMS_VOLUMES']` **at import time**, so without those variables the entire suite errors during collection. When the variables are set but the directories contain no matching files, the per-file `for` loops execute zero times and the tests **pass vacuously** — false confidence (`python_testing.mdc` §10).
- **Framework:** All tests use `unittest.TestCase`, which `python_testing.mdc` §2 forbids for new tests ("Do not write `unittest.TestCase` classes"). `ruff` reports 35×PT009 (`assertEqual`/`assertFalse`/`assertIsInstance`).
- **Dead tests:** `tests/test_geometry.py::test_geometry_cumulative` is disabled by a bare `return` on its first line; the host tests under `src/.../GO_0xxx/tests/` are never collected because `testpaths = ["tests"]`.

High-priority fixes: add real unit tests that import and exercise the pure logic in `util.py`/`index_support.py`; make the env-dependent integration tests skip cleanly and fail (not pass) when no data is found; migrate to pytest style.

## 1. Return values and assertions

- **Existence/type-only asserts.** `test_index.py:46-50` and `test_geometry.py:63-64, 81` only assert `assertIsInstance(..., np.str_)` on element `[0]` of a column — they check the type of one cell, not values, counts, or shape. **Fix:** assert exact expected values for at least one known row (e.g. a known `VOLUME_ID`, a known `START_TIME`).
- **No assertion at all.** `test_geometry.py::test_inventory` (lines 16-27) and `test_index.py::test_supplemental_index__cumulative` (lines 15-25) read each label and assert nothing — they only verify "did not raise." `python_testing.mdc` §7 forbids assertion-free tests. **Fix:** assert on the parsed table (row count > 0, expected columns present).
- **Convoluted/likely-wrong assertion.** `hosts/GO_0xxx/tests/test_geometry.py:32`: `self.assertFalse(np.any(np.where(table.column_values['VOLUME_ID'] != volume)) == np.True_, file)` mixes `np.where` (returns index tuples) with `np.any` and an `== np.True_` comparison; this does not robustly test "all VOLUME_ID == volume." **Fix:** `assert np.all(table.column_values['VOLUME_ID'] == volume)`.

## 2. Success and failure conditions

- Only happy-path "file parses" behavior is covered. There are **no failure-path tests**: no test for invalid SCLK strings, missing label keywords, malformed formats, or the `key__*` functions returning `None`. **Fix:** unit-test `index_config.key__*` and `util.sclk_*`/`rebase`/`add_by_base` with both valid and invalid inputs.
- No edge cases (empty inputs, single-element arrays, wrap-around longitudes). `util._get_range_mod360` has rich branching (single value, full coverage, 90%-confidence gap) and is completely untested. **Fix:** parametrized tests over those branches.

## 3. Consistency

- Naming is inconsistent and non-descriptive: `test_geometry_common`, `test_geometry_body`, `test_supplemental_index__cumulative` (double underscore) don't follow a `test_<unit>_<condition>_<expected>` scheme (`python_testing.mdc` §3). The same method name `test_geometry_common` appears in both `tests/test_geometry.py` and `hosts/.../tests/test_geometry.py` with different bodies.
- Structure is duplicated: every test repeats the `match(...)` → `exclude(...)` → `for file: print(); PdsTable(file)` block. **Fix:** factor into a fixture/helper that yields parsed tables for a glob.

## 4. Completeness (coverage map)

| `src` area | Behavior tested? |
|---|---|
| `util.py` (sclk parsing, rebase, base arithmetic, mod-360 range, txt I/O, name parsing) | **None** |
| `index_support.py` (`IndexTable`, formatting, null lookup, key dispatch) | **None** |
| `geometry_support.py` (`Record`, masks, `FORMAT_DICT` formatting, `Suite`) | **None** |
| `cumulative_support.py` | **None** |
| `common.py` (`Table`, arg parsing, task list) | **None** |
| `label_support.py` | **None** |
| `index_config.key__*` (Galileo) | **None** (only the resulting `.tab` columns are spot-checked) |
| Output `.lbl`/`.tab` files parse & values in range | Yes (integration, env-dependent) |

The existing tests are best described as **archive-validation integration tests**, not unit tests for this package. **Fix:** keep them (behind a marker, see §19) but add a real unit layer.

## 5. Redundancy

- `tests/test_geometry.py::test_geometry_common` and `hosts/.../test_geometry.py::test_geometry_common` overlap (both glob `*_summary.lbl` and check `VOLUME_ID`). `tests/test_index.py::test_supplemental_index_common` and `hosts/.../test_index.py::test_supplemental_index_GOSSI` overlap on `*_supplemental_index.lbl`. **Fix:** separate generic vs. host-specific assertions; don't re-glob the same set twice.

## 6. Parallel execution

- Tests are run under `-n auto --dist loadscope` (`run-all-checks.sh`) / `-n auto` (CI). They share the read-only `$RMS_METADATA` tree, which is safe, **but** they rely on filesystem state and env vars, so behavior differs per worker/machine. No mutable global state is shared, so parallelism itself is not the risk — **reproducibility** is (§15).

## 7. Mocking and dependency isolation

- **Environment dependence (high).** `unittester_support.py:9-10` reads required env vars at import. Tests would behave differently with different `$RMS_METADATA` contents (`python_testing.mdc` §8: "Tests should not depend on real env values"). **Fix:** read env vars lazily inside a fixture; `pytest.skip("RMS_METADATA not set")` when absent.
- **No mocking of external data.** Pure logic that could be unit-tested without any files (sclk math, range math, format strings) is only reachable today through full archive files. **Fix:** test those functions directly with in-memory inputs.

## 8. Security and input validation

- No tests for malformed/hostile input (bad SCLK, non-numeric exposure, path edge cases). Low risk for an internal pipeline, but the formatting/parsing helpers warrant invalid-input tests. **Fix:** add `pytest.raises`-based tests for the parsing helpers.

## 9. Parameterization

- The `for file in files:` loops are hand-rolled iteration that should be pytest parametrization so each archive file reports pass/fail independently (`python_testing.mdc` §6). The long lists of `unit.bounds(self, file, table, 'NAME', min=, max=)` calls in `test_geometry.py:84-98, 115-136` are ideal `@pytest.mark.parametrize` tables. **Fix:** parametrize over (column, min, max).

## 10. Async

- Not applicable to tests (the only async code is in `*_cloud.py` `main()`, which is untested — consider a smoke test that builds the task list).

## 11. Output and contract

- The library's real contract is the **content of generated tables/labels**, but tests only re-parse already-generated files. There is no golden-file comparison of a freshly generated table against an expected one. **Fix:** see §23.

## 12. Error handling and messages

- No test asserts on any exception type or message anywhere (no `pytest.raises`). `python_testing.mdc` §7 requires asserting on exception message content. **Fix:** add error-path tests with `pytest.raises(..., match=...)`.

## 13. State and workflow

- The three-stage pipeline (index → geometry → cumulative) has no end-to-end test on a tiny fixture volume. **Fix:** add one small fixture volume under `tests/data/` and assert the produced supplemental index has the expected rows/columns.

## 14. Test data and fixtures

- **No `conftest.py` and no fixtures.** Shared setup (`match`/`exclude`, parsed tables, env access) is duplicated. `python_testing.mdc` §5 wants shared setup in `conftest.py`. **Fix:** add `tests/conftest.py` with a `metadata_root` fixture (skips if env unset) and a `parsed_tables(glob)` factory fixture.
- `bounds()` in `unittester_support.py:51-85` is a custom assertion helper with builtin-shadowing params `min`/`max` (ruff A002) and pulls an arbitrary null via `nullvals.pop()`. **Fix:** rename params; handle multiple invalid values explicitly.

## 15. Flakiness indicators

- **Vacuous pass when no data:** if a glob matches nothing, the test passes without asserting anything. **Fix:** assert `len(files) > 0` (or skip with a clear reason) before the loop.
- **Order/file-state dependence:** results depend on whatever is currently in `$RMS_METADATA`. **Fix:** pin a small committed fixture tree for the unit/integration boundary.
- No use of `random`/time, so no nondeterminism from those.

## 16. Regression and documentation

- No regression tests reference issues/bugs. The known bug paths identified in `code_critique.md` (`_get_null_value` `break`, detailed-geometry `col.*_DETAILED`, `append_txt_file` double-write) have **no** tests and would not be caught. **Fix:** add a regression test per fixed bug.
- **`filterwarnings` not configured.** `pyproject.toml [tool.pytest.ini_options]` has no `filterwarnings = ["error"]`, so warnings (e.g. the `warnings.warn` calls in `geometry_support.py`/`index_config.py`) are silently swallowed (`python_testing.mdc` §4, critique §16). **Fix:** add `filterwarnings = ["error", ...]` with narrowly-scoped ignores.

## 17. Other

- `print()` is used throughout tests (`test_index.py:23-24, 36-38`, `test_geometry.py:24-26`, etc.) for tracing — noise under `-q`. **Fix:** remove; rely on pytest's `-v`/`--no-header` and assertion messages.
- No type annotations on any test function (`python_testing.mdc` §2 requires `-> None` and param types). ruff/N rules and mypy(tests) would flag.
- `test_geometry_cumulative` (`test_geometry.py:31-42`) is **disabled by a bare `return`** on line 32 before any assertion — it always passes. The comment "this needs to be changed to match cumulative files" marks it unfinished. **Fix:** implement or remove and track with a ticket.

## 18. Code coverage

- **Target 90% not met.** With tests that never import `src`, coverage of `metadata_tools` is approximately **0%**. CI runs `pytest --cov=src -n auto tests` and `coverage report -m`; `codecov.yml` and `[tool.coverage.report] fail_under = 90` both assert 90%. Measurement is full-suite but over code that does not run. **Fix:** add unit tests until `pytest --cov=src --cov-report=term-missing` shows ≥90% of the non-exception lines in `util.py`, `index_support.py`, `geometry_support.py`, `cumulative_support.py`, `common.py`, `label_support.py` actually executing.

## 19. Pytest markers and registration

- `addopts = ["-n","auto","--cov=src","--strict-markers","--strict-config"]` and `markers = []`. `--strict-markers` is on (good), but there are **no markers**, so the slow, data-dependent integration tests cannot be separated from fast unit tests (`python_testing.mdc` §4 wants slow/environment-dependent tiers behind a marker excluded by default). **Fix:** register `integration` and `requires_archive` markers; mark the archive-reading tests and exclude them from the default run via `-m "not requires_archive"`.

## 20. Test boundary (public API vs internals)

- Today tests touch **neither** the public API nor internals of `metadata_tools` — only third-party parsers on output files. This gives false confidence: the public API could be entirely broken while these tests stay green. **Fix:** test through the public functions (`process_index`, `IndexTable`, `util.*`).

## 21. Logging assertions

- The library logs warnings/errors (`com.get_logger()` in `index_support.py`, `geometry_support.py`) and emits `warnings.warn` (`geometry_support.py:968-993`, `index_config.py:114`). No test uses `caplog`/`pytest.warns` to assert these fire (`python_testing.mdc`-adjacent, critique §21). **Fix:** add `caplog`/`pytest.warns` assertions for the "unused columns" warning and the column-overflow/NaN warnings.

## 22. Pytest configuration

- `testpaths = ["tests"]` is set (good) — but this is exactly why `src/metadata_tools/hosts/GO_0xxx/tests/` are never collected (dead tests). **Fix:** either move host tests under `tests/hosts/` or add their path to `testpaths`.
- `pytest-xdist` present and used; `pytest-randomly` not installed (would catch order dependence). No `pytest.ini`/`setup.cfg` conflict. **Fix (optional):** add `pytest-randomly`.
- Consider adding `-W error` (or the `filterwarnings` table, §16) to `addopts`.

## 23. Snapshot and golden-file testing

- Generating PDS3 tables/labels is exactly the kind of large, structured text output that suits golden-file testing. There are currently **no** golden files for generated output. **Fix:** commit a tiny input fixture and an expected `_supplemental_index.tab`/`.lbl` (or use `syrupy`), and assert byte-for-byte equality (modulo timestamps) so regressions in formatting are caught. Document the update procedure.

---

## Prompt for an AI agent to fix the tests

> You are improving the test suite of `rms-metadata-tools` (src-layout package `metadata_tools`; rules in `.cursor/rules/python_testing.mdc` and `python.mdc`). **Do not change production code** except where a test reveals a bug that `critiques/code_critique.md` already lists — in that case fix per that document, but otherwise only add/restructure tests. Use **pytest** (not `unittest`). All new test functions must be type-annotated (`-> None`).
>
> Context (from this report):
> - Current tests never import `metadata_tools`; they only re-parse files under `$RMS_METADATA`. Coverage of `src` is ~0% though `fail_under = 90`.
> - Tests import-time-depend on `RMS_METADATA`/`RMS_VOLUMES` and pass vacuously when globs match nothing.
> - All tests use `unittest.TestCase` (35 PT009 ruff errors); host tests under `src/.../GO_0xxx/tests/` are never collected; `test_geometry_cumulative` is disabled by a bare `return`.
>
> Tasks:
> 1. **Add a unit layer (top priority for coverage).** Create `tests/test_util.py`, `tests/test_index_support.py`, `tests/test_geometry_format.py`, `tests/test_config_keys.py` that import `metadata_tools` and test pure logic directly with in-memory inputs: `util.add_by_base`, `util.rebase`, `util.sclk_split_count`/`sclk_format_count`, `util.get_volume_glob`, `util.parse_template_name`, `util._get_range_mod360` (cover single-value, full-coverage, and gap branches), `index_support.IndexTable._format_value`/`_format_column`/`_get_null_value`, and `index_config.key__*` functions. Use `@pytest.mark.parametrize` for tabulated cases, assert exact values, and use `pytest.approx` for floats. Aim for ≥90% line coverage measured by `pytest --cov=src --cov-report=term-missing` over the **whole** suite.
> 2. **Add a `tests/conftest.py`** with: a `metadata_root` fixture that returns `Path(os.environ["RMS_METADATA"])` or calls `pytest.skip("RMS_METADATA not set")`; and a `parsed_tables` factory fixture replacing the duplicated `match`/`exclude`/loop pattern. Move the `bounds` helper here, renaming the `min`/`max` params to `min_val`/`max_val`.
> 3. **Convert existing tests to pytest functions** (drop `unittest.TestCase`, replace `self.assertX` with `assert`/`pytest.raises`/`pytest.warns`). Before each archive loop, assert `len(files) > 0` (or skip) so a no-data run cannot pass silently. Fix the convoluted assertion in the host `test_geometry_common` to `assert np.all(table.column_values['VOLUME_ID'] == volume)`. Remove all `print()` calls.
> 4. **Markers & config (`pyproject.toml [tool.pytest.ini_options]`):** register `integration` and `requires_archive` markers; mark the archive-reading tests `requires_archive` and add `-m "not requires_archive"` to the default `addopts` so the unit layer runs fast and hermetic. Add `filterwarnings = ["error"]` plus any narrowly-scoped, commented ignores for third-party warnings.
> 5. **Collect or relocate host tests:** move `src/metadata_tools/hosts/GO_0xxx/tests/` into `tests/hosts/GO_0xxx/` (or add to `testpaths`), and implement or delete the `return`-disabled `test_geometry_cumulative`.
> 6. **Golden-file/integration:** add a minimal committed input fixture under `tests/data/` and an end-to-end test that runs `process_index`/`IndexTable` and asserts the produced `.tab` matches an expected golden file (ignore volatile fields like creation time). Document how to regenerate the golden file.
> 7. **Logging/warnings:** add `caplog` assertions for the "Unused columns" warning (`index_support`) and `pytest.warns` for the NaN/overflow warnings (`geometry_support`).
>
> Finish only when `ruff check tests` is clean of PT009/A002/print-related findings and `pytest --cov=src --cov-report=term-missing` reports ≥90% with the unit tests doing the covering (not the archive tests).
