# Test Suite Critique Report

**Generated:** 2026-07-13
**Scope:** `tests/` (all test files and `conftest.py`)

---

## Executive Summary

The test suite is well-structured, hermetic (runs without SPICE kernels or archive holdings), and
uses robust modern practices: strict markers, `filterwarnings = ["error"]`, `pytest-randomly` for
order-independence, and a clean `conftest.py` with a thoughtful fake-config injection. 290 tests
are defined; 275 are collected in the default run (15 deselected via `integration` and
`requires_archive` markers).

**Coverage:** The `.coverage` file on disk records **22.25%** total line coverage, far below the
`fail_under = 90` target in `pyproject.toml`. However this file appears stale (pre-dates many
recently-added test files). A fresh `pytest --cov=src --cov-report=term-missing` must be run to
measure the true current coverage; if it is genuinely below 90% the build gate will fail and large
portions of engine code are untested.

**Exception messages:** Exception-type assertions (`pytest.raises(SystemExit)` at
`test_cli_host.py:48`) lack a `match=` pattern to verify the error message.

**Top priorities:**

1. Run a fresh coverage measurement; add tests for any modules genuinely below 90%.
2. Add `@pytest.mark.parametrize` throughout — 0 uses across 290 tests is the single largest
   maintainability debt.
3. Add message assertions to bare `pytest.raises` calls.
4. Remove bare `print()` from archive test functions and replace with a purposeful assertion or
   structured logging.

---

## 1. Return values and assertions

**Finding 1.1 — `test_cli_host.py:48`: `pytest.raises(SystemExit)` with no message check.**
Evidence:

```python
def test_pop_argv_flag_no_value_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag'])
    with pytest.raises(SystemExit):   # ← no match=
        pop_argv_flag('--flag')
```

The production code calls `sys.exit(f'{flag} requires a value')`. The test should assert the
message:

```python
with pytest.raises(SystemExit, match='--flag requires a value'):
    pop_argv_flag('--flag')
```

**Finding 1.2 — `columns/conftest.py:33-34`: existence-only assertions in a fixture helper.**

```python
assert spec is not None
assert spec.loader is not None
```

These are guards, not value assertions, in `_load_standalone`. While acceptable as defensive
guards in a helper, the module is not further validated (e.g. that `spec.name == name`). Low
severity, but `_load_standalone` could document the invariant it enforces with a better message:
`assert spec is not None, f"Could not build spec for {name}"`.

**Finding 1.3 — `test_geometry.py:test_inventory` — zero assertions.**
`test_inventory()` reads all `*_inventory.lbl` files and calls `pdsparser.PdsLabel.from_file()`
but discards the result (`_ = ...`). The test passes only if no exception is raised; it does not
assert anything about the parsed content. Similarly `test_supplemental_index__cumulative` in
`test_index.py:18-28` reads a table and assigns to `_ =` with no assertions.

**Suggestion:** Add at minimum `assert label_dict is not None` and a check on a known key, or
document explicitly that "no exception is the contract" with a comment.

---

## 2. Success and failure conditions

**Finding 2.1 — `cli/_host.py:dispatch_cloud_run_if_config` and `run_cloud_worker` are untested.**
`dispatch_cloud_run_if_config` (lines 185–295) launches a subprocess and modifies YAML; it is not
covered by any test. `run_cloud_worker` (lines 343–380) drives `asyncio.run`. Both are
non-trivially complex and have conditional branches (e.g. service account injection, KeyboardInterrupt
handling).

**Suggestion:** Add tests with `monkeypatch` to mock `subprocess.Popen` and `asyncio.run`,
verifying that the correct command is built and returned exit codes propagate.

**Finding 2.2 — `load_host` and `host_dir_for` in `_host.py` are untested.**
`load_host` mutates `sys.argv` and calls `sys.exit` for an unknown host. `host_dir_for` just builds
a path. Neither has a test.

**Suggestion:** Add tests:
```python
def test_load_host_strips_argv_and_returns_host_dir(monkeypatch, tmp_path):
    # create a fake host dir, set sys.argv, call load_host, verify argv and return value
    ...

def test_load_host_exits_on_unknown_host(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match='Unknown host'):
        load_host('NONEXISTENT_HOST')
```

**Finding 2.3 — `util.pds_table` is untested.**
`util.py` exports `pds_table()` (line 22) which calls `FCPath.retrieve()` and `pdstable.PdsTable`.
No test exercises this function.

**Finding 2.4 — `label_support.create` `system` parameter path not tested.**
`label_support.py:create` accepts a `system` argument (for rings and moons) but no test exercises
a non-empty `system`. The `test_label_support.py` tests cover missing-file early return, global
template path, host template path, and inventory preprocessor — but not `system != ''`.

**Finding 2.5 — `cumulative_support.test_create_cumulative_indexes_fires_eight_cat_rows`
only checks count, not the exact set of calls.**
`test_cumulative_support.py:111-122` verifies `len(calls) == 8` and checks two specific entries
(`('SkyTable', 'summary')` and `('IndexTable', 'index')`). It should verify the complete set of
8 table/level pairs to guard against duplicated or wrong entries.

---

## 3. Consistency

