# Final report — structural refactor + hermetic test suite

**Date:** 2026-06-15
**Branch:** `ai_rewrite`
**Scope:** Implementation of `plans/plan1_split_geometry_support.md` and
`plans/plan2_test_suite.md`.

This report records (a) the structural work done and (b) every code problem the
work surfaced. **No production behavior was changed** — the splits are mechanical
and output-preserving, and every bug below is pinned by a test (a strict `xfail`
where the test asserts the *intended* behavior, or a passing characterization
test where it documents the *current* behavior). Fixes are deliberately left for
a separate change so the refactor stays reviewable.

---

## 1. What was done

### 1.1 `geometry_support.py` split into a package

| Before | Lines | After |
|---|---:|---|
| `geometry_support.py` | 1654 | `geometry_support/` package: `formats` `masks` `formatting` `prep` `bodies_select` `record` `tables` `suite` `process` `__init__` (≤ 298 each) |

The public import surface is unchanged: `import metadata_tools.geometry_support
as geom` exposes exactly the same names it did before (re-exported from the
package `__init__`). The five state-light geometry helpers became module-level
free functions — the reason they are now directly unit-testable without a
SPICE-backed object.

### 1.2 Hermetic test suite (`pytest` default run, no SPICE, no holdings)

`tests/conftest.py` installs a tested import shim (fake `metadata_tools.bodies`
with a name→object `BODIES`, and stub `host_config`/`index_config`/
`geometry_config`) so every engine module imports without kernels or the host
CWD. 16 new test modules exercise the library directly.

**Coverage: 93.10%** (`fail_under = 90`), measured over the host-agnostic engine.
Per `plan2 §5`, the coverage denominator excludes code that cannot run
hermetically, via documented `omit` entries in `pyproject.toml`:

- `*/metadata_tools/hosts/*` — per-host plugin config, runnable entry scripts,
  `*_cloud.py` GCP workers, and host-local tests (import host modules top-level
  and drive oops/SPICE or rms-cloud-tasks).
- `*/metadata_tools/bodies.py` — builds the oops Body registry via
  `oops.Body.lookup()`, which needs kernels (the engine tests stub it).

No blanket `# pragma: no cover` was used; SPICE-bound constructors
(`Record.__init__`, `Suite.__init__`, `bodies_select.inventory`/`select_bodies`)
are covered by heavy monkeypatching instead.

---

## 2. Confirmed bugs — pinned by strict `xfail` tests (fail on current code)

These four tests assert the **intended** behavior and fail today; flip each to a
passing test in the same commit that fixes the bug.

1. **`util.add_by_base` drops a chained carry** — *correctness, High.*
   When `carry_in + (x+y) % base == base`, the digit is left equal to `base` and
   the carry is not propagated. `add_by_base([9,9],[0,1],[10,10])` returns
   `[0,10,0]`; correct is `[1,0,0]`. Feeds
   `host_config._spacecraft_clock_stop_count_from_label`, so a stop SCLK can be
   malformed at a tick boundary.
   *Test:* `test_util_math.py::test_add_by_base_propagates_chained_carry`.

2. **`util.append_txt_file` duplicates content on first write** — *correctness, Medium.*
   The "no file → `write_txt_file`" shortcut lacks a `return`, so it falls
   through and appends the same content again. A new file written with
   `['lineA','lineB']` ends up containing both lines twice.
   *Test:* `test_util_textfile.py::test_append_to_new_file_writes_content_once`.

