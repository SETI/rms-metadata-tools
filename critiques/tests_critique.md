# Test Suite Critique Report

**Generated:** 2026-07-14
**Scope:** `tests/` (all 29 test files, `conftest.py`, `columns/conftest.py`, `archive_support.py`) —
every file read completely, line by line — cross-checked against every production module under
`src/metadata_tools/` (63 files) and against `.cursor/rules/python_testing.mdc`,
`.cursor/rules/python.mdc`, `.cursor/rules/filecache.mdc`, `.cursor/rules/logging.mdc`.
`.cursor/rules/logging_nav.mdc` does not exist in this repo; logging-navigation checks are skipped.

---

## Executive Summary

The test suite is well-structured, hermetic by default (no SPICE kernels or `$RMS_METADATA`
holdings required — those tests carry `requires_archive`/`integration` markers and are excluded),
and follows strong modern practices: `--strict-markers`, `--strict-config`,
`filterwarnings = ["error"]`, and `pytest-randomly` for order-independence. **304 tests are
defined; 289 run by default (15 deselected via the `integration`/`requires_archive` markers)** —
an increase of 14 tests since the last critique, driven mainly by the new `.env`/`--ssh-paste`
feature work in commit `f344683`.

**Coverage — measured fresh, this run, full suite:** `pytest tests/ --cov=src` (after clearing the
stale on-disk `.coverage` file) reports **93.02% total line+branch coverage**, comfortably above
the `fail_under = 90` gate in `pyproject.toml`. The previous critique's 22.25% figure was indeed
stale, as suspected; that concern is now resolved with real data. See §18 for the per-module
breakdown.

**A test in the suite is currently failing.** Running the exact command CI uses
(`pytest tests/ --cov=src -n auto`) produces **`1 failed, 288 passed`**:

```text
FAILED tests/test_geometry_constructors.py::test_inventory_other_error_returns_empty
ValueError: boom
```