**Finding 3.1 — Naming: `test_geometry_record.py` uses `_fake_registry` as a helper function
that is not a fixture.**
`_fake_registry(monkeypatch, mapping)` (line 90) is called at the top of several tests, acting as
a setup helper. The pattern works but is inconsistent with the rest of the suite which uses pytest
fixtures. Consider making it a parametrized fixture or a local helper with a clearer name.

**Finding 3.2 — `_clear_config` in `test_config.py` is a plain function, not a fixture.**
`_clear_config(monkeypatch)` (line 17) is called in every test in the file instead of being
requested as a fixture via a parameter name. This is minor but inconsistent; turning it into a
`@pytest.fixture` (autouse=False) and calling it in an `@pytest.fixture` would be cleaner:

```python
@pytest.fixture
def clear_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cfg, '_host_id', None)
    ...
```

**Finding 3.3 — Archive tests use `print()` for progress output instead of `capsys` or
structured logging.**
`test_geometry.py`, `test_index.py`, `tests/hosts/GO_0xxx/test_geometry.py`,
`tests/hosts/GO_0xxx/test_index.py` all use bare `print()` in their test bodies:

```python
print()
for file in files:
    print('Reading', file)
```

This violates the no-`print` rule from `python.mdc` (which applies to all code, including tests).
These are debug/progress outputs, which have no assertion value. Remove them.

---

## 4. Completeness

**Coverage map (per module, estimated from reading test scope; stale `.coverage` shows 22.25%):**

| Module | Tests | Assessment |
|---|---|---|
| `config.py` | `test_config.py` | Good — all public paths covered |
| `common.py` | `test_common.py` | Good — Table, PathAction, init_logger covered |
| `task_list_support.py` | `test_task_list.py` | Good — all public functions covered |
| `label_support.py` | `test_label_support.py` | Partial — `system` arg untested |
| `util.py` | `test_util_*.py` (5 files) | Partial — `pds_table`, `sclk_to_ticks`, `read_txt_file` async paths untested |
| `cumulative_support.py` | `test_cumulative_support.py` | Partial — `volumes` filter in `_cat_rows` untested |
| `index_support/` | `test_index_support.py` | Good — major paths covered |
| `geometry_support/formatting.py` | `test_geometry_formatting.py` | Good |
| `geometry_support/masks.py` | `test_geometry_masks.py` | Good |
| `geometry_support/prep.py` | `test_geometry_prep.py` | Good |
| `geometry_support/record.py` | `test_geometry_record.py` | Good |
| `geometry_support/tables.py` | `test_geometry_tables.py` | Good |
| `geometry_support/suite.py` | `test_geometry_tables.py`, `test_geometry_constructors.py` | Good for public API |
| `geometry_support/bodies_select.py` | `test_geometry_constructors.py`, `test_geometry_record.py` | Partial — `obs_excluded` with identifier path |
| `cli/_host.py` | `test_cli_host.py` | Partial — `dispatch_cloud_run_if_config`, `run_cloud_worker`, `load_host` not covered |
| `cli/index.py`, `geometry.py`, `cumulative.py`, `*_cloud.py`, `*_worker.py` | None | Excluded from coverage denominator, but `main()` entry points are entirely untested |
| `columns/` | `test_columns_integration.py` (excluded by default), `columns/test_ring.py`, `test_sky.py`, `test_sun.py` | Good |
| `bodies.py` | None | Excluded from coverage (SPICE-dependent) |

**Finding 4.1 — `util.py:sclk_to_ticks` is never directly tested.**
The function is monkeypatched out in `test_util_math.py` and `test_geometry_record.py` but never
called directly in tests. Add a test using a minimal SPICE stub or confirm it's covered via the
integration tier.

**Finding 4.2 — `cumulative_support._cat_rows` `volumes` filter path untested.**
`_cat_rows` accepts a `volumes` keyword argument (only processes listed volumes) but no test
exercises this path. The `exclude` path IS tested.

---

## 5. Redundancy

**Finding 5.1 — `test_config.py:28-49` — four nearly identical "unregistered" tests.**

```python
def test_current_host_id_raises_when_not_registered(monkeypatch): ...
def test_get_host_config_raises_when_not_registered(monkeypatch): ...
def test_get_index_config_raises_when_not_registered(monkeypatch): ...
def test_get_geometry_config_raises_when_not_registered(monkeypatch): ...
```

All four share an identical pattern: clear config → call function → assert `RuntimeError` with the
same message. These should be parametrized:

```python
@pytest.mark.parametrize('fn', [
    cfg.current_host_id,
    cfg.get_host_config,
    cfg.get_index_config,
    cfg.get_geometry_config,
])
def test_raises_when_not_registered(fn, monkeypatch):
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        fn()
```

**Finding 5.2 — `test_geometry_masks.py` — 13 tests with similar body/shadow/face structure.**
All 13 tests create a fresh `FakeBackplane`, set one attribute, call `construct_excluded_mask`,
and assert one value. The differences are: mask type, body/primary, flags tuple, attribute set.
These are ideal candidates for `@pytest.mark.parametrize`.

**Finding 5.3 — `test_cli_host.py:build_startup_script` tests — 10 tests, near-identical setup.**
Lines 141–304 contain 10 tests for `build_startup_script`. Each creates a temp file, sets
`sys.argv` to `['cmd', 'gs://bucket/vol/']`, sets env vars, and calls `build_startup_script`. Only
the env vars and kwargs differ. The test file setup (writing `tpl.write_text('echo hello\n')`) is
repeated in 9 of 10 tests. A parametrize approach or a shared fixture would eliminate the
duplication.

