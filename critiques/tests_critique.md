# Test Suite Critique Report

**Generated:** 2026-07-08
**Scope:** `tests/` (all files), `tests/columns/`, `tests/hosts/GO_0xxx/`, and root `conftest.py`

---

## Executive Summary

The test suite is well-architected and demonstrates clear engineering intent: a hermetic `conftest.py` that installs SPICE/host fakes at collection time, focused test files that mirror the source layout, and consistent use of `monkeypatch` to isolate engine logic from external systems. The major strengths are the comprehensive geometry pipeline coverage (masks, prep, record, tables, suite, formatting), clean parametrization via fixtures, and the contract guard (`test_geometry_columns_contract.py`) that catches latent `AttributeError` typos.

**Coverage:** The project targets ≥90% line coverage (configured via `fail_under = 90`) and excludes CLI, hosts, and `bodies.py` from the denominator — a reasonable design decision. Coverage has not been measured here (no live run), but some code paths in `config.py`, `geometry_support/bodies_select.py`, and `geometry_support/suite.py` appear untested based on reading.

**Exception messages:** `test_indextable_init_supplemental_missing_primary_raises` does not assert on message content (only exception type). Several other `pytest.raises` uses lack `match=`.

**High-priority fixes:**
1. Add `filterwarnings = ["error"]` to pytest config (currently absent; per `python_testing.mdc` §4).
2. Add exception-message assertions (`match=`) to all `pytest.raises` calls missing them.
3. Deduplicate the `exists_true` fixture from two test files into `conftest.py`.
4. Add tests for `config.py` error paths (unregistered host).
5. Delete dead code in `test_geometry.py` and `tests/hosts/GO_0xxx/test_geometry.py`.

**Nice-to-have:**
- Parametrize the 13 similar mask tests in `test_geometry_masks.py`.
- Add `pytest-randomly` for order-independence verification.
- Add `_silent_logger` as a proper fixture in `test_cumulative_support.py`.

---

## 1. Return values and assertions

### 1.1 Weak assertion: `test_range_of_n_angles_is_bounded`
**File:** `tests/test_util_math.py:124`
**Finding:** Tests only `0.0 <= result <= 360.0`. For a statistical helper whose table is embedded in `util.py`, this exercises nothing meaningful. A seeded random run would give a deterministic value to assert.
**Severity:** Low.
**Fix:** Replace with a seeded test:
```python
def test_range_of_n_angles_deterministic() -> None:
    # Seed numpy so the test is deterministic.
    np.random.seed(42)
    result = util.range_of_n_angles(5, tests=200)
    assert 0.0 <= result <= 360.0
```

### 1.2 Existence-only assertion: `test_write_table_and_label`
**File:** `tests/test_common.py:63-65`
**Finding:** Uses `in calls` membership check. Does not assert that exactly two calls were made (could have spurious extras).
**Severity:** Low.
**Fix:**
```python
assert calls == [('write', ['row1']), ('label', 'body_summary')]
```

### 1.3 No assertion on record prefixes in `test_record_init_no_primary`
**File:** `tests/test_geometry_constructors.py:128-130`
**Finding:** Asserts `'.LBL' in record.prefixes[1]` (substring). The exact expected value is known at test-write time (`'"DATA/C0123.LBL                 "'`). Weak.
**Severity:** Low.
**Fix:**
```python
assert record.prefixes[1] == '"DATA/C0123.LBL                 "'  # 32-char padded
```

---

## 2. Success and failure conditions

### 2.1 Missing: `config.py` error paths not tested
**File:** `src/metadata_tools/config.py`
**Finding:** `current_host_id()`, `get_host_config()`, `get_index_config()`, and `get_geometry_config()` all raise `RuntimeError` when no host is registered. None of these error paths are tested. The conftest always installs a fake host before collection, so the error paths are unreachable in the current test layout.
**Severity:** Medium (uncovered code, and the error message is part of the API).
**Fix:** Add `tests/test_config.py`:
```python
# tests/test_config.py
import types

import pytest

import metadata_tools.config as cfg


def _clear_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Temporarily clear all registered host config modules."""
    monkeypatch.setattr(cfg, '_host_id', None)
    monkeypatch.setattr(cfg, '_host_config', None)
    monkeypatch.setattr(cfg, '_index_config', None)
    monkeypatch.setattr(cfg, '_geometry_config', None)


def test_current_host_id_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.current_host_id()


def test_get_host_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_host_config()


def test_get_index_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_index_config()


def test_get_geometry_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_geometry_config()


def test_set_current_registers_host_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType('fake')
    cfg.set_current(host_id='TEST_HOST', host_config=fake,
                    index_config=fake, geometry_config=fake)
    assert cfg.current_host_id() == 'TEST_HOST'
    # monkeypatch auto-restores after the test, re-exposing the conftest fake.


def test_set_current_registers_all_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    host = types.ModuleType('host')
    idx = types.ModuleType('idx')
    geom = types.ModuleType('geom')
    cfg.set_current(host_id='X', host_config=host, index_config=idx,
                    geometry_config=geom)
    assert cfg.get_host_config() is host
    assert cfg.get_index_config() is idx
    assert cfg.get_geometry_config() is geom
```