This is a real regression, not flakiness: commit `c680375` ("fix: apply code-critique
high-severity findings") changed `bodies_select.inventory()` to **re-raise** non-SPICE exceptions
(`ValueError`, `TypeError`, `KeyError`, ...) instead of swallowing them and returning `[]`, but the
test that exercises exactly that branch was never updated to match. Since `run-tests.yml` runs this
exact suite on every push/PR to `main` across Python 3.11/3.12/3.13, **this branch will fail CI on
its next run** until Finding 12.1 below is fixed. This is the single highest-priority item in this
report — see Fix 1.

**Other top priorities (unchanged from the last critique — none of the following were applied):**

1. Fix the failing test (Finding 12.1 / Fix 1) — blocks CI.
2. Zero uses of `@pytest.mark.parametrize` across 304 tests — the single largest maintainability
   debt, and it has grown (Finding 9.1; `test_cli_host.py` alone now has 20 near-identical
   `build_startup_script` tests).
3. Two features shipped in commit `f344683` have **no test coverage at all**: the `.env`
   `$VAR`-expansion loader in `src/metadata_tools/__init__.py` (Finding 2.6, new) and the
   `defs.set_translations()` / `defs._translations` target-name mapping consumed in
   `Record.__init__` (Finding 2.7, new).
3. `cli/_host.py`'s `load_host`, `host_dir_for`, `cloud_dir_for`, `dispatch_cloud_run_if_config`,
   and `run_cloud_worker` remain completely untested (Findings 2.1–2.3 — the previous report's
   suggested fixes for `load_host` were never applied).
4. `pop_argv_flag`'s `SystemExit` still has no `match=` (Finding 1.1, unchanged).

---

## 1. Return values and assertions

**Finding 1.1 — `test_cli_host.py:49`: `pytest.raises(SystemExit)` with no message check. (Unchanged since last critique — not fixed.)**

```python
def test_pop_argv_flag_no_value_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', '--flag'])
    with pytest.raises(SystemExit):   # ← no match=
        pop_argv_flag('--flag')
```

The production code (`src/metadata_tools/cli/_host.py:104`) calls
`sys.exit(f'{flag} requires a value')`. Add the message check:

```python
with pytest.raises(SystemExit, match='--flag requires a value'):
    pop_argv_flag('--flag')
```

**Finding 1.2 — `test_geometry.py::test_inventory` (line 19) and
`test_index.py::test_supplemental_index__cumulative` (line 18) — zero-assertion tests. (Unchanged.)**

Both read PDS labels/tables from the archive tree and discard the result
(`_ = pdsparser.PdsLabel.from_file(file)` / `_ = pdstable.PdsTable(file)`). The test passes if no
exception is raised; nothing about the parsed content is checked. See Fix 4/5.

**Finding 1.3 — `columns/conftest.py:33-34`: existence-only guard assertions in `_load_standalone`.
(Unchanged, low severity — acceptable as defensive guards, but the message could be improved.)**

```python
assert spec is not None
assert spec.loader is not None
```

---

## 2. Success and failure conditions

**Finding 2.1 — `cli/_host.py:load_host` and `host_dir_for` remain completely untested.**

`load_host(host_id)` (`_host.py:15-31`) validates the host directory, calls `sys.exit` for an
unknown host, and mutates `sys.argv`. `host_dir_for` (`_host.py:34-43`) and `cloud_dir_for`
(`_host.py:46-54`) are pure path builders. None of the three has a test in `test_cli_host.py`,
despite the file existing specifically to cover `_host.py`, and despite the previous critique
report proposing exact test bodies for `load_host` (never applied). See Fix 12.

**Finding 2.2 — `dispatch_cloud_run_if_config` (`_host.py:242-358`) is entirely untested.**

This is the most complex function in the module: it shells out via `subprocess.Popen`, rewrites a
YAML config file (`yaml.safe_load`/`yaml.dump`), injects `--service-account` from
`GCP_SERVICE_ACCOUNT`, and has an explicit error path for `--config` values that look like flags
(`_host.py:318-323`). Zero tests exercise any of it — not the happy path, not the YAML-rewrite
error path, not the service-account precedence rule, not the `KeyboardInterrupt`-during-`proc.wait()`
handling (`_host.py:350-353`), not that the two temp files are always cleaned up via `finally`
(`_host.py:355-358`).

**Finding 2.3 — `run_cloud_worker` (`_host.py:406-443`) is entirely untested.**

Drives `asyncio.run(_run())`, conditionally builds a task source from `--volumes`
(`_host.py:427-434`), and translates `KeyboardInterrupt` into `sys.exit(130)` (`_host.py:441-442`).
No test mocks `cloud_tasks.worker.Worker` to exercise any of this.

**Finding 2.4 — `util.pds_table` (`util.py:21-32`) is untested. (Unchanged.)**

**Finding 2.5 — `label_support.create`'s `system` parameter is never exercised with a non-empty
value. (Unchanged.)** `test_label_support.py` covers the missing-file early return, the global
template path, the host template path, and the inventory-preprocessor-disabled path, but no test
passes `system='JUPITER'` (or any non-empty string), so the `offset = 0 if not system else
len(system) + 1` branch at `label_support.py:55` and the corresponding template-name slicing at
`label_support.py:58` are untested.

**Finding 2.6 — NEW: the `.env` `$VAR`-expansion loader in `src/metadata_tools/__init__.py:22-37`
has zero test coverage.**

This module-level code (added in commit `f344683`) runs at package import time:

```python
_env_file = _Path(__file__).parent.parent.parent / '.env'
if _env_file.is_file():
    with _env_file.open(encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                _k = _k.strip()
                _v = _os.path.expandvars(_v.strip())
                _os.environ.setdefault(_k, _v)
```

It has real branching logic — blank-line skip, `#`-comment skip, `$VAR` expansion against
previously-set env vars *within the same file*, and `setdefault` (does not clobber an
already-set env var) — none of which is exercised by any test. `grep -rn "_env_file"
tests/` returns nothing. This is exactly the kind of import-time logic that silently breaks (e.g.
if a future edit changes `setdefault` to `os.environ[k] = v` and starts clobbering real env vars)
without a single test catching it. See Fix 16.

**Finding 2.7 — NEW: `defs.set_translations()` and the `defs._translations` lookup consumed in
`Record.__init__` (`geometry_support/record.py:75-76`) have zero test coverage.**

Added in the same `f344683` refactor. `record.py:75-76`:

```python
if self.target in defs._translations:
    self.target = defs._translations[self.target]
```

No test in `test_geometry_constructors.py` (which covers `Record.__init__` extensively via
`_patch_record_spice`) ever calls `defs.set_translations(...)` before constructing a `Record`, so
this branch — and `set_translations` itself — is never executed by the suite. See Fix 17.

**Finding 2.8 — `cumulative_support._cat_rows`'s `volumes=` filter path remains untested.
(Unchanged — the previous critique's Fix 13 for this was never applied.)**

`_cat_rows` (`cumulative_support.py:21-106`) accepts a `volumes: list[str] | None` keyword
(line 80: `if not volumes or vol in volumes:`) but every test in `test_cumulative_support.py`
either omits it or only exercises `exclude=`. See Fix 13 (unchanged from before).

**Finding 2.9 — `create_cumulative_indexes`'s explicit `volumes` parameter (as opposed to
`args.volumes`) is never tested.** `cumulative_support.py:137-183`: the function signature accepts
`volumes: list[str] | None = None` which "Overrides args.volumes" per its docstring
(`cumulative_support.py:145`), but `test_create_cumulative_indexes_fires_eight_cat_rows` only
passes `args=types.SimpleNamespace(..., volumes=None, ...)` and never the explicit `volumes=`
keyword.

**Finding 2.10 — `common.get_common_args`'s `metadata_arg=None` / `output_arg=None` branches and
the `--pattern` flag are untested.** `test_common.py::test_get_common_args_skips_volume_when_none`
only covers `volume_arg=None`; the analogous `metadata_arg=None` and `output_arg=None` branches
(`common.py:108-115`) and the `--pattern`/`-p` flag (`common.py:122-123`) have no direct test.

**Finding 2.11 — `config.get_geometry_config()`'s caching behavior is untested.** The docstring
(`config.py:118-119`) states "Subsequent calls return the cached module," but no test verifies
that a second call does not re-invoke `importlib.import_module`. `test_set_host_imports_and_registers_host_modules`
calls `get_geometry_config()` only once.

---

## 3. Consistency

**Finding 3.1 — `test_geometry_record.py:90`: `_fake_registry` helper is a plain function, not a
fixture. (Unchanged.)**

**Finding 3.2 — `test_config.py:17`: `_clear_config` is a plain function called in every test
rather than a fixture. (Unchanged.)**

**Finding 3.3 — Archive tests use bare `print()` for progress output instead of `capsys` or
structured logging. (Unchanged in substance; line numbers updated for the current file state.)**

Current exact locations:

| File | Lines |
|---|---|
| `tests/test_geometry.py` | 26, 28, 44, 54, 69, 71, 92, 94, 131, 133, 174, 176 |
| `tests/test_index.py` | 26, 27, 40, 42 |
| `tests/hosts/GO_0xxx/test_geometry.py` | 25, 27, 44, 46, 62, 64 |
| `tests/hosts/GO_0xxx/test_index.py` | 25, 27 |

This violates the "no bare `print()` in library code" convention in `python.mdc` (applies to all
code, tests included, per `python_testing.mdc` §"complement `python`"). These are unasserted
debug/progress lines. See Fix 3.

**Finding 3.4 — `tests/hosts/GO_0xxx/test_geometry.py:32` — needlessly convoluted assertion.**

```python
assert np.any(np.where(table.column_values['VOLUME_ID'] != volume)) != np.True_, file
```

This double-negates through `np.where(...)` (returning index tuples) then `np.any(...)` then
compares against the numpy scalar `np.True_`, to mean "no row has the wrong `VOLUME_ID`." It is
correct (verified: `np.True_` still exists in numpy 2.4.6, the version installed here) but very
hard to read. Rewrite as:

```python
assert not np.any(table.column_values['VOLUME_ID'] != volume), file
```

---

## 4. Completeness

**Coverage map — this run measured coverage, per module (see §18 for the full table):**

| Module | Tests | Assessment |
|---|---|---|
| `config.py` | `test_config.py` | 100% lines — all public paths covered; caching behavior untested (Finding 2.11) |
| `common.py` | `test_common.py` | 97% — `get_common_args` edge cases untested (Finding 2.10) |
| `task_list_support.py` | `test_task_list.py` | 100% — all public functions covered |
| `label_support.py` | `test_label_support.py` | 98% — `system` arg untested (Finding 2.5) |
| `util.py` | `test_util_*.py` (5 files) | 97% — `pds_table`, `sclk_to_ticks` untested directly (Findings 2.4, 4.1) |
| `cumulative_support.py` | `test_cumulative_support.py` | 92% — `volumes` filter untested (Finding 2.8) |
| `defs.py` | none directly | 95% — `set_translations` untested (Finding 2.7) |
| `index_support/table.py` | `test_index_support.py` | 95% — thorough |
| `geometry_support/formatting.py` | `test_geometry_formatting.py` | 91% — thorough |
| `geometry_support/masks.py` | `test_geometry_masks.py` | 99% — thorough |
| `geometry_support/prep.py` | `test_geometry_prep.py` | 87% |
| `geometry_support/record.py` | `test_geometry_record.py`, `test_geometry_constructors.py`, `test_geometry_tables.py` | 91% — translation branch untested (Finding 2.7) |
| `geometry_support/formats.py` | none directly | 94% — `get_mission_table()` never directly unit-tested (Finding 4.2) |
| `geometry_support/bodies_select.py` | `test_geometry_constructors.py`, `test_geometry_record.py` | 92% — currently has a **failing** test (Finding 12.1) |
| `columns/body.py` | none directly (only via `integration`-marked tests) | 60% — lowest-covered non-excluded module |
| `cli/_host.py` | `test_cli_host.py` | excluded from coverage denominator (`pyproject.toml:151-157`), but `load_host`, `dispatch_cloud_run_if_config`, `run_cloud_worker` untested (Findings 2.1-2.3) |
| `cli/index.py`, `geometry.py`, `cumulative.py`, `*_cloud.py`, `*_worker.py` | none | excluded from coverage denominator; `main()` entry points entirely untested |
| `src/metadata_tools/__init__.py` | none | 95% overall, but the `.env` loader block specifically is untested (Finding 2.6) |
| `bodies.py` | `test_columns_integration.py` (`integration`-marked, excluded by default) | excluded from coverage (SPICE-dependent) |

**Finding 4.1 — `util.py:sclk_to_ticks` (line 520) is never directly tested. (Unchanged.)** It is
monkeypatched out everywhere it is used as a collaborator (`test_util_math.py`,
`test_geometry_record.py`) but the function itself — a one-line wrapper around
`cspyce.sctiks_alias` — has no test that calls the real implementation.

**Finding 4.2 — NEW: `geometry_support/formats.get_mission_table()` (`formats.py:127`) has no
direct unit test.** It is only exercised indirectly through `Record.__init__` in
`test_geometry_constructors.py`, where the fake `geometry_config.MISSION_TABLE = []` (installed by
`tests/conftest.py`) makes the function's internals a no-op. Its actual caching/conversion logic
(reading `MISSION_TABLE`, if any) is never exercised.

---

## 5. Redundancy

**Finding 5.1 — `test_config.py:28-49` — four nearly identical "unregistered" tests. (Unchanged.)**
See Fix 2 (unchanged).

**Finding 5.2 — `test_geometry_masks.py` — 13 tests with a near-identical
backplane/mask/attribute/assert structure. (Unchanged.)** Ideal `@pytest.mark.parametrize`
candidates.

**Finding 5.3 — `test_cli_host.py::build_startup_script` tests — now 20 near-identical tests
(grown from 10 since the last critique).** Lines 159–494 contain 20 tests, each creating a temp
startup-script file, setting `sys.argv`, deleting/setting env vars, and calling
`build_startup_script`. The setup boilerplate (`tpl = tmp_path / 'startup.sh'; tpl.write_text(...)`
plus the `monkeypatch.delenv('GCP_DEBUG_BRANCH', ...)` / `monkeypatch.delenv('GCP_STARTUP_TEMPLATE', ...)`
pair) is repeated in all 20. This has gotten measurably worse since the previous critique (10 → 20)
because none of the previously-suggested cleanup (a shared fixture) was applied while five new
tests (SSH-paste variants, `test_build_startup_expands_env_vars_in_argv`) were added using the same
copy-pasted pattern. See Fix 11.

**Finding 5.4 — `test_geometry_process.py` — three tests share an identical inline `FakeSuite`
class definition. (Unchanged.)**

---

## 6. Parallel execution

**Finding 6.1 — `conftest.py:_install_fakes()` module-import-time global state. (Unchanged;
assessed safe under process-based `pytest-xdist`.)**

**Finding 6.2 — `test_util_math.py:127`: `np.random.seed(0)` mutates global NumPy legacy random
state. (Unchanged.)** See Fix 6 (unchanged).

---

## 7. Mocking and dependency isolation

**Finding 7.1 — `test_geometry_tables.py:235-238,257-260`: logger mock (`SimpleNamespace`) lacks
an `.open()`/`.error()` method — brittle to future `suite.create()` changes. (Unchanged.)**

**Finding 7.2 — `test_cli_host.py` imports the private `metadata_tools.cli._host` module.
(Unchanged, deliberate/acceptable — this file is specifically for `_host.py`.)**

**Finding 7.3 — No tests mock `cloud_tasks.worker.Worker` for `run_cloud_worker`'s async path.
(Unchanged — see Finding 2.3, now the primary framing of this gap.)**

**Finding 7.4 — `test_geometry_constructors.py` patch targets are correct (module-attribute
lookup location, not definition location). No issue.**

---

## 8. Security and input validation

**Finding 8.1 — No tests for `pop_argv_flag`/`build_startup_script` with adversarial or
shell-metacharacter flag values. (Unchanged.)** Given the new `.env` `$VAR`-expansion feature
(Finding 2.6) and `os.path.expandvars(arg)` applied to every worker-command argument
(`_host.py:179`), there is now an *additional* untested surface: a `.env` value or CLI argument
containing `$(...)`, backticks, or other shell metacharacters flowing into the generated startup
script. `shlex.join`/`shlex.quote` are used downstream (`_host.py:182`, `_host.py:208-209`), which
should neutralize this, but no test exercises a value containing `$`, backticks, or quotes to
confirm the quoting holds after `expandvars` substitution.

**Finding 8.2 — `dispatch_cloud_run_if_config` uses `subprocess.Popen` with `shell=False` (safe)
but has zero test coverage of the argument-list assembly (see Finding 2.2).** A future regression
in `modified_cloud_args` assembly (e.g. inserting `None`) would only surface at runtime, and there
would be no test to catch a `shell=True` regression either.

No credential leakage or path-traversal issues found in the test suite itself.

---

## 9. Parameterization

**Finding 9.1 — Zero uses of `@pytest.mark.parametrize` across 304 tests (up from 290; this gap
has grown, not shrunk).**

| Group | File | Lines | # cases |
|---|---|---|---|
| `add_by_base` variants | `test_util_math.py` | 13–29 | 4 |
| `_ninety_percent_gap_degrees` variants | `test_util_range_mod360.py` | 13–25 | 3 |
| `_get_range_mod360` variants | `test_util_range_mod360.py` | 31–67 | 7 |
| `replace` variants | `test_util_replace.py` | 16–91 | 9 |
| unregistered-config errors | `test_config.py` | 28–49 | 4 |
| `format_value` variants | `test_index_support.py` | 37–47 | 3 |
| `format_parms` variants | `test_index_support.py` | 52–62 | 3 |
| `get_null_value` variants | `test_index_support.py` | 68–89 | 4 |
| `formatted_column` variants | `test_geometry_formatting.py` | 17–75 | 8 |
| `circle_coverage` variants | `test_geometry_formatting.py` | 81–105 | 4 |
| mask variants | `test_geometry_masks.py` | 22–133 | 13 |
| **`build_startup_script` variants** | `test_cli_host.py` | 159–494 | **20 (was 10)** |

**Finding 9.2 — Boundary tests missing for `sclk_split_count` pad-to-four field. (Unchanged.)**

**Finding 9.3 — No boundary test for `write_txt_file` with an empty list. (Unchanged.)**

**Finding 9.4 — NEW: no boundary test for `build_startup_script`'s `$VAR` expansion with an
*undefined* variable.** `test_build_startup_expands_env_vars_in_argv`
(`test_cli_host.py:482-494`) only covers the case where `RMS_VOLUMES_GCP` is set. `os.path.expandvars`
leaves `$UNDEFINED_VAR` as a literal string when the variable is not set (does not raise) — this
documented-by-omission behavior has no test.

---

## 10. Async (not applicable)

No async tests. `run_cloud_worker`'s `asyncio.run(_run())` path (Finding 2.3) remains completely
untested.

---

## 11. Output and contract

**Finding 11.1 — `test_geometry_tables.py:130`: `endswith` instead of exact match. (Unchanged.)**
See Fix 7 (unchanged).

**Finding 11.2 — `test_columns_integration.py:29`: `len() > 0` instead of exact set comparison.
(Unchanged — this test also carries `pytest.mark.integration` so is excluded from the default run;
lower urgency, but still worth fixing.)**

---

## 12. Error handling

**Finding 12.1 — CRITICAL, NEW: `test_geometry_constructors.py::test_inventory_other_error_returns_empty`
(lines 47–55) currently FAILS.**

```python
def test_inventory_other_error_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)

    def _raise(bodies: Any, expand: Any, cache: Any) -> Any:
        raise ValueError('boom')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    assert bodies_select.inventory(record, ['IO']) == []  # type: ignore[arg-type]
```

Verified by running `pytest tests/ --cov=src -n auto` in this environment:

```text
FAILED tests/test_geometry_constructors.py::test_inventory_other_error_returns_empty
ValueError: boom
1 failed, 288 passed
```

**Root cause:** `bodies_select.inventory()` (`geometry_support/bodies_select.py:24-61`) was changed
in commit `c680375` ("fix: apply code-critique high-severity findings" — "Re-raise in
bodies_select.inventory() broad except instead of returning []") to **re-raise**
`ValueError`/`TypeError`/`KeyError`/`AttributeError`/`IndexError`/`LookupError`/`AssertionError`
(`bodies_select.py:58-61`) instead of catching them and returning `[]`. Only `OSError`/`RuntimeError`
containing `SPICE(NOFRAMECONNECT)` or `SPICE(CKINSUFFDATA)` (or any other `OSError`/`RuntimeError`)
still return `[]` (`bodies_select.py:44-55`). The test was never updated to match, so it now asserts
the *old*, no-longer-true behavior for a `ValueError`. This is exactly the "other errors are genuine
bugs" contract the production code now documents and enforces — the test needs to assert the
**new** contract (the exception propagates) instead. See Fix 1 — this must be applied first, before
any other fix in this report, because it currently blocks `scripts/run-all-checks.sh` and CI.

**Finding 12.2 — `test_cli_host.py:49`: see Finding 1.1 (duplicate cross-reference).**

---

## 13. State and workflow

**Finding 13.1 — `test_index_support.py::test_create_index_processes_each_volume` — verified
correct, no finding.** (Unchanged assessment.)

**Finding 13.2 — No idempotency test for `conftest._install_fakes()` / double-registration via
`config.set_current()`. (Unchanged.)**

---

## 14. Test data and fixtures

**Finding 14.1 — `tests/columns/conftest.py` `ring_module`/`sky_module`/`sun_module` are
`scope='session'` fixtures loading modules with mutable module-level state. (Unchanged — currently
safe because tests are read-only.)**

**Finding 14.2 — `test_cli_host.py`: now 20 tests (was 10) each write their own near-identical temp
startup-script file. (Same root cause as Finding 5.3; see Fix 11.)**

**Finding 14.3 — `tests/archive_support.py:46-52` `exclude()` uses `range(len(files))` instead of
direct iteration. (Unchanged.)** See Fix (unchanged from before, low severity).

**Finding 14.4 — `conftest.py:silent_logger` fixture name implies a logger is returned, but it
returns `None` and monkeypatches `common.get_logger`. (Unchanged, low severity — see also Finding
7.1: the `SimpleNamespace` it installs still lacks `.open()`/`.error()`/`.debug()`.)**

**Finding 14.5 — NEW: `archive_support.py` itself (the shared helper module for all
`requires_archive` tests) has no unit tests of its own.** `match()`, `exclude()`, and `bounds()`
(lines 18-89) are non-trivial helpers (`bounds()` recurses to add `MINIMUM_`/`MAXIMUM_` prefixes,
handles `invalid_values` null-exclusion) used by every archive-tier test, but none of them is
directly unit-tested. Because these are themselves excluded from coverage measurement only by
virtue of being under `tests/` (`pyproject.toml:151`: `omit = ["tests/*", ...]`), a bug here would
silently make every `requires_archive` bounds check pass or fail incorrectly. Given they're pure
functions taking plain lists/dicts, they would be cheap and valuable to unit-test directly (no
archive tree required) — see Fix 18.

---

## 15. Flakiness indicators

**Finding 15.1 — `test_util_math.py:127`: `np.random.seed(0)`. (Unchanged.)**

**Finding 15.2 — `test_geometry_formatting.py::test_iso_route`: hard-coded UTC offset in the
expected ISO string. (Unchanged.)**

---

## 16. Regression and documentation

**Finding 16.1 — `test_geometry_columns_contract.py` documents its regression story well. Good
practice, no change.**

**Finding 16.2 — `test_cli_host.py::test_build_startup_empty_startup_template_env_uses_default`
carries a regression docstring. Good practice, no change.**

**Finding 16.3-16.6 — `filterwarnings`, `--strict-markers`, `pytest-randomly`, no deprecated API
usage — all still correctly configured. No change.**

**Finding 16.7 — NEW: the `f344683` commit message documents "Add test_build_startup_expands_env_vars_in_argv"
as its only test addition, but the commit also changed `defs.py` (`set_translations`),
`record.py` (translation lookup), and `src/metadata_tools/__init__.py` (`.env` loader) with zero
accompanying tests for those three (Findings 2.6, 2.7).** Per `git_workflow.mdc`'s expectation that
behavior changes ship with tests, these three should have had coverage added in the same commit.

---

## 17. Other

**Finding 17.1 — `print()` in archive test bodies. (Unchanged in substance; see Finding 3.3 for
current line numbers.)**

**Finding 17.2 — Terse test naming in `test_geometry_tables.py`. (Unchanged.)**

**Finding 17.3 — `test_geometry_prep.py:183`: `.strip().isdigit()` non-specific assertion.
(Unchanged.)** See Fix 9 (unchanged).

**Finding 17.4 — `test_geometry_prep.py::test_multiple_tile_sets_tuple_emits_a_row_per_set`
docstring references a bug fix with no issue link. (Unchanged, low severity.)**

**Finding 17.5 — `hosts/GO_0xxx/test_geometry.py:32`: see Finding 3.4 (new, moved here from
"Other" in spirit but filed under Consistency since it's a readability issue, not a behavioral
gap).**

---

## 18. Code coverage

**Target:** 90% line+branch coverage (`pyproject.toml:165`, `fail_under = 90`).

**Status: MEASURED FRESH, this session, full default suite** (`pytest tests/ --cov=src -n auto`,
after deleting the stale on-disk `.coverage` file):

```text
TOTAL   1434 stmts   69 miss   530 branch   62 partial   93.02% cover
Required test coverage of 90.0% reached. Total coverage: 93.02%
```

This resolves the previous critique's open question — the 22.25% figure on disk was stale, as
suspected. **The coverage gate passes comfortably.** Full per-module table:

| Module | Stmts | Miss | Branch | BrPart | Cover |
|---|---|---|---|---|---|
| `__init__.py` | 14 | 0 | 6 | 1 | 95% |
| `columns/__init__.py` | 6 | 0 | 0 | 0 | 100% |
| `columns/body.py` | 32 | 12 | 8 | 0 | **60%** (lowest) |
| `columns/ring.py` | 28 | 0 | 10 | 0 | 100% |
| `columns/sky.py` | 3 | 0 | 0 | 0 | 100% |
| `columns/sun.py` | 4 | 0 | 0 | 0 | 100% |
| `common.py` | 69 | 1 | 20 | 2 | 97% |
| `config.py` | 35 | 0 | 10 | 0 | 100% |
| `cumulative_support.py` | 75 | 3 | 30 | 5 | 92% |
| `defs.py` | 21 | 1 | 0 | 0 | 95% |
| `geometry_support/__init__.py` | 6 | 0 | 0 | 0 | 100% |
| `geometry_support/bodies_select.py` | 76 | 4 | 36 | 5 | 92% |
| `geometry_support/formats.py` | 15 | 0 | 2 | 1 | 94% |
| `geometry_support/formatting.py` | 69 | 4 | 44 | 6 | 91% |
| `geometry_support/masks.py` | 39 | 0 | 32 | 1 | 99% |
| `geometry_support/prep.py` | 108 | 11 | 64 | 11 | 87% (lowest non-excluded besides columns/body.py) |
| `geometry_support/process.py` | 54 | 4 | 24 | 3 | 91% |
| `geometry_support/record.py` | 101 | 6 | 36 | 4 | 91% |
| `geometry_support/suite.py` | 112 | 7 | 40 | 5 | 92% |
| `geometry_support/tables.py` | 35 | 1 | 8 | 1 | 95% |
| `index_support/__init__.py` | 4 | 0 | 0 | 0 | 100% |
| `index_support/key_fns.py` | 10 | 0 | 0 | 0 | 100% |
| `index_support/process.py` | 50 | 6 | 16 | 6 | 82% |
| `index_support/table.py` | 180 | 4 | 62 | 7 | 95% |
| `label_support.py` | 36 | 0 | 6 | 1 | 98% |
| `task_list_support.py` | 25 | 0 | 8 | 0 | 100% |
| `util.py` | 227 | 5 | 68 | 3 | 97% |

**Below-target / notable modules:**
- `columns/body.py` at 60% is the weakest measured module (12/32 statements missed). It is
  imported at collection time via `columns/conftest.py`'s standalone-loading trick for
  `ring`/`sky`/`sun`, but `body.py` itself has no dedicated `test_body.py` — only the
  `integration`-marked `test_columns_integration.py` touches it, and that's excluded by default.
- `index_support/process.py` at 82% and `geometry_support/prep.py` at 87% are the next-weakest.

**Modules correctly excluded from the coverage denominator** (`pyproject.toml:151-157`):
`tests/*`, `*/_version.py`, `*/metadata_tools/bodies.py`, `*/metadata_tools/hosts/*`,
`*/metadata_tools/cli/*`.

**Known gaps not in the denominator but worth integration-testing** (unchanged from before):
`cli/index.py`, `cli/geometry.py`, `cli/cumulative.py`, `cli/*_cloud.py`, `cli/*_worker.py`,
`hosts/GO_0xxx/*`.

---

## 19. Pytest markers

All custom markers are registered (`pyproject.toml:65-68`) and `--strict-markers` is enabled. No
change from the previous critique. `columns/test_columns_integration.py:14` correctly uses
`pytestmark = pytest.mark.integration`. No `xfail` or stale `skip`/`skipif` markers exist.

**Finding 19.1 — No `slow` marker. (Unchanged.)**

---

## 20. Test boundary (public API vs internals)

**Finding 20.1 — `test_cli_host.py:14-22` imports private `_host` module functions. (Unchanged,
deliberate/acceptable.)**

**Finding 20.2 — `test_index_support.py` accesses `IndexTable._format_value`, `_format_parms`,
`_get_null_value`, `_get_column_values`, `_format_column`, `_index_one_value` directly.
(Unchanged, accepted white-box testing practice for this class.)**

**Finding 20.3 — `test_geometry_record.py:138,144-145`: assertions on the internal `record.dicts`
attribute structure. (Unchanged, medium severity.)**

---

## 21. Logging assertions

**Finding 21.1 — No `caplog` usage anywhere (PdsLogger is not stdlib `logging`, so this is
expected, not a gap).**

**Finding 21.2 — `silent_logger` fixture suppresses PdsLogger output but nothing verifies it is
actually called. (Unchanged.)**

**Finding 21.3 — NEW: `test_common.py::test_init_logger_registers_handlers`
(`test_common.py:112-124`) only asserts `('stdout',) in handlers`; it does not assert that the file
handler (`('file', path)`, from the monkeypatched `pdslogger.file_handler`) was also added, nor
that `_LOGGER.log('header', 'Initialized %s log for %s', log_type, log_dir.name)` fired with the
expected arguments.** The `handlers` list in the test also conflates two different call sites
(`add_handler` appends the handler directly; `log` appends a `('log', msg)` tuple), making the
single assertion weaker than the fixture setup implies. Strengthen to:

```python
def test_init_logger_registers_handlers(monkeypatch: pytest.MonkeyPatch,
                                        tmp_path: Path) -> None:
    handlers: list[Any] = []
    fake_logger = types.SimpleNamespace(
        add_handler=lambda h: handlers.append(h),
        log=lambda level, msg, *a: handlers.append(('log', level, msg, a)))
    monkeypatch.setattr(com, '_LOGGER', fake_logger)
    monkeypatch.setattr(pdslogger, 'file_handler',
                        lambda path, level: ('file', path))
    monkeypatch.setattr(pdslogger, 'STDOUT_HANDLER', ('stdout',))
    log_dir = FCPath(tmp_path)
    com.init_logger(log_dir, 'index')
    expected_path = log_dir / f'{log_dir.name}_index-log.txt'
    assert ('stdout',) in handlers
    assert ('file', expected_path) in handlers
    assert ('log', 'header', 'Initialized %s log for %s', ('index', log_dir.name)) in handlers
```

(Drop the throwaway `assert (...) or True` line above when writing the real test — it is left in
only to flag that the exact `log_dir.name` used in the filename assertion depends on what
`tmp_path`'s basename actually is; adjust `'GO_0001_index-log.txt'` to
`f'{FCPath(tmp_path).name}_index-log.txt'` so the assertion is not hard-coded against a directory
name pytest did not actually create.)

---

## 22. Pytest configuration

No changes since the previous critique: `pythonpath`, `testpaths`, `addopts`
(`-n auto --cov=src --strict-markers --strict-config -m "not integration and not requires_archive"`),
`markers`, and `filterwarnings = ["error"]` are all present and correct.

**Finding 22.1 — No `pytest-timeout` in dev dependencies. (Unchanged.)**

**Finding 22.2 — `pytest-randomly` seed not pinned/logged in CI for reproducibility. (Unchanged.)**
`run-tests.yml`'s `test` job runs `python -m pytest --cov=src --cov-report=xml -n auto tests`
directly (not via `scripts/run-all-checks.sh`), so a randomly-ordered failure in CI has no captured
seed to reproduce locally; consider `pytest --randomly-seed=last` guidance in the contributor docs
or logging the seed explicitly in the CI step.

---

## 23. Snapshot and golden-file testing

No change from the previous critique — no snapshot tests exist, none are currently needed; the
archive-backed tests function as informal golden-file tests already.

---

## Prompt for an AI agent to fix tests

You are fixing the test suite of `rms-metadata-tools` (package `metadata_tools`) based on the
critique report above. The source is in `src/metadata_tools/`. Tests are in `tests/`. **Do not
modify any production code** in `src/` EXCEPT where a fix explicitly says to touch `src/` (only
Fix 1 may require a judgment call about which side is "correct" — see below). Only add, modify, or
remove lines in `tests/` for all other fixes.

Preserve all existing passing tests (do not delete or weaken assertions). Add or strengthen
assertions, add parametrize, add new test functions, and fix the issues described below.

### Working directory
`/home/spitale/rms-/rms-metadata-tools`

### Setup
```bash
source venv/bin/activate
pytest tests/ --cov=src --cov-report=term-missing -n auto 2>&1 | tail -40
```

---

### Fix 1 — CRITICAL, DO THIS FIRST: repair the currently-failing test

**File:** `tests/test_geometry_constructors.py`, lines 47–55.

Run the suite first to confirm the failure:
```bash
pytest tests/test_geometry_constructors.py::test_inventory_other_error_returns_empty -v
```

You will see `ValueError: boom` propagate out of `bodies_select.inventory()`. This is expected:
`src/metadata_tools/geometry_support/bodies_select.py:58-61` deliberately re-raises
`ValueError`/`TypeError`/`KeyError`/`AttributeError`/`IndexError`/`LookupError`/`AssertionError`
as "genuine bugs" (this was an intentional behavior change in commit `c680375`). The test still
asserts the pre-`c680375` contract (`== []`). Update the test to assert the **current, intended**
contract — that the exception propagates — and rename it to match:

```python
def test_inventory_other_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-SPICE exceptions from observation.inventory() are genuine bugs and must propagate."""
    monkeypatch.setattr(config, 'EXPAND', 0.0, raising=False)

    def _raise(bodies: Any, expand: Any, cache: Any) -> Any:
        raise ValueError('boom')

    obs = types.SimpleNamespace(inventory=_raise)
    record = types.SimpleNamespace(observation=obs, pointing_available=True)
    with pytest.raises(ValueError, match='boom'):
        bodies_select.inventory(record, ['IO'])  # type: ignore[arg-type]
    # Non-CKINSUFFDATA/non-SPICE errors must NOT clear pointing_available (only the
    # SPICE(CKINSUFFDATA)/SPICE(NOFRAMECONNECT) branch does that).
    assert record.pointing_available is True
```

This also folds in the previous critique's suggested strengthening (asserting
`pointing_available` is left unchanged). After this change, run:
```bash
pytest tests/ --cov=src -n auto
```
and confirm `0 failed`.

---

### Fix 2 — Parametrize the four unregistered-config tests

**File:** `tests/test_config.py`, lines 28–49.

```python
from typing import Any

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

Delete the original four test functions.

---

### Fix 3 — Remove bare `print()` from archive test bodies

Delete every `print()` call at these exact locations (leave everything else unchanged):

- `tests/test_geometry.py`: lines 26, 28, 44, 54, 69, 71, 92, 94, 131, 133, 174, 176
- `tests/test_index.py`: lines 26, 27, 40, 42
- `tests/hosts/GO_0xxx/test_geometry.py`: lines 25, 27, 44, 46, 62, 64
- `tests/hosts/GO_0xxx/test_index.py`: lines 25, 27

---

### Fix 4 — Add an assertion to `test_inventory` (archive test)

**File:** `tests/test_geometry.py`, `test_inventory` (starts at line 19).

```python
def test_inventory() -> None:
    files = support.match(support.METADATA, '*_inventory.lbl')
    files = support.exclude(files, 'templates/', 'old/', '__skip/')
    for file in files:
        label_dict = pdsparser.PdsLabel.from_file(file).as_dict()
        assert label_dict, f'Empty label dict in {file}'
```

---

### Fix 5 — Add an assertion to `test_supplemental_index__cumulative`

**File:** `tests/test_index.py`, `test_supplemental_index__cumulative` (starts at line 18).

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

### Fix 6 — Replace `np.random.seed(0)` with an isolated RNG

**File:** `tests/test_util_math.py`, lines 124–129.

Check `src/metadata_tools/util.py:range_of_n_angles` (line 565) first — it calls `np.random.rand`
internally with no way to inject a generator. Two options, in order of preference:

1. (Preferred, requires a `src/` change) Add an optional `rng: np.random.Generator | None = None`
   parameter to `range_of_n_angles` in `src/metadata_tools/util.py`, defaulting to
   `np.random.default_rng()` when `None`, and use `rng.random(n) * 360.` instead of
   `np.random.rand(n) * 360.`. Then:
   ```python
   def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
       rng = np.random.default_rng(0)
       result = util.range_of_n_angles(5, tests=200, rng=rng)
       assert result == pytest.approx(<value observed after running with the new rng path>)
   ```
   Run the test once to capture the actual `pytest.approx` value for the new RNG stream (it will
   differ from the legacy-RNG value since `default_rng` uses a different algorithm).
2. (Test-only, if you do not want to touch `src/`) Keep `np.random.seed(0)` but isolate it:
   ```python
   def test_range_of_n_angles_is_deterministic_when_seeded() -> None:
       state = np.random.get_state()
       try:
           np.random.seed(0)
           result = util.range_of_n_angles(5, tests=200)
       finally:
           np.random.set_state(state)
       assert result == pytest.approx(125.7494161526109)
   ```
   This still mutates global state transiently but restores it, removing the parallel-worker leak.

---

### Fix 7 — Strengthen `test_record_add_named_column_dict` assertion

**File:** `tests/test_geometry_tables.py`, line 130.

```python
# CURRENT:
assert lines[0].endswith('  28.648,  57.296')
# FIXED:
assert lines[0] == '"vol","file",  28.648,  57.296'
```

---

### Fix 8 — (superseded by Fix 1) — `pointing_available` assertion now lives inside Fix 1's
rewritten test. No separate action needed.

---

### Fix 9 — Strengthen `test_detailed_subregions_emit_rows` subregion assertion

**File:** `tests/test_geometry_prep.py`, line 183.

```python
# CURRENT:
assert rows[0][-2].strip().isdigit()
# FIXED:
assert rows[0][-2].strip() == '0'   # first (and only) subregion index is 0
```

---

### Fix 10 — Fix the confusing `np.True_` assertion for readability

**File:** `tests/hosts/GO_0xxx/test_geometry.py`, line 32.

```python
# CURRENT:
assert np.any(np.where(table.column_values['VOLUME_ID'] != volume)) != np.True_, file
# FIXED:
assert not np.any(table.column_values['VOLUME_ID'] != volume), file
```

---

### Fix 11 — Add a startup-template fixture and parametrize `build_startup_script` tests

**File:** `tests/test_cli_host.py`

Add near the top of the file, after `_simple_parser`:

```python
@pytest.fixture
def startup_tpl(tmp_path: Path) -> Path:
    """A minimal startup template for build_startup_script tests."""
    tpl = tmp_path / 'startup.sh'
    tpl.write_text('echo hello\n')
    return tpl


@pytest.fixture(autouse=True)
def _clean_startup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """build_startup_script tests assume a clean env unless they set/delete explicitly."""
    monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
    monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
```

Then, for every `test_build_startup_*` test that currently does:
```python
tpl = tmp_path / 'startup.sh'
tpl.write_text('echo hello\n')
...
monkeypatch.delenv('GCP_DEBUG_BRANCH', raising=False)
monkeypatch.delenv('GCP_STARTUP_TEMPLATE', raising=False)
```
replace the `tpl = ...` / `tpl.write_text(...)` lines with a `startup_tpl: Path` fixture parameter
and use `startup_tpl` instead of `tpl`; delete the now-redundant `monkeypatch.delenv(...)` calls
that the new `_clean_startup_env` autouse fixture already covers (keep any test-specific
`monkeypatch.setenv(...)` calls that intentionally override the clean state, e.g.
`test_build_startup_oops_resources_from_env`). Tests using a *different* template body (e.g.
`test_build_startup_contains_template_body`, `test_build_startup_ssh_paste_replaces_cd_root`)
should keep their own local `tpl`/`tpl.write_text(...)` since they need non-default content — do
not force those onto the shared fixture.

---

### Fix 12 — Add tests for `load_host`, `host_dir_for`, and `cloud_dir_for`

**File:** `tests/test_cli_host.py` — add new test functions (import `load_host`, `host_dir_for`,
`cloud_dir_for` from `metadata_tools.cli._host` at the top of the file alongside the existing
private imports):

```python
def test_load_host_returns_host_dir_and_strips_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_host removes HOST_ID from sys.argv and returns the host directory."""
    monkeypatch.setattr(sys, 'argv', ['cmd', 'GO_0xxx', 'arg1'])
    host_dir = _host_mod.load_host('GO_0xxx')
    assert host_dir.name == 'GO_0xxx'
    assert host_dir.is_dir()
    assert sys.argv == ['cmd', 'arg1']


def test_load_host_exits_for_unknown_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_host calls sys.exit when the host directory does not exist."""
    monkeypatch.setattr(sys, 'argv', ['cmd', 'NONEXISTENT_HOST', 'arg1'])
    with pytest.raises(SystemExit, match='Unknown host'):
        _host_mod.load_host('NONEXISTENT_HOST')


def test_host_dir_for_does_not_mutate_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'argv', ['cmd', 'GO_0xxx'])
    result = _host_mod.host_dir_for('GO_0xxx')
    assert result.name == 'GO_0xxx'
    assert sys.argv == ['cmd', 'GO_0xxx']  # unchanged