**Finding 5.4 — `test_geometry_process.py` — three tests, identical `FakeSuite` pattern.**
Tests at lines 46, 66, 85 each define a local `FakeSuite` class and call
`proc.process_tables(...)`. The class definitions differ only in what they record. A single shared
parametrized pattern would be cleaner.

---

## 6. Parallel execution

**Finding 6.1 — `conftest.py:_install_fakes()` is called at module-import time (line 52), setting
module-level state in `metadata_tools.config`.**
This is correct for the entire-suite approach: the fake config is installed once before any test
runs. Under `pytest-xdist -n auto` with process-level workers this is safe because each worker
gets its own interpreter. Under thread-based parallelism (not used here) it would not be.
**Assessment:** safe as currently configured.

**Finding 6.2 — `test_util_math.py:127`: `np.random.seed(0)` sets global NumPy random state.**

```python
def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
    np.random.seed(0)   # ← global legacy RNG
    result = util.range_of_n_angles(5, tests=200)
```

`np.random.seed()` modifies the global legacy random state. Under parallel execution (`-n auto`),
this leaks into other tests running in the same worker. Use the `rng`-based API instead:

```python
def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
    rng = np.random.default_rng(0)
    # pass rng to the function, or seed before calling if the function uses np.random
```

If `util.range_of_n_angles` calls `np.random` internally, consider adding an `rng` parameter to
the production function so callers can inject the random state.

---

## 7. Mocking and dependency isolation

**Finding 7.1 — `test_geometry_tables.py:test_suite_create_processes_observations` and
`test_suite_create_skips_glob_mismatch` — logger mock lacks `open` method.**
The mock at line 235 (and 257) is:

```python
monkeypatch.setattr(com, 'get_logger',
    lambda: types.SimpleNamespace(
        info=lambda *a, **k: None, warning=lambda *a, **k: None,
        close=lambda: None))
```

`suite.create()` calls `logger.info(...)`, `logger.warning(...)`, and `logger.close()` — all
present. However any future modification to `suite.create()` that calls `logger.open(...)` or
`logger.error(...)` would produce an `AttributeError` rather than a test failure. Consider using
`unittest.mock.MagicMock()` as the logger stand-in so any method call succeeds:

```python
import unittest.mock
monkeypatch.setattr(com, 'get_logger', unittest.mock.MagicMock)
```

**Finding 7.2 — `test_cli_host.py` imports private module `metadata_tools.cli._host`.**

```python
import metadata_tools.cli._host as _host_mod
from metadata_tools.cli._host import (
    _strip_cloud_args,
    build_startup_script,
    pop_argv_flag,
    ...
)
```

This is a deliberate, appropriate choice (the test file is specifically for `_host.py`), but
per `python_testing.mdc` section 20, importing `_`-prefixed names from tests creates tight
coupling. A public re-export from `metadata_tools.cli` would decouple the test from the private
module layout. Low severity given the deliberate 1:1 mapping.

**Finding 7.3 — No tests for the `async` path in `run_cloud_worker`.**
`run_cloud_worker` (lines 343–380 in `_host.py`) calls `asyncio.run(_run())` and catches
`KeyboardInterrupt`. No test mocks `cloud_tasks.worker.Worker` to exercise this path.

**Finding 7.4 — `test_geometry_constructors.py` — `monkeypatch.setattr` targets reference the
production module's own namespace correctly.**
The `monkeypatch.setattr(bodies_select, 'inventory', ...)` targets the module attribute directly
(where the name is looked up), which is correct. No patch-target issues found.

---

## 8. Security and input validation

**Finding 8.1 — No tests for `pop_argv_flag` with adversarial or special-character flag values.**
`pop_argv_flag` is used to extract `--debug-branch` from the command line; that value is later
embedded in a shell script via `shlex.quote`. The quoting is tested only implicitly. A test with a
flag value containing spaces or shell metacharacters would validate the `shlex.quote` path.

**Finding 8.2 — `dispatch_cloud_run_if_config` uses `subprocess.Popen` with `shell=False` but
no test verifies the command-list assembly.**
Without a test, a future regression in `modified_cloud_args` assembly (e.g. inserting a `None`)
would only surface at runtime.

No credential leakage or path traversal issues found in the test suite itself.

---

## 9. Parameterization

**Finding 9.1 — Zero uses of `@pytest.mark.parametrize` across 290 tests.**

This is the single largest maintainability gap. Copy-pasted test bodies hide failures in
individual cases. The following groups should be parametrized:

| Group | File | Lines | # cases |
|---|---|---|---|
| `add_by_base` variants | `test_util_math.py` | 14–29 | 4 |
| `_ninety_percent_gap_degrees` variants | `test_util_range_mod360.py` | 13–25 | 3 |
| `_get_range_mod360` variants | `test_util_range_mod360.py` | 31–68 | 7 |
| `replace` variants | `test_util_replace.py` | 16–91 | 9 |
| unregistered-config errors | `test_config.py` | 28–49 | 4 |
| `format_value` variants | `test_index_support.py` | 37–47 | 3 |
| `format_parms` variants | `test_index_support.py` | 51–62 | 3 |
| `get_null_value` variants | `test_index_support.py` | 68–89 | 4 |
| `formatted_column` variants | `test_geometry_formatting.py` | 17–75 | 8 |
| `circle_coverage` variants | `test_geometry_formatting.py` | 81–105 | 4 |
| mask variants | `test_geometry_masks.py` | 22–133 | 13 |
| `build_startup_script` variants | `test_cli_host.py` | 141–304 | 10 |

**Finding 9.2 — Boundary tests missing for `sclk_split_count` pad-to-four field.**
`test_sclk_split_count_pads_to_four_fields` checks the 3-field → 4-field pad path, but there is
no test for 2-field or 1-field inputs (or 5-field inputs, which should truncate or raise).

**Finding 9.3 — No boundary test for `write_txt_file` with an empty list.**
`test_util_textfile.py` tests non-empty lists and strings but not `write_txt_file(path, [])`.

---

## 10. Async (not applicable)

No async tests. The async `run_cloud_worker` function is not tested at all (see Finding 7.3).

---

## 11. Output and contract

**Finding 11.1 — `test_geometry_tables.py:test_record_add_named_column_dict` — assertion uses
`endswith` instead of exact match.**

```python
assert lines[0].endswith('  28.648,  57.296')
```

The prefix before the data is not asserted. Since `record_stub` has `prefixes=['"vol"', '"file"']`,
the full expected value is `'"vol","file",  28.648,  57.296'`. Use an exact assertion:

```python
assert lines[0] == '"vol","file",  28.648,  57.296'
```

**Finding 11.2 — `test_columns_integration.py:test_body_summary_dict_is_populated` only checks
`len() > 0`.**

```python
assert len(col.get_body_summary_dict()) > 0
```

Should assert the exact expected key count (matching the number of configured bodies in
`defs.BODY_NAMES`) or at least a minimum:

```python
import metadata_tools.defs as defs
assert set(col.get_body_summary_dict().keys()) == set(defs.BODY_NAMES)
```

---

## 12. Error handling

**Finding 12.1 — `test_cli_host.py:48`: `pytest.raises(SystemExit)` without `match=`.**
See Finding 1.1. When the error code is wrong (e.g. a different `sys.exit` call fires), the test
still passes. Adding `match='--flag requires a value'` catches this regression.

**Finding 12.2 — `test_geometry_constructors.py:test_inventory_other_error_returns_empty` —
only checks return value, not that `pointing_available` is unchanged.**
`inventory()` for a non-`CKINSUFFDATA` exception returns `[]` but should NOT clear
`pointing_available`. The test asserts the return value but not that `record.pointing_available`
remains `True`. Add:

```python
assert record.pointing_available is True  # other errors don't clear pointing
```

---

## 13. State and workflow

**Finding 13.1 — `test_index_support.py:test_create_index_processes_each_volume` verifies that
the unused-column warning contains the cross-volume intersection `{'COLA'}`, but does not verify
the warning message format.**

The test checks `assert warnings == [{'COLA'}]` which means the `warning()` method received the
set `{'COLA'}` as its second argument. This is correct. No finding.

**Finding 13.2 — No idempotency test for `conftest._install_fakes()`.**
If `set_current()` is called twice with different hosts (e.g. if tests are collected in multiple
workers that both call `_install_fakes()`), the second call silently overwrites. There is no test
verifying that double-registration behaves correctly or is prevented.

---

## 14. Test data and fixtures

**Finding 14.1 — `tests/columns/conftest.py` `ring_module`, `sky_module`, `sun_module` are
`scope='session'` fixtures — but they load submodules that include mutable state.**
Loading a module via `importlib.util.spec_from_file_location` at session scope means changes to
the module object (e.g. if any test mutates `ring_module.RING_SUMMARY_DICT`) would leak across
tests. Current tests only read from these modules, so this is not a current problem, but the
broad scope is risky.

**Finding 14.2 — `test_cli_host.py:141–304` — ten tests each write their own temp file with the
same content `'echo hello\n'`.**
A shared `@pytest.fixture` for the startup-template temp file would eliminate this duplication:

```python
@pytest.fixture
def startup_template(tmp_path: Path) -> Path:
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    return tpl
```

**Finding 14.3 — `tests/archive_support.py:exclude` uses `range(len(files))` instead of direct
iteration.**

```python
for i in range(len(files)):
    ...
    if files[i].find(pattern) != -1:
```

This is a Python anti-pattern. Rewrite as:

```python
for f in files:
    if any(pattern in f for pattern in patterns):
        result.append(f)
```

(Low severity; correctness not affected.)

**Finding 14.4 — `conftest.py:silent_logger` fixture name implies it returns a logger, but it
returns `None`.**
Tests request `silent_logger: None` in their signature (e.g. `test_cumulative_support.py:24`)
which is correct but unusual. Rename to `suppress_logger` or use `autouse` on a narrowly-scoped
fixture to avoid cluttering signatures.

---

## 15. Flakiness indicators

**Finding 15.1 — `test_util_math.py:127`: `np.random.seed(0)` — global random state mutation.**
See Finding 6.2. This is a flakiness risk under parallel execution.