### 2.2 Missing: `label_support.create()` with `system` arg
**File:** `src/metadata_tools/label_support.py:17`
**Finding:** The `system` parameter affects the template path offset but no test exercises a non-None/empty `system` value.
**Severity:** Medium.
**Fix:** Add a test to `tests/test_label_support.py` that passes `system='JUPITER'` and asserts the template lookup uses the offset-adjusted stem name.

### 2.3 Missing: `_create_index` with `volumes` filter
**File:** `tests/test_index_support.py`
**Finding:** `_create_index` has a `volumes` parameter that restricts which volumes are processed. No test exercises `volumes=['GO_0001']` while a second volume also exists.
**Severity:** Low.
**Fix:** Add a test that builds a two-volume tree, calls `_create_index(volumes=['GO_0001'])`, and asserts only one volume was processed.

### 2.4 Dead code: `test_geometry_cumulative` returns immediately
**File:** `tests/test_geometry.py:34`
**Finding:**
```python
def test_geometry_cumulative() -> None:
    return   # <-- function exits here; all code below is dead
    files = support.match(...)
    ...
```
This test will never fail or assert anything. The early `return` and the inline `#####` comment indicate unfinished work.
**Severity:** High (provides false confidence that cumulative geometry is tested).
**Fix:** Replace the dead body with a skip:
```python
def test_geometry_cumulative() -> None:
    pytest.skip('Not yet implemented — see issue #<N> for cumulative geometry validation')
```

---

## 3. Consistency

### 3.1 Duplicated `exists_true` fixture
**Files:** `tests/test_geometry_masks.py:14-17` and `tests/test_geometry_prep.py:14-17`
**Finding:** Both files define an identical `exists_true` fixture:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```
This violates DRY and means changes must be made in two places.
**Severity:** Medium.
**Fix:** Move to `tests/conftest.py`:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every oops.Body.exists() call return True (no SPICE registry)."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```
Then remove both local definitions and verify collection with:
```bash
pytest tests/test_geometry_masks.py tests/test_geometry_prep.py --collect-only
```

### 3.2 `_silent_logger` is a helper function, not a fixture
**File:** `tests/test_cumulative_support.py:21-23`
**Finding:**
```python
def _silent_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None))
```
This is called as `_silent_logger(monkeypatch)` in several tests. Per `python_testing.mdc` §3, shared setup belongs in `conftest.py` as a fixture.
**Severity:** Low.
**Fix:** Convert to a fixture in `tests/conftest.py`:
```python
@pytest.fixture
def silent_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress all PdsLogger output in the test."""
    import metadata_tools.common as com
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(info=lambda *a, **k: None,
                                                      warning=lambda *a, **k: None,
                                                      close=lambda **k: None))
```
Then update `test_cumulative_support.py` to accept `silent_logger` as a parameter instead of calling `_silent_logger(monkeypatch)`.

### 3.3 Inconsistent exception assertion style
**Finding:** Some `pytest.raises` calls use `match=` (good), others only check the type:
- `test_indextable_init_supplemental_missing_primary_raises` (`tests/test_index_support.py:333`): only `FileNotFoundError`, no `match=`
- `test_suite_init_multiple_indexes_raises` (`tests/test_geometry_constructors.py:167`): uses `match='index files'` ✓
- `test_index_one_value_none_without_null_constant_raises` (`tests/test_index_support.py:187`): uses `match='Null constant needed'` ✓
**Severity:** Low.
**Fix:** Add `match=` to `test_indextable_init_supplemental_missing_primary_raises`:
```python
with pytest.raises(FileNotFoundError, match='No primary index for GO_0001'):
    IndexTable(...)
```

---

## 4. Completeness

### 4.1 `geometry_support/bodies_select.py` — `get_primary` multiple-range edge case
**File:** `src/metadata_tools/geometry_support/bodies_select.py`
**Finding:** `get_primary()` iterates a time-range table and returns on the first match. No test exercises a table with multiple time ranges where the second range matches.
**Severity:** Low.