def test_cloud_dir_for_resolves_under_cloud_tree() -> None:
    result = _host_mod.cloud_dir_for('GO_0xxx')
    assert result.name == 'GO_0xxx'
    assert result.parent.name == 'cloud'
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

Also add a test for `create_cumulative_indexes`'s explicit `volumes=` parameter (Finding 2.9):

```python
def test_create_cumulative_indexes_explicit_volumes_overrides_args(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path, silent_logger: None) -> None:
    """The explicit `volumes` parameter overrides args.volumes per the docstring."""
    calls: list[Any] = []
    monkeypatch.setattr(cum, '_cat_rows', lambda *a, **k: calls.append(k.get('volumes')))
    args = types.SimpleNamespace(output_dir=str(tmp_path / 'GO_0xxx' / 'GO_0999'),
                                 volumes=['GO_0999_IGNORED'], exclude=None)
    cum.create_cumulative_indexes('GO_0xxx_supplemental_index',
                                  volumes=['GO_0001'], args=args)  # type: ignore[arg-type]
    assert all(v == ['GO_0001'] for v in calls)
```

---

### Fix 14 — Add exact-call-set assertion to `test_create_cumulative_indexes_fires_eight_cat_rows`

**File:** `tests/test_cumulative_support.py`, lines 111–123.

