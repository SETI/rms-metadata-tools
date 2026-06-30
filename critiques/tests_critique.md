# Test Suite Critique Report

**Generated:** 2026-06-29
**Scope:** `tests/` (all subdirectories) and `conftest.py` files — full read of every test file and every line.
**Authoritative rules:** `.cursor/rules/python_testing.mdc` (primary), `python.mdc`, `filecache.mdc`, `logging.mdc`.

---

## Executive Summary

The test suite has been substantially rewritten from the prior `unittest.TestCase` style and is
now a strong foundation. The hermetic conftest shim (`_install_fakes()` injecting fake
`bodies`/`host_config`/`index_config`/`geometry_config` modules before collection) is an
excellent design that enables testing SPICE-dependent code without real kernels. Broad coverage
exists across `util.py`, `index_support.py`, `common.py`, `cumulative_support.py`,
`label_support.py`, and all `geometry_support` sub-modules. `monkeypatch` is used
exclusively (no `unittest.mock.patch` race risks). `--strict-markers`, `--strict-config`,
`fail_under = 90`, and branch coverage are all configured.

**High-priority fixes (must fix):**
1. Add `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` in `pyproject.toml`.
2. Fix dead test `test_geometry_cumulative` in `tests/test_geometry.py` (bare `return` as
   first statement — always passes trivially).
3. Add `match=` to the bare `pytest.raises(FileNotFoundError)` at
   `tests/test_index_support.py:346`.
4. Move the duplicated `exists_true` fixture out of `test_geometry_masks.py` and
   `test_geometry_prep.py` and into `tests/conftest.py`.
5. Replace `Args:` with `Parameters:` in all three docstrings of `tests/archive_support.py`.

**Medium-priority improvements:**
- Parameterize the `_format_value` / `_format_parms` / `_get_null_value` test groups
  (currently 7 near-identical test functions that should be one `@pytest.mark.parametrize`
  each).
- Add `caplog`/monkeypatch-logger assertions for warning-emitting code paths.
- Move `_reset_task_list` autouse fixture to the root `conftest.py`.
- Add `match=` to all bare `pytest.raises()` calls.
- Replace the dead `test_geometry_body` host test (no assertions) with a skip.

---

## 1. Return Values and Assertions

**Good:** The vast majority of tests assert exact values rather than merely checking
truthiness. Examples: `record.add()` is asserted as `== ['"vol","file",  28.648,  57.296']`;
`_format_value` is asserted against exact padded strings; formatting functions assert exact
column output including whitespace.

**Issue (medium) — existence-only asserts in `columns/conftest.py`:**
`tests/columns/conftest.py:33–34` asserts `spec is not None` and `spec.loader is not None`.
These are guard assertions in fixture setup, which is acceptable, but the error message on
failure would not help a developer understand which module failed to load. Add a descriptive
`assert spec is not None, f"Could not find spec for {name}"`.

**Issue (low) — type-only assertions in archive-backed tests:**
`tests/test_geometry.py:67–68` and `tests/test_index.py:50–54` assert only
`isinstance(..., np.str_)`. For archive integration tests this is acceptable, but at least one
value-level spot check per column type would catch value regressions.

**Issue (low) — `test_sclk_format_count_returns_str_not_int` is a subset of the roundtrip test:**
`tests/test_util_math.py:81–85` asserts only `isinstance(result, str)`. The roundtrip test
immediately below asserts the exact string value. The isinstance-only test is therefore a
strict subset of the roundtrip and adds no additional confidence.

---

## 2. Success and Failure Conditions

**Good:** Most error paths are tested. `test_index_support.py:186` uses
`pytest.raises(ValueError, match='Null constant needed')`. `test_geometry_constructors.py`
tests `RuntimeError` with a `match=` pattern. The geometry formatting tests include NaN,
overflow, and infinity paths.

**Issue (medium) — Dead test `test_geometry_cumulative` in `tests/test_geometry.py:34–46`:**
```python
def test_geometry_cumulative() -> None:
    return   # first line: test is dead
    # Get labels to test
##### this needs to be changed to match cumulative files
```
This test always passes and never executes any assertion. Per `python_testing.mdc §10`, a
test that passes with no assertions provides false confidence. Fix: apply
`@pytest.mark.skip(reason='cumulative file pattern not yet implemented')` and keep the body,
or implement it fully.