**Finding 15.2 — `test_geometry_formatting.py:test_iso_route` — the expected ISO string encodes
hard-coded UTC offset.**

```python
assert result == '"2000-01-01T11:59:28.000","2000-01-01T12:00:28.000"'
```

This assumes a fixed UTC→TDB offset. If the underlying `julian` library changes its epoch or
conversion formula, this test will fail. The value is deterministic but fragile. A tolerance-based
comparison (or deriving the expected string from the same `julian` call) would be more robust.

---

## 16. Regression and documentation

**Finding 16.1 — `test_geometry_columns_contract.py` documents its regression story well** — the
docstring explains the original typo bug (`RING_SUMMARY_DETAILED`, `BODY_SUMMARY_DETAILED`,
`BODYX`). This is a model for how regression tests should be written.

**Finding 16.2 — `test_cli_host.py:test_build_startup_empty_startup_template_env_uses_default`
has a docstring documenting the regression.**

```python
"""Regression: GCP_STARTUP_TEMPLATE='' must not be passed to Path()."""
```

Good practice; all regression tests should carry this annotation.

**Finding 16.3 — `filterwarnings = ["error"]` IS configured in `pyproject.toml:69-71`.** Good.

**Finding 16.4 — `--strict-markers` IS configured in `pyproject.toml:64`.** Good.

**Finding 16.5 — `pytest-randomly` IS declared in dev dependencies.** Good.

**Finding 16.6 — No deprecated APIs are used in the test suite itself.** No `filterwarnings`
suppression of `DeprecationWarning` is needed. Good.

---

## 17. Other

**Finding 17.1 — `test_geometry.py` and archive tests use bare `print()` in test bodies.**
`test_geometry.py:26,30,35,48,66,71,86,95,128,135,165,171` and similar in
`tests/hosts/GO_0xxx/test_geometry.py` use `print()` for progress. These are never asserted.
Remove them. If progress logging is genuinely needed, use `capsys` or a logger fixture.

**Finding 17.2 — Test naming in `test_geometry_tables.py` is sometimes terse.**
`test_record_add_builds_summary_line` (line 109) and `test_record_add_named_column_dict` (line
121) both test `Record.add` but neither name includes the condition. Prefer:
`test_record_add_sky_qualifier_builds_formatted_row`.

**Finding 17.3 — `test_geometry_prep.py:test_detailed_subregions_emit_rows` asserts on
`.strip().isdigit()` which is non-specific.**

```python
assert rows[0][-2].strip().isdigit()
```

This only verifies the column is a digit string, not what the digit is. Assert the exact expected
subregion index:

```python
assert rows[0][-2].strip() == '0'   # first (and only) subregion
```

**Finding 17.4 — `test_geometry_prep.py:test_multiple_tile_sets_tuple_emits_a_row_per_set`
docstring references a specific bug fix ("TypeError") but has no issue link.**

**Finding 17.5 — `test_cli_host.py:test_volumes_as_task_file_rewrites_argv_inside_block` reads
the task file inside the `with` block and parses JSON (good), but `test_single_task_as_task_file_
injects_task_file` also reads the file inside the block — this is correct because the temp file
exists only within the `with` block.**

---

## 18. Code coverage

**Target:** 90% line coverage (configured in `pyproject.toml:165`; `fail_under = 90`).

**Status:** The `.coverage` file on disk records **22.25%** total coverage. This is almost
certainly stale — the file predates many recently-added test modules (`test_geometry_formatting.py`,
`test_geometry_masks.py`, `test_geometry_prep.py`, etc. cover modules the stale report marks near
zero). A fresh measurement is required before conclusions can be drawn.

**Measurement command:**
```bash
source venv/bin/activate
pytest tests/ --cov=src --cov-report=term-missing -n auto
```

Modules excluded from coverage denominator (correct, per `pyproject.toml:151-157`):
- `tests/*`
- `*/_version.py`
- `*/metadata_tools/bodies.py`
- `*/metadata_tools/hosts/*`
- `*/metadata_tools/cli/*`

**Known gaps not in denominator but worth integration-testing:**
- `cli/index.py`, `cli/geometry.py`, `cli/cumulative.py`, `cli/*_cloud.py`, `cli/*_worker.py`
- `hosts/GO_0xxx/*` (config, geometry_config, index_config, host_init)

---

## 19. Pytest markers

**All custom markers ARE registered** in `pyproject.toml:65-68`:
```toml
markers = [
  "integration: requires oops/SPICE host initialization (excluded by default)",
  "requires_archive: requires the $RMS_METADATA holdings tree (excluded by default)",
]
```

**`--strict-markers` IS enabled** via `addopts`. Good.

**Finding 19.1 — `columns/test_columns_integration.py:14` uses `pytestmark = pytest.mark.integration`
correctly.** Tests are properly excluded by default.

**Finding 19.2 — No `slow` marker is used.** Some geometry tests with heavy `monkeypatch` setups
(e.g. `test_geometry_constructors.py:test_suite_init_builds_tables_and_meshgrids`) take longer
than pure-logic tests. Adding a `slow` marker for tests that require many patches would allow
`pytest -m "not slow"` to run an even faster subset.

**Finding 19.3 — No `xfail` markers.** Good — no known-broken tests.