```python
    assert set(calls) == {
        ('SkyTable', 'summary'),
        ('SkyTable', 'detailed'),
        ('BodyTable', 'summary'),
        ('BodyTable', 'detailed'),
        ('RingTable', 'summary'),
        ('RingTable', 'detailed'),
        ('InventoryTable', None),
        ('IndexTable', 'index'),
    }
```
(Run the test first to confirm the exact tuple set produced by the current code before
hard-coding it — the lambda already records `(type(a[4]).__name__, a[4].level)`.)

---

### Fix 15 — Run coverage and confirm the module-level gaps

After applying the fixes above, run:
```bash
pytest tests/ --cov=src --cov-report=term-missing -n auto
```
Coverage is already at 93.02% (well above the 90% gate), so this fix is about closing the specific
gaps below, not raising the aggregate number:
- `columns/body.py` (60% — lowest-covered non-excluded module): add a `tests/columns/test_body.py`
  using the same standalone-loading pattern as `ring_module`/`sky_module`/`sun_module` in
  `tests/columns/conftest.py`, OR determine whether `body.py`'s remaining logic genuinely requires
  a live SPICE body registry (in which case document why it can only be covered by the
  `integration`-marked tests, and note that explicitly with a `# pragma: no cover` at the
  SPICE-only call sites per the `pyproject.toml:139-149` convention, not a blanket file omit).