**Issue (medium) — `pytest.raises(FileNotFoundError)` without `match=` at line 346:**
`tests/test_index_support.py:346` (`test_indextable_init_supplemental_missing_primary_raises`):
```python
with pytest.raises(FileNotFoundError):
    IndexTable(FCPath(indir), FCPath(indir), ...)
```
Per `python_testing.mdc §7`, every `pytest.raises` call must also assert the exception message
via `match=` (or a captured `excinfo.value` check). Fix: run the test to capture the actual
message and add `match=r'GO_0001'` (or the relevant path fragment).

**Issue (low) — `test_geometry_body` in `tests/hosts/GO_0xxx/test_geometry.py:41–67`:**
The function opens each summary label file but makes **no assertions** — all bounds checks are
commented out with `#`. Either restore the assertions or replace with:
```python
@pytest.mark.skip(reason='GOSSI geometry body bounds not yet ported')
def test_geometry_body() -> None: ...
```

**Missing failure-path tests:**
- `util.splitpath()` has no test for the case where the target string is not found in
  `path.parts` (raises `ValueError` from `list.index()`).
- `label_support.create()` with a `None` or nonexistent template path is not tested.
- `cumulative_support` error path when the volume directory has no matching index files is
  not tested.

---

## 3. Consistency

**Good:** Naming follows a consistent `test_<action>_<condition>_<result>` or
`test_<function>_<description>` convention throughout. Most files organize tests into sections
separated by `#====...====` banners.

**Issue (low) — Inconsistent docstring presence:**
`tests/test_util_replace.py` has a comprehensive module docstring and a one-line docstring on
every test function. Most other files (`test_common.py`, `test_index_support.py`,
`test_geometry_constructors.py`, etc.) have no docstrings at all.
`python.mdc §6` requires docstrings on all functions. Choose one convention and apply it: either
add intent docstrings to all tests, or rely entirely on descriptive function names (acceptable
when the name is self-documenting) and add no docstrings anywhere.

**Issue (low) — `tests/archive_support.py` uses `Args:` instead of `Parameters:`:**
Lines 21, 38, and 60 use `Args:` (NumPy/Sphinx style). `python.mdc §6` specifies **Google style**
with `Parameters:`. Fix all three.

**Issue (low) — Commented-out imports in `tests/hosts/GO_0xxx/test_geometry.py:8–12`:**
Three import lines are commented out. Remove stale dead code.

---

## 4. Completeness

**Coverage map (source modules vs. test files):**

| Source module | Test file | Assessment |
|---|---|---|
| `common.py` | `test_common.py` | Good — Table, write, PathAction, args, task list, init_logger |
| `util.py` | `test_util_math.py`, `test_util_names.py`, `test_util_range_mod360.py`, `test_util_replace.py`, `test_util_textfile.py` | Good — broad coverage |
| `index_support/` (table.py, process.py, key_fns.py) | `test_index_support.py` | Good — format, dispatch, walk, init paths |
| `label_support.py` | `test_label_support.py` | Good — 4 creation paths |
| `cumulative_support.py` | `test_cumulative_support.py` | Good — cat_rows, get_args, create |
| `geometry_support/formatting.py` | `test_geometry_formatting.py` | Good — all flag paths, NaN, inf, overflow |
| `geometry_support/masks.py` | `test_geometry_masks.py` | Good — 13 test cases |
| `geometry_support/prep.py` | `test_geometry_prep.py` | Good — body prefix, row variants, tiling |
| `geometry_support/record.py` | `test_geometry_record.py` | Good — backplane key, key map, postprocess |
| `geometry_support/tables.py` + `suite.py` | `test_geometry_tables.py` | Good — dispatch, Suite, create/write |
| `geometry_support/process.py` | `test_geometry_process.py` | Good — get_args, process_tables variants |
| `columns/ring.py`, `sky.py`, `sun.py` | `test_ring.py`, `test_sky.py`, `test_sun.py` | Good |
| `columns/body.py` | No hermetic test | **Gap** — tested only via integration |
| `defs.py` | No direct test | Low concern (constants only) |
| `bodies.py` | `test_columns_integration.py` (integration) | Gap — SPICE-gated, acceptable |
| `util.pds_table()` | Not directly tested | Gap — requires real SPICE/cspyce |
| `util.sclk_to_ticks()` | Mocked everywhere | Gap — SPICE-gated, acceptable |