3. **`IndexTable._get_null_value` returns the last, not the first, null
   keyword** — *correctness, High.* The priority loop uses `continue` where it
   means `break`, so the result is the lookup of the **lowest-priority** keyword
   present. A column with only `NULL_CONSTANT` set returns `None`.
   *Test:* `test_index_support.py::test_get_null_value_prefers_highest_priority_key`
   (and a passing companion `…returns_last_present_key` documenting today's value).

4. **`bodies_select.obs_excluded` short-circuits on the first identifier
   exception** — *correctness, Medium.* It `return`s the first config-function
   exception's bool immediately, so a later regex exception is never evaluated.
   `['always_false_fn', '.*CAL']` against an id matching `.*CAL` yields `False`
   instead of `True`.
   *Test:* `test_geometry_record.py::test_obs_excluded_identifier_then_regex`.

---

## 3. Bugs / smells documented by passing characterization tests

These tests pass — they pin the **current** (often wrong) behavior so the Plan 1
refactor is fenced and the defects are recorded.

5. **`prep_row` builds the label `override` from the last column only, and
   reuses `target`** — *correctness, Medium.* The `override`
   (NULL_VALUE/VALID_MINIMUM/MAXIMUM) is assembled after the per-column loop from
   whatever survived the final iteration, and the `target` parameter is
   overwritten by `event_key[1]` mid-loop.
   *Test:* `test_geometry_prep.py::test_override_reflects_last_column_only`
   (asserts the saved override carries the *last* column's range).

6. **`prep_row` multiple-tile-set (`tiles` is a tuple) path raises `TypeError`**
   — *correctness, Medium; newly identified.* The recursive call passes
   `primary/target/name_length/…` positionally, but those parameters are
   keyword-only (after `*`), so the call always raises. The detailed multi-tile
   path is therefore dead. This predates the package split (the original method
   had the same shape).
   *Test:* `test_geometry_prep.py::test_multiple_tile_sets_tuple_raises_typeerror`.

7. **`masks.construct_excluded_mask` dead branch + mixed return type** —
   *robustness, Medium.* `if np.any(excluded): return excluded` precedes the
   unreachable `if np.all(excluded): return True`; the function returns a numpy
   array in some paths and a Python `bool` in others, and the `#!!!!` comment
   admits gridless backplanes are unhandled.
   *Tests:* `test_geometry_masks.py::test_day_face_masks_antisunward` (all-True
   returns the array, documenting the unreachable `True`),
   `…::test_all_false_returns_python_false`, `…::test_nonexistent_target_returns_true`.

8. **`Record.get_backplane_key` docstring is wrong** — *doc, Low.* Docstring
   says `Returns: None`; it returns the backplane key.
   *Test:* `test_geometry_record.py::test_get_backplane_key_*`.

9. **`util.sclk_format_count` return-type mismatch** — *doc, Low.* Docstring
   says `Returns: int`; it returns a delimited string.
   *Test:* `test_util_math.py::test_sclk_format_count_returns_str_not_int`.

10. **`util._get_range_mod360` raises `IndexError` on empty input** — *robustness,
    Low.* `values[0]` is accessed unconditionally; the docstring makes no promise
    about empty input.
    *Test:* `test_util_range_mod360.py::test_range_empty_raises_indexerror`.

---

## 4. Bugs identified but not yet test-asserted (still latent)

11. **`index_support._create_index` accumulator/scope bug** — *correctness, High.*
    `unused = None` is reset **inside** the per-directory `walk` loop, and
    `logger.close(force=True)` + the task-file write + the unused-columns warning
    all run inside the loop rather than once after it. So the cross-volume
    "unused columns" intersection never accumulates and the log/task file are
    rewritten per directory. The new walk tests
    (`test_index_support.py::test_create_index_*`) exercise the loop for coverage
    but do **not** assert the intended single-close/intersection — fixing this
    needs a dedicated recording test alongside the fix.

12. **`index_support._index_one_value` dead `assert` / `-O` fragility** —
    *robustness, Low.* `assert value is not None` can never fire (the preceding
    line already substituted `nullval`) and is stripped under `python -O`. The
    null substitution, not the assert, enforces the invariant.

13. **`util.replace` uses `eval()` on column-derived strings** — *security/robustness,
    High* (carried from `code_critique.md §7`; unchanged here). Reachable from the
    `BODYX` dictionary-reference placeholders in `columns/*.py`.

14. **Misplaced class docstrings in `geometry_support/tables.py`** —
    *maintainability, Low.* The `"""…"""` strings sit **before** each `class`
    statement (a no-op expression), so `InventoryTable`/`SkyTable`/`SunTable`/
    `RingTable`/`BodyTable` have no docstring. Moved verbatim from the original
    file to preserve byte-for-byte behavior.

---

## 5. Pre-existing issues unchanged by this work

Carried over from `code_critique.md` and not in scope here: pervasive builtin
shadowing (`format`, `id`, `type`, …) and the remaining ruff findings (the engine
is not ruff-clean repo-wide); the library is still largely unannotated so
`mypy --strict` does not pass repo-wide; `common.Table.write` still ships a
`util.dbprint` debug line; the two `GO_0xxx_geometry.py` entry points diverge from
the cloud worker; `*_cloud.py` reach into the private `worker._data`.

---

## 6. How to act on this

1. Fix items 1–4 (strict `xfail`): each fix flips its test from `xfail` to pass.
2. Fix items 5–7, 11 and update their characterization tests to assert the
   corrected behavior.
3. Items 8–10, 12, 14 are doc/robustness cleanups; 13 is the standing `eval()`
   security item tracked in `code_critique.md §7`.