**Finding 19.4 — No stale `skip`/`skipif` markers.** Good.

---

## 20. Test boundary (public API vs internals)

**Finding 20.1 — `test_cli_host.py:14-21` imports private `_host` module functions.**

```python
import metadata_tools.cli._host as _host_mod
from metadata_tools.cli._host import (
    _strip_cloud_args,
    build_startup_script,
    ...
)
```

`_strip_cloud_args` is a module-private helper (single underscore prefix) being imported directly.
The tests are appropriate given the file is specifically `test_cli_host.py`, but if `_host.py` is
renamed or the helper is inlined, the test breaks. Consider re-exporting public-ish helpers from
`metadata_tools.cli` or accepting this coupling as intentional.

**Finding 20.2 — `test_index_support.py` accesses `IndexTable._format_value`, `_format_parms`,
`_get_null_value`, `_get_column_values`, `_format_column`, `_index_one_value` directly.**
All are private methods (single underscore). These tests exercise implementation details. A
refactor that merges two of these methods would break the tests without breaking the public
API. However, given that `IndexTable` is itself a complex internal class, this is an accepted
practice. Document in the test file that these tests are white-box tests of the formatting logic.

**Finding 20.3 — `test_geometry_record.py:140-146` — `test_record_init_detailed_selects_detailed_dicts`
asserts `record.dicts['ring'] is col.RING_DETAILED_DICT`.**
This asserts the internal `dicts` attribute structure, which is private to `Record`. If the
internal representation changes (e.g., renamed key), the test breaks. Medium severity.

---

## 21. Logging assertions

**Finding 21.1 — No `caplog` usage anywhere in the test suite.**
`caplog` is a pytest built-in for capturing stdlib `logging` output. This project uses
`pdslogger.PdsLogger` (not stdlib `logging`), so `caplog` would not capture any messages even if
used. This is a PdsLogger limitation, not a test deficiency.

**Finding 21.2 — The `silent_logger` fixture suppresses PdsLogger output but does not verify it.**
`test_cumulative_support.py` and `test_index_support.py` use `silent_logger` to suppress output
but no test verifies that the logger IS called (e.g. that a "Building Cumulative" info message is
emitted). If the logger call were removed from `_cat_rows`, no test would catch it.

**Suggestion:** Since PdsLogger cannot be captured via `caplog`, use `monkeypatch` to replace
`get_logger()` with a `unittest.mock.MagicMock` and assert `.info.call_count > 0` or specific
`.info.call_args` values:

```python
def test_cat_rows_logs_progress(monkeypatch, tmp_path, silent_logger):
    import unittest.mock
    mock_logger = unittest.mock.MagicMock()
    monkeypatch.setattr(com, 'get_logger', lambda: mock_logger)
    cum._cat_rows(...)
    mock_logger.info.assert_called()
```

---

## 22. Pytest configuration

**`pyproject.toml` `[tool.pytest.ini_options]`:**

```toml
pythonpath = ["src"]         ✓
testpaths = ["tests"]        ✓
addopts = ["-n", "auto", "--cov=src", "--strict-markers", "--strict-config",
           "-m", "not integration and not requires_archive"]
markers = [...]              ✓
filterwarnings = ["error"]   ✓
```

**Finding 22.1 — `addopts` includes `--strict-config` but NOT `--strict-ini`.**
`--strict-config` (available since pytest 6.2) promotes ini-file warnings to errors, which is
correct. No issue.

**Finding 22.2 — `pytest-randomly` is in dev deps but no `--randomly-seed` is pinned in CI.**
`pytest-randomly` randomizes test order, which is good. But CI should capture and log the random
seed so failing runs can be reproduced deterministically (`--randomly-seed last`).

**Finding 22.3 — `--cov=src` in `addopts` collects coverage even during `--co` (collect-only)
runs, which pollutes output with coverage headers.**
This is a minor UX annoyance; separate coverage invocations with `--no-cov` for quick collect
checks: `pytest --co --no-cov`.

**Installed plugins detected in `pyproject.toml` dev dependencies:**
- `pytest>=7.0` ✓
- `pytest-cov>=4.0` ✓
- `pytest-randomly>=3.0` ✓
- `pytest-xdist>=3.8.0` ✓

**Finding 22.4 — No `pytest-timeout` in dev dependencies.**
Tests that call real oops/SPICE functions (archive/integration tier) could hang if kernel loading
blocks. Adding `pytest-timeout` with a per-test default would catch hangs in CI.

---

## 23. Snapshot and golden-file testing

No snapshot or golden-file tests exist. For the geometry formatting tests
(`test_geometry_formatting.py`), the expected formatted strings are short enough to assert inline,
so snapshot testing is not needed. The archive-backed tests (`test_geometry.py`,
`test_index.py`) are the closest to golden-file tests — they compare column types and value bounds
against pre-generated data, which is appropriate.

---

## Prompt for an AI agent to fix tests

You are fixing the test suite of `rms-metadata-tools` (package `metadata_tools`) based on the
critique report above. The source is in `src/metadata_tools/`. Tests are in `tests/`. **Do not
modify any production code** in `src/`. Only add, modify, or remove lines in `tests/`.

Preserve all existing passing tests (do not delete or weaken assertions). Add or strengthen
assertions, add parametrize, add new test functions, and fix the issues described below.