**Notable gap — `columns/body.py`:**
The body columns are the most complex (per-body dicts built from `BODIES`, placeholder
replacement, `oops.Body` registry). No hermetic unit test exists analogous to `test_ring.py`.
A test loading the module via the same `importlib.util.spec_from_file_location` pattern in
`tests/columns/conftest.py` would close this gap.

---

## 5. Redundancy

**Issue (medium) — `exists_true` fixture duplicated in two files:**
`tests/test_geometry_masks.py:15–17` and `tests/test_geometry_prep.py:16–17` define
identical fixtures:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```
Move to the root `tests/conftest.py`. Note that `test_geometry_constructors.py` uses an
inline `monkeypatch.setattr` call for the same purpose — that can remain inline or use the
shared fixture.

**Issue (low) — `test_sclk_format_count_returns_str_not_int` is a redundant subset:**
See §1. Remove or merge with the roundtrip test.

**Issue (low) — `_silent_logger` pattern repeated across test files:**
Several files independently do `monkeypatch.setattr(com, 'get_logger', lambda: PdsLogger(...))`.
If this grows further, promote to a root conftest fixture.

---

## 6. Parallel Execution

**Good:** `-n auto` is in `addopts`. All tests use `monkeypatch` which auto-reverts. No
shared mutable state is written to `tmp_path` across tests.

**Issue (low) — `common.task_list` global is guarded only in `test_common.py`:**
The `_reset_task_list` autouse fixture clears `com.task_list` before and after each test, but
it lives only in `test_common.py`. If code paths in other test files (e.g.
`test_geometry_process.py`) were ever to call `com.add_task()` without monkeypatching it
first, task list state would leak between parallel workers. The current tests monkeypatch
`com.add_task` before use, so this is fragile but not currently broken. Promote
`_reset_task_list` to the root `conftest.py` to make isolation explicit.

---

## 7. Mocking and Dependency Isolation

**Good:** Exclusively `monkeypatch`. The `_install_fakes()` call in `tests/conftest.py` is
clean and well-commented. `FakeBackplane` and `FakeWhere` are realistic fakes.

**Issue (low) — `FakeBackplane.evaluate()` fallback imports `oops` lazily:**
`tests/conftest.py:106`: if a key is not in `self.evaluations`, the fallback returns
`oops.Scalar(np.zeros(self.shape), True)`. This imports `oops` at call time, creating an
implicit dependency on `oops` being importable. Consider making the default return value
configurable in `FakeBackplane.__init__` instead.

**Issue (low) — `raising=False` patches may silently accept misspelled attributes:**
Several `monkeypatch.setattr(..., raising=False)` calls in `test_geometry_constructors.py`
will succeed even if the attribute name is misspelled, since `raising=False` suppresses the
`AttributeError`. Consider following each with an `assert hasattr(config, 'ATTR_NAME')` to
catch typos.

---

## 8. Security and Input Validation

No tests for path traversal or injection — appropriate for a library that receives programmatic
(not user-web) input.

**Note (low) — `util.replace()` uses `eval()` on column definition strings:**
`src/metadata_tools/util.py` uses `eval()` on strings of the form `defs.DICT["key"]`. There
is a `# nosec B307` comment. The `test_util_replace.py::test_replace_evaluates_embedded_dict_reference`
test correctly exercises this path with a known-safe input. No adversarial tests are expected
here (library-internal, not user-facing), but the existing test serves as documentation.

---

## 9. Parameterization

**Issue (medium) — `_format_value` and `_format_parms` test groups (6 functions):**
`tests/test_index_support.py:36–62` has three separate tests for `_format_value` and three
for `_format_parms`, each differing only in the input/expected values. Collapse to two
parametrized tests:

```python
@pytest.mark.parametrize('value,fmt,expected', [
    ('IO', 'A10', '"IO        "'),
    (3.14159, 'F8.3', '   3.142'),
    (42, 'I5', '   42'),
], ids=['character', 'real', 'integer'])
def test_format_value(value: Any, fmt: str, expected: str) -> None:
    assert IndexTable._format_value(value, fmt) == expected


@pytest.mark.parametrize('fmt,expected', [
    ('A10', (12, 'CHARACTER')),
    ('F8.3', (8, 'ASCII_REAL')),
    ('I5', (5, 'ASCII_INTEGER')),
], ids=['character', 'real', 'integer'])
def test_format_parms(fmt: str, expected: tuple[int, str]) -> None:
    assert IndexTable._format_parms(fmt) == expected
```

**Issue (low) — `_get_null_value` group (4 tests, `test_index_support.py:67–88`):**
Four near-identical functions differing only in the input `stub` dict and expected return value.
Parametrize over `(stub_dict, expected_null)` tuples.

**Issue (low) — `test_add_by_base_*` group (4 tests, `test_util_math.py:13–29`):**
Four near-identical tests; parametrize over `(args, expected)` tuples.

**Issue (low) — `test_circle_coverage_*` group (`test_geometry_formatting.py:81–104`):**
Three tests for `circle_coverage` with different scalar types; parametrize.

---

## 10. Async

Not applicable — the project has no async code outside cloud entry points, which are not tested.

---

## 11. Output and Contract

**Good:** Return-shape assertions are precise throughout. `record.add()` output is asserted
to the exact formatted string. Table row counts are verified.

**Issue (low) — `test_suite_get_override_named` asserts only two of the expected keys:**
`tests/test_geometry_tables.py:149–153`:
```python
overrides = Suite.get_override(record, 'ring', name='JUPITER')
assert len(overrides) == 1
assert overrides[0]['NULL_VALUE'] == -999.
```
The analogous non-named test (`test_suite_get_override_builds_one_dict_per_column`) also
asserts `VALID_MINIMUM` and `VALID_MAXIMUM`. Add those assertions here for consistency.

**Issue (low) — `test_indextable_init_primary_path` asserts only one column stub attribute:**
`test_index_support.py:306–319` asserts `len(table.files) == 1` and
`column_stubs[0]['NAME'] == 'VOLUME_ID'` but does not assert `'FORMAT'` or `'BYTES'` of the
stub, leaving those init paths partially verified.

---

## 12. Error Handling

**Issue (medium) — `pytest.raises(FileNotFoundError)` without `match=` (see §2).**
`test_index_support.py:346`. Add `match=` with the actual exception message substring.

**Issue (low) — Warning side-effect not asserted in `test_format_column_invalid_format_warns`:**
`test_index_support.py:119–124`:
```python
result = IndexTable._format_column(stub, [1, 2])
assert result == 8 * '*'
```
The function also logs a warning via `pdslogger`. Since `pdslogger` does not go through
stdlib `logging`, `caplog` won't catch it; but a monkeypatched logger check would confirm the
warning fires. At minimum, add a comment noting the warning is an expected side effect.

---

## 13. State and Workflow

**Good:** The index, geometry, and cumulative pipeline orchestrators are each tested
end-to-end at the dispatch level with fake stand-ins.

**Issue (low) — `task_list` idempotency not tested:**
If `com.add_task()` is called twice with the same `volume_id`, the list grows to two entries.
No test verifies whether this is intended (list grows) vs. a bug (should de-duplicate). Add a
test.

---

## 14. Test Data and Fixtures

**Good:** `tmp_path` is used everywhere for filesystem isolation. `tmp_volume_tree` in
`conftest.py` is a clean factory fixture. `FakeBackplane` is well-designed.

**Issue (medium) — `exists_true` duplicated (see §5).**

**Issue (low) — `ring_module`, `sky_module`, `sun_module` are session-scoped:**
`tests/columns/conftest.py:40–55`. Correct for immutable module objects, but if a test ever
mutated the module's `__dict__` the contamination would affect all later tests in the session.
Add a comment: `# Read-only — do not mutate this module object in tests`.

**Issue (low) — `FakePds3Table` is local to `test_index_support.py`:**
The stub is only used in one file, which is fine. But if a future test file needs to stub
`Pds3Table`, this class should be promoted to `conftest.py`.