### 4.2 `geometry_support/suite.py` — `create(labels_only=True)` path untested
**File:** `tests/test_geometry_tables.py`
**Finding:** `test_suite_create_processes_observations` calls `suite.create()` (default `labels_only=False`) and asserts `written == [False]`. The `labels_only=True` path is never exercised.
**Severity:** Low.
**Fix:**
```python
def test_suite_create_labels_only(monkeypatch: pytest.MonkeyPatch) -> None:
    suite = Suite.__new__(Suite)
    suite.observations = [types.SimpleNamespace(basename='C0123.IMG',
                                                filespec='data/C0123.IMG')]
    suite.glob = 'C0*'
    suite.first = None
    suite.volume_id = 'GO_0001'
    written: list[Any] = []
    monkeypatch.setattr(Suite, 'make_records', lambda self, i: ['rec'])
    monkeypatch.setattr(Suite, 'add', lambda self, records: None)
    monkeypatch.setattr(Suite, 'write',
                        lambda self, labels_only=False: written.append(labels_only))
    monkeypatch.setattr(config, 'cleanup', lambda: None, raising=False)
    monkeypatch.setattr(com, 'get_logger',
                        lambda: types.SimpleNamespace(
                            info=lambda *a, **k: None, warning=lambda *a, **k: None,
                            close=lambda: None))
    suite.create(labels_only=True)
    assert written == [True]
```

### 4.3 `geometry_support/formatting.py` — string-valued ISO branch untested
**File:** `tests/test_geometry_formatting.py`
**Finding:** `test_iso_route` calls `formatted_column` with a Scalar of floats (TAI times). The string branch (where `values` is already a string) is not tested.
**Severity:** Low.

### 4.4 `index_support/table.py` — `_format_column` count mismatch error untested
**File:** `src/metadata_tools/index_support/table.py`
**Finding:** `_format_column` raises `ValueError` when `len(value) != count` for multi-item columns. No test covers this path.
**Severity:** Low.
**Fix:**
```python
def test_format_column_count_mismatch_raises() -> None:
    stub = {'NAME': 'X', 'FORMAT': '"A4"', 'ITEMS': 3, 'NULL_CONSTANT': '-'}
    with pytest.raises(ValueError, match='expected 3 values but got 2'):
        IndexTable._format_column(stub, ['AB', 'CD'])
```

### 4.5 `util.py` — `pds_table()` not tested
**File:** `src/metadata_tools/util.py`
**Finding:** `pds_table()` calls `label_path.retrieve()` and `label_path.with_suffix('.tab').retrieve()`. No hermetic test exercises these FCPath paths.
**Severity:** Low (thin wrapper; the `.retrieve()` calls are the interesting part — acceptable to leave for integration tests).

### 4.6 `cumulative_support.py` — `volumes` filter in `_cat_rows` untested
**File:** `tests/test_cumulative_support.py`
**Finding:** `_cat_rows` has a `volumes` parameter that restricts which volumes are included. No test exercises `volumes=['GO_0001']` while a second volume exists.
**Severity:** Low.
**Fix:** Add a test that builds a two-volume tree, calls `_cat_rows(volumes=['GO_0001'])`, and asserts only `'GO_0001'` rows are written.

---

## 5. Redundancy

### 5.1 `test_make_task_structure` and `test_make_task_data_volume_id` overlap
**File:** `tests/test_task_list.py:17-23`
**Finding:**
```python
def test_make_task_structure() -> None:
    task = tl.make_task('GO_0017')
    assert task == {'task_id': 'task-GO_0017', 'data': {'volume_id': 'GO_0017'}}

def test_make_task_data_volume_id() -> None:
    assert tl.make_task('GO_0001')['data']['volume_id'] == 'GO_0001'
```
`test_make_task_structure` already covers the full structure including `data.volume_id`. `test_make_task_data_volume_id` is redundant.
**Severity:** Low.
**Fix:** Remove `test_make_task_data_volume_id`.

### 5.2 `test_format_value_*` — three near-identical tests
**File:** `tests/test_index_support.py:37-51`
**Finding:** Three tests differ only in `value`, `fmt`, and `expected`. Good parametrization candidates.
**Severity:** Low.
**Fix (optional):**
```python
@pytest.mark.parametrize('value,fmt,expected', [
    ('IO', 'A10', '"IO        "'),
    (3.14159, 'F8.3', '   3.142'),
    (42, 'I5', '   42'),
])
def test_format_value(value: Any, fmt: str, expected: str) -> None:
    assert IndexTable._format_value(value, fmt) == expected
```

---

## 6. Parallel execution