- `index_support/process.py` (82%) and `geometry_support/prep.py` (87%): run
  `pytest --cov=src --cov-report=term-missing` and add targeted tests for the specific
  uncovered line ranges shown in the `Missing` column.

Do not modify `src/` production code merely to raise coverage; only add tests, except where Fix 1
or Fix 6 (option 1) explicitly call for a `src/` change.

---

### Fix 16 — Add tests for the `.env` `$VAR`-expansion loader (Finding 2.6)

**File:** create `tests/test_init_env_loading.py` (new file — the logic lives in
`src/metadata_tools/__init__.py`, which is otherwise untested).

This is import-time module code, so it must be tested via `importlib.reload` with a monkeypatched
`.env` path, since `metadata_tools` is already imported by the time any test runs. Use a
subprocess-based test to get a truly fresh interpreter, OR use `importlib.reload` with careful
env-var cleanup. A subprocess approach is simplest and most reliable here:

```python
################################################################################
# tests/test_init_env_loading.py: the $VAR-expanding .env loader in __init__.py.
################################################################################
import subprocess
import sys
from pathlib import Path


def _run_with_env_file(tmp_path: Path, env_file_content: str, extra_env: dict[str, str],
                        probe_var: str) -> str:
    """Run a subprocess that imports metadata_tools with a temp .env file and prints probe_var."""
    repo_root = Path(__file__).resolve().parents[1]
    env_file = tmp_path / '.env'
    env_file.write_text(env_file_content, encoding='utf-8')
    # metadata_tools/__init__.py resolves .env as Path(__file__).parent.parent.parent / '.env',
    # i.e. three levels above src/metadata_tools/__init__.py -- the repo root in an editable
    # install. We can't easily relocate the package, so instead we copy the probe into a
    # subprocess whose cwd/env we control and rely on the real repo-root .env being absent
    # or by temporarily writing to the real location and restoring it. Simpler: monkeypatch
    # the _env_file computation isn't possible from outside, so drive this test by writing to
    # (and restoring) the real repo-root .env file directly.
    raise NotImplementedError  # replaced below with the real-file approach


def test_env_var_expands_against_earlier_line_same_file(tmp_path: Path, monkeypatch) -> None:
    """A later .env line's $VAR reference resolves against an earlier line in the same file."""
    import importlib
    import os

    repo_root = Path(__file__).resolve().parents[1]
    real_env_file = repo_root / '.env'
    backup = real_env_file.read_text(encoding='utf-8') if real_env_file.is_file() else None
    try:
        real_env_file.write_text(
            'RMS_TEST_BASE=/tmp/base\nRMS_TEST_DERIVED=$RMS_TEST_BASE/sub\n', encoding='utf-8')
        monkeypatch.delenv('RMS_TEST_BASE', raising=False)
        monkeypatch.delenv('RMS_TEST_DERIVED', raising=False)
        import metadata_tools
        importlib.reload(metadata_tools)
        assert os.environ['RMS_TEST_BASE'] == '/tmp/base'
        assert os.environ['RMS_TEST_DERIVED'] == '/tmp/base/sub'
    finally:
        if backup is None:
            real_env_file.unlink(missing_ok=True)
        else:
            real_env_file.write_text(backup, encoding='utf-8')
        os.environ.pop('RMS_TEST_BASE', None)
        os.environ.pop('RMS_TEST_DERIVED', None)


def test_env_var_does_not_override_existing_os_environ(monkeypatch) -> None:
    """setdefault semantics: an already-set env var is not clobbered by .env."""
    import importlib
    import os

    repo_root = Path(__file__).resolve().parents[1]
    real_env_file = repo_root / '.env'
    backup = real_env_file.read_text(encoding='utf-8') if real_env_file.is_file() else None
    monkeypatch.setenv('RMS_TEST_PRESET', 'from-shell')
    try:
        real_env_file.write_text('RMS_TEST_PRESET=from-dotenv\n', encoding='utf-8')
        import metadata_tools
        importlib.reload(metadata_tools)
        assert os.environ['RMS_TEST_PRESET'] == 'from-shell'
    finally:
        if backup is None:
            real_env_file.unlink(missing_ok=True)
        else:
            real_env_file.write_text(backup, encoding='utf-8')
        os.environ.pop('RMS_TEST_PRESET', None)
```