---

## 15. Flakiness Indicators

**Issue (low) — `test_range_of_n_angles_is_bounded` uses unseeded `np.random`:**
`tests/test_util_math.py:124–126`. `util.range_of_n_angles()` calls `np.random.rand` internally.
The test only asserts `0.0 <= result <= 360.0`, which virtually always passes. Add
`np.random.seed(42)` before the call to make it deterministic and document why the seed is
needed.

No time-based assertions, no network calls, no external service calls in the default suite.

---

## 16. Regression and Documentation

**Good:** `test_geometry_columns_contract.py` explicitly documents past bugs (typos
`RING_SUMMARY_DETAILED`, `BODY_SUMMARY_DETAILED`, `BODYX`) in its module docstring. This
pattern should be maintained.

**Issue (high) — `filterwarnings = ["error"]` missing from pytest config:**
`pyproject.toml [tool.pytest.ini_options]` has `--strict-markers` and `--strict-config` but
no `filterwarnings` entry. Per `python_testing.mdc §4`, warnings should be treated as errors
with narrow explicit exclusions. Without this, new deprecation warnings from numpy, oops,
cspyce, or the package's own `warnings.warn()` calls go undetected during the default test run.

**Fix in `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
# ... existing entries ...
filterwarnings = [
    "error",
    # Suppress third-party deprecations — add entries as needed:
    # "ignore::DeprecationWarning:cspyce",
    # "ignore::FutureWarning:oops",
]
```
After adding this, run `pytest` once and add `ignore::` lines for any warnings from
third-party packages, with comments explaining why each is suppressed.

---

## 17. Other

**Issue (low) — `print()` in archive-backed tests:**
`tests/test_index.py`, `tests/test_geometry.py`, `tests/hosts/GO_0xxx/test_geometry.py`,
`tests/hosts/GO_0xxx/test_index.py` call `print('Reading', file)` inside their archive loops.
For tests excluded from the default run (`requires_archive`), this is a minor issue, but it
adds noise under `-s`. Consider removing `print()` calls and relying on pytest's `-v` flag
for file-level progress.

**Issue (low) — `tests/hosts/GO_0xxx/test_geometry.py:8–12` has commented-out imports:**
Three import statements are commented out. Remove them.

**Good note:** `RecordingRecord` in `test_geometry_tables.py` is a well-engineered fake that
records dispatch arguments, enabling precise behavioral assertions on what `Suite` passes to
each table. This pattern should be the model for any future table-type fakes.

---

## 18. Code Coverage

**Target:** ≥90% line+branch coverage, enforced by `fail_under = 90` in
`[tool.coverage.report]`.

**Configuration:** Correct. `[tool.coverage.run]` sets `branch = true`, `parallel = true`,
`source = ["metadata_tools"]`. The `omit` list correctly excludes SPICE-gated and host code:
- `tests/*`
- `*/_version.py`
- `*/metadata_tools/bodies.py`
- `*/metadata_tools/hosts/*`

**Measurement:** `pytest --cov=src` is in `addopts`, so coverage is measured over the full
default suite. This is correct per `python_testing.mdc §9`.

**Known acceptable gaps (properly omitted):**
- `bodies.py` — excluded; tested via integration only.
- `hosts/*` — excluded; tested by `tests/hosts/GO_0xxx/` (requires archive).

**Potential gaps to investigate (run `pytest --cov=src --cov-report=term-missing`):**
- `util.pds_table()` — requires real `cspyce`; no hermetic test.
- `util.sclk_to_ticks()` — wraps `cspyce.sctiks_alias`; always mocked; acceptable.
- `geometry_support/formats.py` — `ALT_FORMAT_DICT` and `MISSION_TABLE` structure is exercised
  indirectly but not directly asserted.

---

## 19. Pytest Markers

**Good:** `--strict-markers` is enabled. Both `integration` and `requires_archive` are
registered with descriptions in `[tool.pytest.ini_options].markers`. Default run correctly
excludes both tiers via `-m "not integration and not requires_archive"`.

**Issue (low) — `test_geometry_cumulative` should use `@pytest.mark.skip` not a bare `return`:**
A test skipped by `return` is invisible in pytest reporting — it appears as PASS even though
nothing ran. Use `@pytest.mark.skip(reason='...')` so it shows up as SKIPPED and can be
tracked.