### Working directory
`/home/spitale/rms-/rms-metadata-tools`

### Setup
```bash
source venv/bin/activate
pytest tests/ --cov=src --cov-report=term-missing -n auto 2>&1 | tail -30
```

---

### Fix 1 — Add `match=` to `pytest.raises(SystemExit)` without a message

**File:** `tests/test_cli_host.py`, line 48

```python
# CURRENT (bad):
with pytest.raises(SystemExit):
    pop_argv_flag('--flag')

# FIXED:
with pytest.raises(SystemExit, match='--flag requires a value'):
    pop_argv_flag('--flag')
```

**Why:** The production code calls `sys.exit(f'{flag} requires a value')`. Without `match=`, any
`SystemExit` (including from an unrelated error) passes the test.

---

### Fix 2 — Add `@pytest.mark.parametrize` to the four unregistered-config tests

**File:** `tests/test_config.py`, lines 28–49

Replace the four separate test functions with:

```python
import metadata_tools.config as cfg

_NOT_REGISTERED = r'set_host\(\) has not been called'


@pytest.mark.parametrize('fn', [
    cfg.current_host_id,
    cfg.get_host_config,
    cfg.get_index_config,
    cfg.get_geometry_config,
], ids=['current_host_id', 'get_host_config', 'get_index_config', 'get_geometry_config'])
def test_raises_when_not_registered(fn: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """All getters raise RuntimeError when no host is registered."""
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match=_NOT_REGISTERED):
        fn()
```

Delete the original four functions. Add `from typing import Any` if not already imported.

---

### Fix 3 — Remove bare `print()` from archive test bodies

**Files:**
- `tests/test_geometry.py` — lines 26, 29, 35, 48, 68, 72, 88, 96, 126, 134, 166, 174
- `tests/test_index.py` — lines 25, 27, 41, 44
- `tests/hosts/GO_0xxx/test_geometry.py` — lines 20, 29, 39, 48, 58, 66
- `tests/hosts/GO_0xxx/test_index.py` — lines 19, 28, 30

Delete all bare `print()` calls in test function bodies. Replace `print()` (blank) and
`print('Reading', file)` with nothing — the iteration still validates the data via `assert`
statements that follow.

For example, in `test_geometry.py::test_geometry_body`:
```python
# REMOVE these lines:
print()
for file in files:
    print('Reading', file)
    table = pdstable.PdsTable(file)
    ...

# KEEP (just remove the prints):
for file in files:
    table = pdstable.PdsTable(file)
    ...
```

---

### Fix 4 — Add an assertion to `test_inventory` (archive test)

**File:** `tests/test_geometry.py`, lines 19–30

```python
def test_inventory() -> None:
    files = support.match(support.METADATA, '*_inventory.lbl')
    files = support.exclude(files, 'templates/', 'old/', '__skip/')
    for file in files:
        label_dict = pdsparser.PdsLabel.from_file(file).as_dict()
        # Verify the label parses and contains at least one key.
        assert label_dict, f'Empty label dict in {file}'
```

Change the `_ = pdsparser.PdsLabel.from_file(file)` line to actually assert on the result.

---

### Fix 5 — Add an assertion to `test_supplemental_index__cumulative`

**File:** `tests/test_index.py`, lines 18–29

```python
def test_supplemental_index__cumulative() -> None:
    files = support.match(support.METADATA, '*_0999_supplemental_index.lbl')
    files = support.exclude(files, 'templates/', 'old/', '__skip/')
    for file in files:
        table = pdstable.PdsTable(file)
        assert table.info.rows > 0, f'Cumulative table has no rows: {file}'
        assert 'VOLUME_ID' in table.column_values, f'Missing VOLUME_ID in {file}'
```

---

### Fix 6 — Replace `np.random.seed(0)` with `rng`-based approach

**File:** `tests/test_util_math.py`, lines 124–129

```python
def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
    """range_of_n_angles is deterministic when the global RNG is seeded."""
    # Legacy seed: np.random.seed(0) is a global mutation; use the
    # new Generator API if util.range_of_n_angles supports it, otherwise
    # seed the legacy state immediately before the call and document why.
    np.random.seed(0)   # nosec — seeds legacy RNG; util.range_of_n_angles uses np.random
    result = util.range_of_n_angles(5, tests=200)
    assert result == pytest.approx(125.7494161526109)
```

If `util.range_of_n_angles` can be modified to accept an `rng` parameter, do that in production
code and update the test:
```python
def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
    rng = np.random.default_rng(0)
    result = util.range_of_n_angles(5, tests=200, rng=rng)
    # Update the expected value after adding the rng parameter.
    assert isinstance(result, float)
    assert 100.0 < result < 200.0  # reasonable range
```

---

### Fix 7 — Strengthen `test_record_add_named_column_dict` assertion

**File:** `tests/test_geometry_tables.py`, line 130

```python
# CURRENT:
assert lines[0].endswith('  28.648,  57.296')

# FIXED:
assert lines[0] == '"vol","file",  28.648,  57.296'
```

---

### Fix 8 — Add missing assertion to `test_inventory_other_error_returns_empty`

**File:** `tests/test_geometry_constructors.py`, lines 47–55