### 6.1 Global state patched in `conftest.py` at module level is safe under `-n auto`
**File:** `tests/conftest.py`
**Finding:** `_install_fakes()` runs once at module import (before workers fork), modifying `sys.modules` and calling `mt_config.set_current()`. These are module-level singletons. Tests that clear config via `monkeypatch` (as proposed in §2.1) **must** use `monkeypatch`, not direct assignment, since `monkeypatch` is function-scoped and auto-reverts.
**Severity:** Low (no current issue; note for future tests).

### 6.2 `_Backplane` inline class in `test_geometry_tables.py` vs `FakeBackplane` in conftest
**File:** `tests/test_geometry_tables.py:92`
**Finding:** `_Backplane` is a local class with simpler defaults than `FakeBackplane` in conftest. Both are fine for parallel execution since they create new instances per test. No issue.

---

## 7. Mocking and dependency isolation

### 7.1 `FakeBackplane.evaluate` lazy-imports `oops`
**File:** `tests/conftest.py:112`
**Finding:** `evaluate()` does `import oops` inside the method to avoid a top-level import in `conftest.py`. Intentional and correct. If `oops` is not installed this will fail at test time rather than collection time — acceptable for this project.

### 7.2 `PdsLabel.from_file` patched as `staticmethod`
**File:** `tests/test_index_support.py:223`
**Finding:**
```python
monkeypatch.setattr(PdsLabel, 'from_file',
                    staticmethod(lambda path: fake_label))
```
Correct patch target (patching where it's looked up, not where defined). ✓

### 7.3 Missing: no test for `IndexTable.add()` when `_format_column` logs a warning
**File:** `src/metadata_tools/index_support/table.py`
**Finding:** `_format_column` logs a warning via `logger.warning(...)` in the `TypeError` path. No test checks that the logger was invoked.
**Severity:** Low (the logger is PdsLogger, not stdlib; `caplog` does not work with it directly).

---

## 8. Security and input validation

### 8.1 Missing: path traversal in `splitpath`
**File:** `src/metadata_tools/util.py`
**Finding:** `splitpath(path, volume_id)` calls `path.parts.index(string)`, which raises `ValueError` if `volume_id` is not in the path. No test covers this `ValueError` path.
**Severity:** Low.
**Fix:**
```python
def test_splitpath_raises_when_string_not_in_path() -> None:
    with pytest.raises(ValueError):
        util.splitpath(FCPath('/a/b/c.lbl'), 'GO_MISSING')
```

---

## 9. Parameterization

### 9.1 `test_geometry_masks.py` — 13 similar tests could be parametrized
**File:** `tests/test_geometry_masks.py`
**Finding:** Each test follows the pattern: configure `fake_backplane.<registry>[key] = _one_pixel()`, call `masks.construct_excluded_mask(...)`, assert `result.vals.sum() == <N>`. Thirteen tests share this pattern.
**Severity:** Low (tests are clear as-is; parametrization would be optional cleanup).

### 9.2 `test_util_math.py` — `add_by_base` cases could be parametrized
**File:** `tests/test_util_math.py:13-29`
**Finding:** Four tests of `add_by_base` differ only in arguments and expected result. Could be parametrized.
**Severity:** Low.

---

## 10. Async

Not applicable — the project uses no async code.

---

## 11. Output and contract

### 11.1 `test_record_add_builds_summary_line` — exact output string
**File:** `tests/test_geometry_tables.py:118`
**Finding:** `assert lines == ['"vol","file",  28.648,  57.296']` — exact string assertion. ✓

### 11.2 `test_suite_get_override_builds_one_dict_per_column` — exact dict equality
**File:** `tests/test_geometry_tables.py:147`
**Finding:** Asserts `== [{'NULL_VALUE': -999., 'VALID_MINIMUM': 0, 'VALID_MAXIMUM': 360}]`. ✓

### 11.3 `test_suite_create_returns_early_without_observations`
**File:** `tests/test_geometry_tables.py:214`
**Finding:** `assert suite.create() is None` — asserts `None` return of a `-> None` typed function. While technically correct (verifies early return doesn't raise), the intent is better expressed by asserting no side-effects occurred (e.g., no calls to `write`). Minor.
**Severity:** Low.

---

## 12. Error handling

### 12.1 Exception type only — no message: `test_indextable_init_supplemental_missing_primary_raises`
**File:** `tests/test_index_support.py:325-335`
**Finding:**
```python
with pytest.raises(FileNotFoundError):
    IndexTable(...)
```
Per `python_testing.mdc` §7: "When testing errors, ALWAYS ... assert on the exception **message content**". The source raises:
```python
raise FileNotFoundError(f'No primary index for {self.volume_id}')
```
**Fix:**
```python
with pytest.raises(FileNotFoundError, match='No primary index for GO_0001'):
    IndexTable(...)
```

---

## 13. State and workflow

### 13.1 `create_cumulative_indexes` — 8-table dispatch tested but only two entries spot-checked
**File:** `tests/test_cumulative_support.py:121`
**Finding:** `test_create_cumulative_indexes_fires_eight_cat_rows` asserts `len(calls) == 8` and spot-checks two specific entries. All 8 `(type_name, level)` pairs are not exhaustively asserted.
**Severity:** Low.
**Fix (optional):** Assert the full sorted list after reading `cumulative_support.py` lines 171-180 to confirm the expected pairs.

### 13.2 `Suite.create(labels_only=True)` — see §4.2

---

## 14. Test data and fixtures

### 14.1 `exists_true` duplication — see §3.1

### 14.2 `_Backplane` inline class partially duplicates `FakeBackplane`
**File:** `tests/test_geometry_tables.py:92`
**Finding:** `_Backplane` overlaps with `FakeBackplane` in conftest but is simpler (always returns a non-masked Scalar or all-False array). Both are fine. Low priority to merge.

### 14.3 `tmp_volume_tree` fixture only used in one file
**File:** `tests/conftest.py:157`
**Finding:** `tmp_volume_tree` is project-wide but only used in `test_index_support.py`. No harm, but could move to a local conftest if more granularity is desired.
**Severity:** Low.

### 14.4 `archive_support.py` — `range(len(...))` loop pattern
**File:** `tests/archive_support.py:35-52`
**Finding:** The `exclude()` function uses:
```python
for i in range(len(files)):
    if files[i].find(pattern) != -1:
```
Per `python.mdc` §1, prefer `for filename in files: if pattern in filename:`.
**Severity:** Low.

---

## 15. Flakiness indicators

### 15.1 `test_range_of_n_angles_is_bounded` — non-deterministic
**File:** `tests/test_util_math.py:124`
**Finding:** `util.range_of_n_angles(5, tests=200)` uses `np.random.rand` internally, making the result non-deterministic. The test asserts only `0.0 <= result <= 360.0`, which always passes regardless of correctness.
**Severity:** Medium.
**Fix:** Seed numpy RNG before the call:
```python
def test_range_of_n_angles_is_bounded() -> None:
    np.random.seed(0)
    result = util.range_of_n_angles(5, tests=200)
    assert 0.0 <= result <= 360.0
```

### 15.2 No other flakiness indicators observed
Wall-clock time assertions, external network calls, and unseeded random data in other assertions are absent from the hermetic test suite. ✓

---

## 16. Regression and documentation

### 16.1 `test_geometry_columns_contract.py` — excellent regression guard ✓
**File:** `tests/test_geometry_columns_contract.py`
**Finding:** AST-based contract tests that catch `AttributeError` typos in column name lookups. Well-designed.

### 16.2 `test_geometry_cumulative` has inline `#####` comment without issue reference
**File:** `tests/test_geometry.py:38`
**Finding:** `##### this needs to be changed to match cumulative files` — unlinked TODO without a tracking issue.
**Severity:** Medium.
**Fix:** Open a tracking issue and replace with `pytest.skip('...')` as described in §2.4.

### 16.3 No `filterwarnings = ["error"]` in pytest config
**File:** `pyproject.toml`
**Finding:** Per `python_testing.mdc` §4, `filterwarnings = ["error"]` should be set. The current `addopts` does not include `-W error` or `filterwarnings`. Warnings emitted by third-party libraries (oops, polymath, pdslogger) during tests would go silently unnoticed.
**Severity:** High.
**Fix:** Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
filterwarnings = [
  "error",
  # oops/polymath emit NumPy deprecation warnings we cannot fix:
  "ignore::DeprecationWarning:oops",
  "ignore::DeprecationWarning:polymath",
]
```
Note: `test_geometry_formatting.py` explicitly uses `pytest.warns(UserWarning, ...)` — those warnings must remain catchable, not silenced.

---

## 17. Other

### 17.1 `tests/hosts/GO_0xxx/test_geometry.py` — extensive commented-out code
**File:** `tests/hosts/GO_0xxx/test_geometry.py`
**Finding:** Commented-out imports and assertions throughout:
```python
#metadata_tools.util as util
#import metadata_tools.hosts.GO_0xxx.host_config as config
#SYSTEMS_TABLE = util.convert_systems_table(config.SYSTEMS_TABLE, config.SCLK_BASES)
```
and `# support.bounds(...)` calls. Dead code should be removed, not commented out (per `python.mdc` §2).
**Severity:** Low.
**Fix:** Delete commented-out lines. If bounds checks are needed, implement them or open an issue.

### 17.2 `test_geometry_tables.py` — `or args[-1]` trick in monkeypatch lambda
**File:** `tests/test_geometry_tables.py:185`
**Finding:**
```python
monkeypatch.setattr(
    suite_mod, 'Record',
    lambda *args: created.append(args[-1]) or args[-1])
```
The `or args[-1]` trick returns `args[-1]` as the "Record" object. This works but is non-obvious. A brief comment would help future readers.
**Severity:** Low.

### 17.3 `test_cumulative_support.py` — `hconf` is module-level mutable
**File:** `tests/test_cumulative_support.py:18`
**Finding:** `hconf = get_host_config()` at module level. Tests call `monkeypatch.setattr(hconf, 'get_volume_id', ...)`. Safe because `monkeypatch` auto-reverts. Any test that modifies `hconf` attributes directly (not via monkeypatch) would cause cross-test pollution. No current test does this.

---

## 18. Code coverage

**Target:** ≥90% (configured via `fail_under = 90` in `pyproject.toml`).
**Measurement:** Branch coverage enabled (`branch = true`).
**Excluded from denominator:** `tests/*`, `*/_version.py`, `*/metadata_tools/bodies.py`, `*/metadata_tools/hosts/*`, `*/metadata_tools/cli/*`.

**Estimated gaps (inferred from reading, not measured):**

| Module | Likely uncovered paths |
|--------|----------------------|
| `config.py` | Error branches in `current_host_id()`, `get_*_config()` when `_host_id` is None; `set_host()` (requires real host) |
| `label_support.py` | `system` parameter offset branch |
| `cumulative_support.py` | `volumes` filter branch in `_cat_rows` |
| `util.py` | `pds_table()`, `sclk_to_ticks()` (needs SPICE) |
| `geometry_support/suite.py` | `create(labels_only=True)` |
| `geometry_support/formatting.py` | String value branch for non-ISO flag |
| `index_support/table.py` | `_format_column` `ValueError` on count mismatch |

**Action:** Run `pytest --cov=src --cov-report=term-missing` and examine the missing-lines report for each module above.

---

## 19. Pytest markers

### 19.1 Markers are registered ✓
Both `integration` and `requires_archive` are registered in `pyproject.toml` with descriptions. ✓

### 19.2 `--strict-markers` is enabled ✓
`--strict-markers` is in `addopts`. ✓

### 19.3 No `xfail` tests ✓

### 19.4 No `slow` marks
The project has no `@pytest.mark.slow` category. Most hermetic tests run quickly; archive-backed tests are already gated. No action needed.

---

## 20. Test boundary

### 20.1 `idx.table` patched for `Pds3Table`
**File:** `tests/test_index_support.py:287`
**Finding:** `monkeypatch.setattr(idx.table, 'Pds3Table', ...)` — patches the internal module reference. Acceptable; no clean alternative without refactoring production code.

### 20.2 No private `_`-prefixed names imported directly from source ✓
All test imports are through public package names. ✓

### 20.3 `_create_index` (private by convention) in `__all__`
**File:** `src/metadata_tools/index_support/__init__.py:21`
**Finding:** `_create_index` is in `__all__`, which is unusual for a `_`-prefixed function. Tests call `idx._create_index(...)` directly. Intentional design choice, but inconsistent with the naming convention.
**Severity:** Low.

---

## 21. Logging assertions

### 21.1 No `caplog` usage anywhere — expected limitation
**Finding:** No test uses `caplog`. The project uses `pdslogger.PdsLogger`, which does not integrate with pytest's `caplog` fixture (which intercepts stdlib `logging`). Acceptable.

### 21.2 Warnings tested explicitly with `pytest.warns` ✓
**File:** `tests/test_geometry_formatting.py`
**Finding:** NaN, infinity, and overflow paths use `pytest.warns(UserWarning, match=...)`. ✓

---

## 22. Pytest configuration

### 22.1 `filterwarnings` missing — HIGH PRIORITY
See §16.3.

### 22.2 `testpaths = ["tests"]` ✓

### 22.3 `--strict-markers` and `--strict-config` ✓

### 22.4 `pytest-xdist` declared ✓ (`pytest-xdist>=3.8.0` in dev deps)

### 22.5 `pytest-randomly` not installed
**Finding:** No `pytest-randomly` in dev dependencies. Without it, test order is deterministic and order-dependence bugs go undetected.
**Severity:** Low.
**Fix:** Add `pytest-randomly>=3.0` to `[project.optional-dependencies].dev` in `pyproject.toml`.

---

## 23. Snapshot and golden-file testing

### 23.1 No snapshot tests — appropriate for this codebase
**Finding:** For geometry formatting tests, exact string comparisons serve as inline golden values and are appropriate for the small, deterministic outputs exercised. No action needed.

---

## Prompt for an AI agent to fix tests

You are modifying the test suite for the `rms-metadata-tools` Python package. The package generates PDS3 index, geometry, and cumulative metadata tables. The tests live in `tests/`. The source lives in `src/metadata_tools/`. Do **not** modify any production source code unless a finding explicitly says to (none do).

### Context

- `pyproject.toml` configures pytest under `[tool.pytest.ini_options]` with `--strict-markers`, `--strict-config`, `-n auto`, `--cov=src`, and `-m "not integration and not requires_archive"`.
- `tests/conftest.py` installs fake SPICE/host modules at collection time via `_install_fakes()`. All engine tests are hermetic (no real SPICE/archive needed).
- Custom markers: `integration` (needs SPICE/oops init) and `requires_archive` (needs `$RMS_METADATA` holdings). Both are excluded from the default run.
- The project uses `pdslogger.PdsLogger` (not stdlib logging). `caplog` does not work with it.
- Coverage target: ≥90% for `src/metadata_tools/` excluding `bodies.py`, `hosts/`, and `cli/`.
- All tests must pass `mypy` strict type checking. Add type annotations to any new test code.

### Tasks (in priority order)

---

#### CRITICAL

**Task 1: Add `filterwarnings = ["error"]` to pytest config**

File: `pyproject.toml`

In `[tool.pytest.ini_options]`, after the `markers` block, add:
```toml
filterwarnings = [
  "error",
  "ignore::DeprecationWarning:oops",
  "ignore::DeprecationWarning:polymath",
]
```

After adding, run the full test suite. For each test that now fails with an unexpected warning, either:
- Fix the warning source in production code, OR
- Add a narrowly scoped `"default::WarningType:module_name"` entry with a comment explaining why you can't fix it.

---

**Task 2: Add exception-message assertions to all `pytest.raises` calls missing `match=`**

File: `tests/test_index_support.py`

Find the test named `test_indextable_init_supplemental_missing_primary_raises`. Change:
```python
with pytest.raises(FileNotFoundError):
```
to:
```python
with pytest.raises(FileNotFoundError, match='No primary index for GO_0001'):
```

Then search all test files for `pytest.raises(` without `match=`:
```bash
grep -n 'pytest.raises(' tests/*.py tests/**/*.py | grep -v 'match='
```
For each result, look up the exception message in the source and add an appropriate `match=` pattern.

---

**Task 3: Delete dead code in `test_geometry.py` and `tests/hosts/GO_0xxx/test_geometry.py`**

File: `tests/test_geometry.py`

Find `test_geometry_cumulative`. Replace its entire body with:
```python
def test_geometry_cumulative() -> None:
    pytest.skip('Not yet implemented: cumulative geometry table validation')
```

File: `tests/hosts/GO_0xxx/test_geometry.py`

Remove all commented-out import lines at the top (lines that start with `#metadata_tools` or `#import`). Remove all commented-out `support.bounds(...)` calls. Remove any other commented-out code blocks. Keep the docstrings and active test code.

---

#### HIGH

**Task 4: Create `tests/test_config.py` for `config.py` error paths**

Create a new file `tests/test_config.py` with the following content:

```python
################################################################################
# tests/test_config.py: Tests for metadata_tools.config error paths.
################################################################################
import types

import pytest

import metadata_tools.config as cfg


def _clear_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all registered host config modules for the duration of the test."""
    monkeypatch.setattr(cfg, '_host_id', None)
    monkeypatch.setattr(cfg, '_host_config', None)
    monkeypatch.setattr(cfg, '_index_config', None)
    monkeypatch.setattr(cfg, '_geometry_config', None)


def test_current_host_id_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.current_host_id()


def test_get_host_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_host_config()


def test_get_index_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_index_config()


def test_get_geometry_config_raises_when_not_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config(monkeypatch)
    with pytest.raises(RuntimeError, match='set_host\\(\\) has not been called'):
        cfg.get_geometry_config()


def test_set_current_registers_host_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType('fake')
    cfg.set_current(host_id='TEST_HOST', host_config=fake,
                    index_config=fake, geometry_config=fake)
    assert cfg.current_host_id() == 'TEST_HOST'
    # monkeypatch auto-restores original values at teardown.


def test_set_current_registers_all_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    host = types.ModuleType('host')
    idx = types.ModuleType('idx')
    geom = types.ModuleType('geom')
    cfg.set_current(host_id='X', host_config=host, index_config=idx,
                    geometry_config=geom)
    assert cfg.get_host_config() is host
    assert cfg.get_index_config() is idx
    assert cfg.get_geometry_config() is geom
```

**Important:** The `_clear_config` function uses `monkeypatch` so that all changes are reverted after each test. Do NOT assign directly to `cfg._host_id = None` — that would permanently modify module state and break subsequent tests running in the same worker.

After creating the file, confirm the match patterns are correct by checking what message `config.py` raises. If the exact message differs, update `match=` to match the actual message.

---

**Task 5: Move `exists_true` fixture to `tests/conftest.py`**

Step 1: Open `tests/conftest.py`. Add the following fixture after the existing fixture definitions:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch oops.Body.exists to return True for every name (no SPICE registry)."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```
Ensure `oops` is already imported at the top of `conftest.py` (it is — `FakeBackplane.evaluate` imports it lazily, but the top-level import may be absent; add `import oops` if needed).

Step 2: Open `tests/test_geometry_masks.py`. Delete lines 14-17:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every body name 'exist' (no SPICE registry available in tests)."""
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```

Step 3: Open `tests/test_geometry_prep.py`. Delete the identical `exists_true` fixture (also lines 14-17 or similar).

Step 4: Verify:
```bash
pytest tests/test_geometry_masks.py tests/test_geometry_prep.py --collect-only -q
```
All tests must still collect without errors.

---

**Task 6: Convert `_silent_logger` to a fixture in conftest**

Step 1: Open `tests/conftest.py`. Add:
```python
@pytest.fixture
def silent_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress all PdsLogger output for the duration of a test."""
    import metadata_tools.common as com
    monkeypatch.setattr(
        com, 'get_logger',
        lambda: types.SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            close=lambda **k: None))
```
Ensure `types` is imported at the top of `conftest.py` (it may already be there; add if absent).

Step 2: Open `tests/test_cumulative_support.py`.
- Delete the `_silent_logger` function definition.
- For each test that currently calls `_silent_logger(monkeypatch)`, add `silent_logger: None` to the test's parameter list and remove the `_silent_logger(monkeypatch)` call from the body.

Example: a test like:
```python
def test_cat_rows_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _silent_logger(monkeypatch)
    ...
```
becomes:
```python
def test_cat_rows_empty(monkeypatch: pytest.MonkeyPatch, silent_logger: None) -> None:
    ...
```

---

#### MEDIUM

**Task 7: Seed the `test_range_of_n_angles_is_bounded` test**

File: `tests/test_util_math.py`

Find `test_range_of_n_angles_is_bounded`. Before the `util.range_of_n_angles(...)` call, add:
```python
np.random.seed(0)
```
Ensure `numpy` is already imported as `np` in this file (it is).

---

**Task 8: Remove redundant `test_make_task_data_volume_id`**

File: `tests/test_task_list.py`

Delete the entire `test_make_task_data_volume_id` function. The assertion it makes is already fully covered by `test_make_task_structure`.

---

#### LOW (optional cleanup)

**Task 9: Add `_format_column` count mismatch test**

File: `tests/test_index_support.py`

Add a new test after `test_format_column_multi_item_expands_and_joins` (search for that name to find the insertion point):
```python
def test_format_column_count_mismatch_raises() -> None:
    stub = {'NAME': 'X', 'FORMAT': '"A4"', 'ITEMS': 3, 'NULL_CONSTANT': '-'}
    with pytest.raises(ValueError, match='expected 3 values but got 2'):
        IndexTable._format_column(stub, ['AB', 'CD'])
```
Before writing, check the actual error message raised by `_format_column` in `src/metadata_tools/index_support/table.py` and adjust `match=` accordingly.

---

**Task 10: Add `splitpath` ValueError test**

File: `tests/test_util_names.py`

Add after `test_splitpath_splits_around_string` (search for that name):
```python
def test_splitpath_raises_when_string_not_in_path() -> None:
    from rms_filecache import FCPath
    with pytest.raises(ValueError):
        util.splitpath(FCPath('/a/b/c.lbl'), 'GO_MISSING')
```

---

**Task 11: Add `pytest-randomly` to dev dependencies**

File: `pyproject.toml`

In `[project.optional-dependencies].dev`, add:
```toml
"pytest-randomly>=3.0",
```

After adding, run the full test suite multiple times (`pytest --count=3` if available, or just `pytest` twice). If any test fails on the second run but not the first, investigate test-order dependence.

---

### Verification

After completing all tasks, run:
```bash
scripts/run-all-checks.sh -c
```
Or equivalently:
```bash
ruff check src tests
mypy src tests
pytest --tb=short
```

Confirm:
1. All non-archive, non-integration tests pass.
2. Coverage ≥ 90% for the covered modules.
3. No unexpected warnings (the new `filterwarnings = ["error"]` will surface them).
4. `mypy` reports no type errors in the new test files.