**Issue (low) — No `xfail` usage exists:**
Not a problem in itself, but documents that no known-failing test is being tracked. The dead
`test_geometry_cumulative` is a candidate for `xfail` rather than `skip` if the feature is
in-progress.

---

## 20. Test Boundary

**Issue (low) — Some tests bypass `__init__` via `Class.__new__(Class)`:**
`test_index_support.py:131` does `IndexTable.__new__(IndexTable)` and then manually sets
attributes. `test_geometry_tables.py:166` does `Suite.__new__(Suite)`. This is necessary when
the constructor requires SPICE or real files. Add a comment on each: `# __new__ bypasses
SPICE-gated __init__ — keep this test hermetic`.

---

## 21. Logging Assertions

**Issue (medium) — Warning-emitting code paths lack log assertions:**
`index_support.py` logs warnings (e.g. for invalid column formats, unused columns).
`geometry_support` emits `warnings.warn(... UserWarning)` for NaN/overflow. The geometry
formatting tests do use `pytest.warns(UserWarning, match='NaN encountered')` — this is the
right pattern. Extend it to cover the logging paths in `index_support.py`:

```python
import warnings
with pytest.warns(UserWarning, match='unused column'):
    # call the path that triggers the warning
```

For `pdslogger`-based warnings (not stdlib `logging`), monkeypatch the logger:
```python
warns_seen: list[str] = []
monkeypatch.setattr(com.get_logger(), 'warn', lambda msg, *a: warns_seen.append(msg % a))
# ... trigger the path ...
assert any('Unused columns' in w for w in warns_seen)
```

---

## 22. Pytest Configuration

**Good:** `testpaths = ["tests"]` and `pythonpath = ["src"]` are set. `addopts` includes
`-n auto`, `--cov=src`, `--strict-markers`, `--strict-config`. `pytest-cov` and
`pytest-xdist` are in `dev` dependencies.

**Issue (high) — `filterwarnings` missing (see §16).**

**No conflicts:** Only `pyproject.toml` is used; no separate `pytest.ini`, `setup.cfg`, or
`.coveragerc`. `[tool.coverage.run]` and `[tool.coverage.report]` are consolidated there.

---

## 23. Snapshot and Golden-File Testing

No snapshot testing is used. The suite tests the generation machinery, not the final file
content byte-for-byte. For a library whose core deliverable is exact PDS3 table/label content,
golden-file testing of a small fixture volume would be high-value:

1. Commit a minimal input under `tests/data/GO_0001/` (a few label stubs and an index).
2. Commit an expected `GO_0001_supplemental_index.tab` and `.lbl`.
3. Add a test that runs `process_index()` against the fixture and asserts the output matches
   the expected file (masking the `LABEL_REVISION_NOTE` timestamp line).
4. Document how to regenerate the golden files when the format changes.

This is the gap between the current hermetic unit tests (which verify the machinery) and
confidence that the end-to-end output format is correct.

---

## Prompt for an AI Agent to Fix Tests

**Copy this prompt into a fresh conversation with no prior context. Do NOT modify any file
under `src/` unless explicitly noted.**

---

You are improving the test suite for `rms-metadata-tools`, a Python package in
`/home/spitale/rms-/rms-metadata-tools`. The package generates PDS3 index/geometry/cumulative
metadata tables.

**Project layout:**
- `src/metadata_tools/` — source
- `tests/` — all tests (pytest, `--strict-markers`, `-n auto`)
- `pyproject.toml` — all config (no separate `pytest.ini` or `.coveragerc`)
- Virtualenv at `./venv`; activate with `source venv/bin/activate`
- Run tests: `pytest`
- Run single test: `pytest tests/test_index_support.py::test_name -v`
- Check coverage: `pytest --cov=src --cov-report=term-missing`
- Lint: `ruff check src tests`