Delete the unused `_run_with_env_file` helper stub above before committing — it was left in this
prompt only to show the rejected approach; write the two tests directly. Because this test
mutates a real repo-root file (there is no way to inject a fake `.env` path into already-written
production code without a `src/` change), mark it clearly and keep the try/finally restoration
strict. If you would rather avoid touching the real `.env` file even transiently, propose (but do
not silently make) a minimal `src/` change: extract the `.env`-parsing loop in
`src/metadata_tools/__init__.py:26-37` into a small testable pure function (e.g. `_parse_env_file(text:
str) -> dict[str, str]`) that returns the parsed mapping without touching `os.environ`, called from
the module-level block — that would let the parsing logic be unit-tested without subprocess/reload
tricks, while the thin `os.environ.setdefault` loop remains (and stays untested, but is now
trivial). If you make this change, flag it to the user rather than doing it silently, since it is
a `src/` change outside pure test-file edits.

---

### Fix 17 — Add tests for `defs.set_translations()` and the `Record.__init__` translation branch

**File:** `tests/test_geometry_constructors.py` — add:

```python
def test_set_translations_applies_at_record_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """A raw target name present in the translation table is rewritten in Record.__init__."""
    import metadata_tools.defs as defs
    _patch_record_spice(monkeypatch, primary='')
    monkeypatch.setattr(defs, '_translations', {'RAW_NAME': 'JUPITER'})
    record = Record(_observation(target='RAW_NAME'), 'GO_0001', {}, 8, 'summary')
    assert record.target == 'JUPITER'


def test_set_translations_leaves_unmapped_target_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    import metadata_tools.defs as defs
    _patch_record_spice(monkeypatch, primary='')
    monkeypatch.setattr(defs, '_translations', {'OTHER': 'SATURN'})
    record = Record(_observation(target='SKY'), 'GO_0001', {}, 8, 'summary')
    assert record.target == 'SKY'
```