After the return value assertion, add:
```python
assert bodies_select.inventory(record, ['IO']) == []
assert record.pointing_available is True  # non-CKINSUFFDATA errors leave pointing unchanged
```

The current test only checks the return value; it should also verify that `pointing_available` is
not cleared for non-`CKINSUFFDATA` errors.

---

### Fix 9 — Strengthen `test_detailed_subregions_emit_rows` subregion assertion

**File:** `tests/test_geometry_prep.py`, line 183

```python
# CURRENT:
assert rows[0][-2].strip().isdigit()

# FIXED:
assert rows[0][-2].strip() == '0'   # first (and only) subregion index is 0
```

---

### Fix 10 — Add `match=` to `test_geometry_constructors.py:test_suite_init_multiple_indexes_raises`
(already has `match=` — no change needed). Verify existing message text.

**File:** `tests/test_geometry_constructors.py`, line 174 — already has
`pytest.raises(RuntimeError, match='index files')`. Good.

---

### Fix 11 — Add a startup-template fixture to `test_cli_host.py`

**File:** `tests/test_cli_host.py`

Add at the top of the file, after imports:

```python
@pytest.fixture
def startup_tpl(tmp_path: Path) -> Path:
    """A minimal startup template for build_startup_script tests."""
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    return tpl
```

Then replace the repeated `tpl = tmp_path / 'startup.sh'; tpl.write_text('echo hello\n')` in
each of the 9 `test_build_startup_*` tests with `startup_tpl` as a fixture parameter. Update each
function signature to accept `startup_tpl: Path` and replace `str(tpl)` with `str(startup_tpl)`.

---

### Fix 12 — Add tests for `load_host` in `_host.py`

**File:** `tests/test_cli_host.py` — add new test functions:

```python
def test_load_host_returns_host_dir_and_strips_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_host removes HOST_ID from sys.argv and returns the host directory."""
    monkeypatch.setattr(sys, 'argv', ['cmd', 'GO_0xxx', 'arg1'])
    host_dir = _host_mod.load_host('GO_0xxx')
    assert host_dir.name == 'GO_0xxx'
    assert 'GO_0xxx' not in sys.argv
    assert sys.argv == ['cmd', 'arg1']


def test_load_host_exits_for_unknown_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_host calls sys.exit when the host directory does not exist."""
    monkeypatch.setattr(sys, 'argv', ['cmd', 'INVALID_HOST', 'arg1'])
    with pytest.raises(SystemExit, match='Unknown host'):
        _host_mod.load_host('INVALID_HOST')
```

---

### Fix 13 — Add a test for `_cat_rows` with the `volumes` filter

**File:** `tests/test_cumulative_support.py` — add after `test_cat_rows_skips_missing_table`:

```python
def test_cat_rows_filters_to_specified_volumes(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """_cat_rows only processes volumes listed in `volumes`."""
    root = tmp_path / 'GO_0xxx'
    for vol, line in [('GO_0001', 'a'), ('GO_0002', 'b'), ('GO_0003', 'c')]:
        vdir = root / vol
        vdir.mkdir(parents=True)
        (vdir / f'{vol}_sky_summary.tab').write_text(line + '\r\n', encoding='utf-8')
    cumulative_dir = root / 'GO_0999'
    cumulative_dir.mkdir()
    monkeypatch.setattr(hconf, 'get_volume_id', lambda p: FCPath(p).name)
    written: dict[str, Any] = {}
    monkeypatch.setattr(util, 'write_txt_file',
                        lambda path, content: written.update({'content': content}))
    monkeypatch.setattr(lab, 'create', lambda *a, **k: None)
    cum._cat_rows(FCPath(root), FCPath(cumulative_dir), FCPath('/tmpl.lbl'),
                  'GO_0[0-9][0-9][0-9]', geom.SkyTable(level='summary'),
                  volumes=['GO_0001', 'GO_0003'])
    assert written['content'] == ['a', 'c']  # GO_0002 excluded
```

---

### Fix 14 — Add exact-call-set assertion to `test_create_cumulative_indexes_fires_eight_cat_rows`

**File:** `tests/test_cumulative_support.py`, lines 111–122

After `assert len(calls) == 8`, add:

```python
expected = {
    ('IndexTable', 'index'),
    ('InventoryTable', None),
    ('SkyTable', 'summary'),
    ('SkyTable', 'detailed'),
    ('RingTable', 'summary'),
    ('RingTable', 'detailed'),
    ('BodyTable', 'summary'),
    ('BodyTable', 'detailed'),
}
assert set(calls) == expected
```

(Adjust the exact set if the production code differs — run the test first to see what `calls`
contains.)

---

### Fix 15 — Run coverage and ensure ≥90%

After applying the above fixes, run:
```bash
pytest tests/ --cov=src --cov-report=term-missing -n auto
```

If any module shows coverage below 90%, add targeted tests for the uncovered branches. The most
likely gaps are:
- `util.pds_table` — needs a test that stubs `pdstable.PdsTable`
- `label_support.create` with `system != ''` — add a test varying the `system` parameter
- `cli/_host.py:dispatch_cloud_run_if_config` — add a test mocking `subprocess.Popen` and `yaml`
- `cumulative_support._cat_rows` with `volumes` filter — covered by Fix 13 above

Do not modify `src/` production code to raise coverage; only add tests.