**Rules (from `.cursor/rules/python_testing.mdc`):**
- pytest only (no `unittest.TestCase`)
- All test functions must have `-> None` return annotation and type-annotated parameters
- Every `pytest.raises(ExcType)` must include `match=` asserting the exception message
- Use `monkeypatch` (never `mock.patch`)
- `filterwarnings = ["error"]` must be in pytest config with narrow ignores for third-party
- Use `@pytest.mark.parametrize` for table-driven tests
- Docstrings: Google style with `Parameters:` (not `Args:`)
- 90% line+branch coverage target

---

### Fix 1 — Add `filterwarnings = ["error"]` (HIGH)

**File:** `pyproject.toml`

In `[tool.pytest.ini_options]`, add:
```toml
filterwarnings = [
    "error",
    # Add third-party ignores here as discovered, for example:
    # "ignore::DeprecationWarning:cspyce",
    # "ignore::FutureWarning:oops",
]
```

After adding, run `pytest` and examine any newly-surfaced warnings. For warnings from
third-party packages (oops, cspyce, numpy), add a narrow `ignore::` entry with a comment
explaining the package and why the warning is suppressed. Do not use a blanket
`"ignore::DeprecationWarning"`.

---

### Fix 2 — Add `match=` to `pytest.raises(FileNotFoundError)` (MEDIUM)

**File:** `tests/test_index_support.py` around line 346

First, run the test to get the actual exception message:
```bash
cd /home/spitale/rms-/rms-metadata-tools && source venv/bin/activate
pytest tests/test_index_support.py::test_indextable_init_supplemental_missing_primary_raises -s -v 2>&1 | grep "FileNotFoundError"
```

Then add `match=` with a relevant substring from the actual error message. Example:
```python
with pytest.raises(FileNotFoundError, match=r'GO_0001'):
    IndexTable(FCPath(indir), FCPath(indir), FCPath('/tmpl.lbl'),
               FCPath(meta), qualifier='supplemental', volume_id='GO_0001')
```

---

### Fix 3 — Fix dead test `test_geometry_cumulative` (HIGH)

**File:** `tests/test_geometry.py`

Find the function `test_geometry_cumulative`. It currently starts with `return` as the first
line, making it dead. Replace:

```python
# BEFORE — dead test
def test_geometry_cumulative() -> None:
    return
    # Get labels to test
##### this needs to be changed to match cumulative files
    ...

# AFTER — explicit skip so it shows as SKIPPED in pytest output
@pytest.mark.skip(reason='cumulative geometry label pattern not yet implemented')
def test_geometry_cumulative() -> None:
    """Validate that every cumulative geometry label can be parsed."""
    files = support.match(support.METADATA, '*_cumulative_summary.lbl')
    files = support.exclude(files, 'templates/', 'old/', '__skip/')
    assert len(files) > 0, 'No cumulative geometry labels found'
    for file in files:
        _ = pdstable.PdsTable(file)
```

Verify with: `pytest tests/test_geometry.py -v` — `test_geometry_cumulative` should show as
`SKIPPED` not `PASSED`.

---

### Fix 4 — Move `exists_true` fixture to root `conftest.py` (MEDIUM)

**Step A — Add to `tests/conftest.py`:**

Find the section with `fake_backplane` fixture and add after it:

```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make oops.Body.exists() return True for any name without SPICE."""
    import oops
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```

**Step B — Remove from `tests/test_geometry_masks.py`:**

Delete lines that define the local `exists_true` fixture (the `@pytest.fixture` decorator
line and the two-line function body). The root conftest version will be found automatically.

**Step C — Remove from `tests/test_geometry_prep.py`:**

Same deletion as Step B.

**Verify:**
```bash
pytest tests/test_geometry_masks.py tests/test_geometry_prep.py -v
```
All tests in both files must still pass.

---

### Fix 5 — Fix `Args:` → `Parameters:` in `tests/archive_support.py` (LOW)

**File:** `tests/archive_support.py`

Find all three docstrings that use `Args:`. Replace `Args:` with `Parameters:` in each.
There should be exactly three occurrences (in the `match`, `exclude`, and `bounds` functions).
Verify with: `grep -n 'Args:' tests/archive_support.py` — should return no results after fix.

---

### Fix 6 — Parameterize `_format_value` and `_format_parms` tests (MEDIUM)

**File:** `tests/test_index_support.py`