Also add a direct unit test for the accessor itself in `tests/test_config.py` or a new
`tests/test_defs.py`:

```python
################################################################################
# tests/test_defs.py: Tests for metadata_tools.defs.set_translations.
################################################################################
import metadata_tools.defs as defs


def test_set_translations_replaces_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    defs.set_translations({'A': 'B'})
    assert defs._translations == {'A': 'B'}
    defs.set_translations({})  # reset so other tests are unaffected
    assert defs._translations == {}
```

Note: `defs._translations` is module-level global state, not monkeypatch-scoped by `set_translations`
itself — prefer `monkeypatch.setattr(defs, '_translations', {...})` in tests that need isolation
(as in the `Record.__init__` tests above), and only call `set_translations()` directly in a test
that explicitly resets the table afterward, to avoid leaking state into other tests under
`pytest-randomly`/`pytest-xdist`.

---

### Fix 18 — Add direct unit tests for `tests/archive_support.py` helpers (Finding 14.5)

**File:** create `tests/test_archive_support.py` (new file):

```python
################################################################################
# tests/test_archive_support.py: Direct unit tests for match/exclude/bounds.
################################################################################
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import tests.archive_support as support


def test_match_finds_files_by_glob(tmp_path: Path) -> None:
    (tmp_path / 'a_summary.lbl').write_text('x', encoding='utf-8')
    (tmp_path / 'b_other.lbl').write_text('x', encoding='utf-8')
    result = support.match(str(tmp_path), '*_summary.lbl')
    assert len(result) == 1
    assert result[0].endswith('a_summary.lbl')


def test_match_walks_subdirectories(tmp_path: Path) -> None:
    sub = tmp_path / 'GO_0001'
    sub.mkdir()
    (sub / 'x_summary.lbl').write_text('x', encoding='utf-8')
    result = support.match(str(tmp_path), '*_summary.lbl')
    assert len(result) == 1


def test_exclude_removes_matching_patterns() -> None:
    files = ['/a/templates/x.lbl', '/a/old/y.lbl', '/a/z.lbl']
    assert support.exclude(files, 'templates/', 'old/') == ['/a/z.lbl']


def test_exclude_keeps_non_matching_files() -> None:
    files = ['/a/b.lbl', '/a/c.lbl']
    assert support.exclude(files, 'nomatch/') == files


class _FakeColumnInfo:
    def __init__(self, invalid_values: set[Any]) -> None:
        self.invalid_values = invalid_values


class _FakeTable:
    def __init__(self, values: dict[str, Any], invalid: dict[str, set[Any]]) -> None:
        self.column_values = values
        self.info = type('Info', (), {
            'column_info_dict': {k: _FakeColumnInfo(v) for k, v in invalid.items()}})()


def test_bounds_passes_within_range() -> None:
    table = _FakeTable(
        {'MINIMUM_PHASE_ANGLE': np.array([10.0, 20.0]),
         'MAXIMUM_PHASE_ANGLE': np.array([15.0, 25.0])},
        {'MINIMUM_PHASE_ANGLE': set(), 'MAXIMUM_PHASE_ANGLE': set()})
    support.bounds('file.lbl', table, 'PHASE_ANGLE', min_val=0, max_val=180)  # no assertion error


def test_bounds_raises_outside_range() -> None:
    table = _FakeTable(
        {'MINIMUM_PHASE_ANGLE': np.array([-5.0]), 'MAXIMUM_PHASE_ANGLE': np.array([15.0])},
        {'MINIMUM_PHASE_ANGLE': set(), 'MAXIMUM_PHASE_ANGLE': set()})
    with pytest.raises(AssertionError):
        support.bounds('file.lbl', table, 'PHASE_ANGLE', min_val=0, max_val=180)


def test_bounds_ignores_null_value() -> None:
    table = _FakeTable(
        {'MINIMUM_X': np.array([-999.0, 10.0]), 'MAXIMUM_X': np.array([-999.0, 20.0])},
        {'MINIMUM_X': {-999.0}, 'MAXIMUM_X': {-999.0}})
    support.bounds('file.lbl', table, 'X', min_val=0, max_val=180)  # -999 excluded, no error
```

Adjust the `_FakeTable`/`_FakeColumnInfo` stand-ins if `pdstable.PdsTable`'s real
`info.column_info_dict[key].invalid_values` shape differs from what is assumed here — check
`support.bounds` (`tests/archive_support.py:56-89`) against the real `pdstable` API before
finalizing field names.

---

### Final verification

After applying all fixes:
```bash
pytest tests/ --cov=src --cov-report=term-missing -n auto
mypy tests
ruff check tests
```
Confirm: `0 failed`, coverage still `>= 90%`, no new mypy or ruff violations.