Find the six individual test functions:
- `test_format_value_character_is_quoted_and_padded`
- `test_format_value_real`
- `test_format_value_integer`
- `test_format_parms_character_width_includes_quotes`
- `test_format_parms_real`
- `test_format_parms_integer`

Replace all six with two parametrized tests:

```python
from typing import Any

@pytest.mark.parametrize('value,fmt,expected', [
    ('IO', 'A10', '"IO        "'),
    (3.14159, 'F8.3', '   3.142'),
    (42, 'I5', '   42'),
], ids=['character', 'real', 'integer'])
def test_format_value(value: Any, fmt: str, expected: str) -> None:
    assert IndexTable._format_value(value, fmt) == expected


@pytest.mark.parametrize('fmt,expected', [
    ('A10', (12, 'CHARACTER')),
    ('F8.3', (8, 'ASCII_REAL')),
    ('I5', (5, 'ASCII_INTEGER')),
], ids=['character', 'real', 'integer'])
def test_format_parms(fmt: str, expected: tuple[int, str]) -> None:
    assert IndexTable._format_parms(fmt) == expected
```

Verify the old tests are gone and the new ones pass: `pytest tests/test_index_support.py -k "format_value or format_parms" -v`

---

### Fix 7 — Move `_reset_task_list` to root conftest (LOW)

**Step A — Add to `tests/conftest.py`:**

At the bottom, after the existing fixtures, add:

```python
from collections.abc import Iterator
import metadata_tools.common as _com

@pytest.fixture(autouse=True)
def _reset_task_list() -> Iterator[None]:
    """Clear the module-level task_list before and after every test."""
    _com.task_list.clear()
    yield
    _com.task_list.clear()
```

**Step B — Remove from `tests/test_common.py`:**

Find the local `_reset_task_list` autouse fixture and delete it (usually defined at the top of
the file or in a class). The root conftest version will take over.

**Verify:**
```bash
pytest tests/test_common.py -v
```
All tests should still pass. Confirm no fixture-conflict error.

---

### Fix 8 — Replace dead `test_geometry_body` in host tests (LOW)

**File:** `tests/hosts/GO_0xxx/test_geometry.py`

Find the `test_geometry_body` function. It reads files but makes no assertions (all bounds
checks are commented out). Add `@pytest.mark.skip`:

```python
@pytest.mark.skip(reason='GOSSI body geometry bounds not yet ported to new test format')
def test_geometry_body() -> None:
    """Validate per-body geometry column bounds for Galileo SSI body summaries."""
    files = support.match(support.METADATA, '*_summary.lbl')
    files = support.exclude(files, 'templates/', 'old/', '__skip/', '_ring_', '_sky_', 'GO_0999/')
    for file in files:
        table = pdstable.PdsTable(file)
        assert table is not None
```

Also remove the commented-out import lines at the top of the file.

---

### Fix 9 — Remove redundant `test_sclk_format_count_returns_str_not_int` (LOW)

**File:** `tests/test_util_math.py`

Find `test_sclk_format_count_returns_str_not_int` (approximately lines 81–85). Delete it.
The roundtrip test immediately below asserts both the type and exact value, making the
isinstance-only test redundant.

Verify: `pytest tests/test_util_math.py -v` — all remaining tests pass.

---

### Verification Checklist

After all fixes, run the full verification sequence:

```bash
cd /home/spitale/rms-/rms-metadata-tools
source venv/bin/activate

# 1. Lint — must be clean
ruff check tests/

# 2. Full default suite
pytest

# 3. Coverage detail — must show ≥90% total
pytest --cov=src --cov-report=term-missing 2>&1 | tail -20

# 4. Confirm skipped tests show as SKIPPED (not PASSED)
pytest tests/test_geometry.py -v | grep -E "PASSED|SKIPPED|FAILED"

# 5. Confirm exists_true fixture is not defined twice
grep -rn 'def exists_true' tests/

# 6. Confirm no Args: in archive_support
grep -n 'Args:' tests/archive_support.py

# 7. Confirm filterwarnings is set
grep -A5 'filterwarnings' pyproject.toml
```

Expected: all `ruff check` clean, `pytest` exits 0, coverage ≥90%, `exists_true` appears
only in `tests/conftest.py`, no `Args:` in `archive_support.py`.
