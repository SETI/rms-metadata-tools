# Plan 2 — Hermetic test suite to ≥90% coverage (no holdings, no SPICE)

**Goal:** Build a unit-test layer that imports and exercises the `metadata_tools` library
directly, runs with **no `$RMS_METADATA`/`$RMS_VOLUMES` and no SPICE kernels**, and pushes
`pytest --cov=src` to **≥90%** — the target `pyproject.toml` already declares (`fail_under = 90`)
but the current suite does not meet (it only re-parses pre-generated archive files; coverage of
`src` is ~0%).

**Method discipline (per the user's instruction):** Tests are derived from each function's
**docstring + name + call-sites**, not from re-reading the implementation. Where the docstring
is insufficient, the code is consulted only to learn shape. Crucially, tests assert the
**intended** behavior; where the implementation contradicts the docstring/name, the test is
written to the intent and is **expected to fail**, flagging a bug. No production code is changed.

---

## 1. The keystone: a hermetic import shim (proven to work)

Three things block importing the support modules without SPICE; all three are solved in one
`tests/conftest.py` that runs **before collection** (import time):

| Blocker | Why | Fix |
|---|---|---|
| `metadata_tools.bodies` runs `oops.Body.lookup('MERCURY')` at import | needs SPICE body registry | inject a fake `metadata_tools.bodies` module with `BODIES = {name: object()}` for all body names **before** anything imports `metadata_tools.columns` |
| `index_support`/`cumulative_support` do `import host_config`, `import index_config` (top-level) | only resolve when CWD is the host dir | inject stub `host_config`, `index_config` modules into `sys.modules` |
| `geometry_support` does `import geometry_config` and runs `MISSION_TABLE = convert_mission_table(config.MISSION_TABLE, config.SC)` at import (cspyce SCLK) | needs kernels | inject stub `geometry_config` with `MISSION_TABLE = []`, `SC = -77` so the conversion is a no-op |

**Verified working** (probe run during planning):

```python
# tests/conftest.py  (sketch — runs at import, before test collection)
import sys, types

def _install_fakes() -> None:
    body_names = ['MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE',
                  'PLUTO','IO','EUROPA','GANYMEDE','CALLISTO','METIS','ADRASTEA','AMALTHEA',
                  'THEBE','MOON']
    fb = types.ModuleType('metadata_tools.bodies')
    fb.BODIES = {n: object() for n in body_names}
    fb.get_bodies = lambda names: {n: object() for n in names}
    sys.modules.setdefault('metadata_tools.bodies', fb)

    for name, attrs in [
        ('host_config',     {'get_volume_id': lambda p: 'GO_0001',
                             'SCLK_BASES': [16777215, 91, 10, 8],
                             'template_name': 'GO_0xxx_supplemental_index'}),
        ('index_config',    {'glob': 'C0*.LBL'}),
        ('geometry_config', {'MISSION_TABLE': [], 'SC': -77, 'EXPAND': 0.00015,
                             'target_name': lambda d: d.get('TARGET_NAME', 'SKY'),
                             'cleanup': lambda: None}),
    ]:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules.setdefault(name, m)

_install_fakes()
```

Probe confirmed: with these fakes, `import metadata_tools.columns`, `index_support`,
`geometry_support`, `cumulative_support` all import cleanly, `FORMAT_DICT` has 52 entries, and
real `polymath`/`oops.Scalar` math (used by `formatted_column`) works without kernels.

> Note for sequencing: this shim becomes simpler after Plan 1, but it is **not blocked by
> Plan 1** — it works against today's single-file `geometry_support.py` too. The two plans are
> independent; do Plan 2 first if you want the behavior fence before refactoring.

Stubs use `setdefault` so a real host environment (if ever present) is not clobbered. The
existing `tests/columns/conftest.py` (file-level `importlib` loading) stays as-is; the new
top-level conftest covers the support modules.

---

## 2. Markers, config, hermeticity guards (`pyproject.toml`)

- Keep the `integration` marker; **add** `requires_archive`. Mark every existing archive-reading
  test (`tests/test_index.py`, `tests/test_geometry.py`) `requires_archive` and exclude by
  default (`addopts += -m "not integration and not requires_archive"`). The unit layer then runs
  fast and hermetic; the archive tests remain runnable on demand.
- `tests/unittester_support.py` reads `os.environ['RMS_METADATA']` **at import** → make that lazy
  (move into a fixture that `pytest.skip`s when unset) so collection never errors without env.
- Add `filterwarnings = ["error"]` with narrowly-scoped, commented ignores, so the library's
  `warnings.warn` calls (NaN/overflow in `formatted_column`, VICAR in `index_config`) are
  asserted via `pytest.warns`, not silently swallowed.
- Before each archive `for file in files:` loop, assert `len(files) > 0` (or skip) so a no-data
  run cannot pass vacuously.

---

## 3. Test architecture

```
tests/
├── conftest.py                  # the import shim (§1) + shared fixtures
├── test_util_math.py            # add_by_base, rebase, sclk_*, get_volume_glob, parse_template_name, pm/smooth
├── test_util_range_mod360.py    # _get_range_mod360 + _ninety_percent_gap_degrees (parametrized branches)
├── test_util_textfile.py        # read/write/append_txt_file, expandvars, splitpath, get_volume_subdir
├── test_util_names.py           # get_index_name, get_template_name, select_dir, replacement_fn
├── test_index_support.py        # _format_value/_format_parms/_format_column/_get_null_value/
│                                #   _get_column_values/_index_one_value + key__* + _create_index
├── test_geometry_formatting.py  # formatted_column, circle_coverage (real polymath Scalars)
├── test_geometry_masks.py       # construct_excluded_mask (fake Backplane)
├── test_geometry_record.py      # get_backplane_key, get_key_map, postprocess/link_null, _get_primary, _obs_excluded
├── test_geometry_prep.py        # prep_row tiling/subregion logic (fake Backplane)
├── test_geometry_tables.py      # InventoryTable/Sky/Sun/Ring/BodyTable.add (fake Record), Suite helpers
├── test_common.py               # Table, PathAction, get_common_args, task_list, init_logger, write_task_file
├── test_label_support.py        # label_support.create early-return + template-path derivation
├── test_cumulative_support.py   # _cat_rows walk + create_cumulative_indexes (fake tree, mocked tables)
└── test_config_keys.py          # host_config/index_config key__* (mock julian/vicar where needed)
```

### Shared fixtures (conftest.py)

- `fake_backplane`: a stand-in exposing `.shape`, `.evaluate(key)`, `.where_in_back`,
  `.where_inside_shadow`, `.where_antisunward`, `.where_sunward`, returning `oops.Scalar`/boolean
  arrays of a fixed small shape (e.g. 4×4). Lets `construct_excluded_mask` and `prep_row` run
  without SPICE.
- `make_scalar`: helper to build masked/partly-masked `oops.Scalar`s for formatting tests.
- `tmp_volume_tree`: builds a tiny on-disk `GO_0xxx/GO_0001/...` tree of `.tab`/`.lbl` stubs
  under `tmp_path` for the walk-based functions (`_create_index`, `_cat_rows`,
  `process_tables`), exercised with `FCPath` so no remote access occurs.
- `record_stub`: a `Record` built via `Record.__new__` with only the attributes a given method
  reads (`sampling`, `dicts`, `backplane_keys`, `prefixes`, `inventory`, `bodies`, `primary`,
  `level`) so table/record methods can be tested without `__init__`'s SPICE path.

---

## 4. Coverage map — what each test targets

Legend: **[BUG]** = test asserts intended behavior and is **expected to fail** on current code
(see §6); **[char]** = characterization test pinning current behavior (for the Plan 1 refactor
fence); plain = straightforward correctness test.

### `util.py`  (highest single-file coverage win; pure, fully hermetic)

- `add_by_base` — **[BUG]** carry not propagated when `carry_in + (digit_sum % base) == base`.
  Tests: `add_by_base([9,9],[0,1],[10,10]) == [1,0,0]` (currently `[0,10,0]`); plus simple
  no-carry, single-carry, and SCLK-base cases that pass.
- `rebase` — `rebase(123,[10,10,10]) == ([1,2,3], 0)`; overflow case returns nonzero remainder;
  `ceil=True` rounds a fractional tick up. Cross-check `add_by_base`∘`rebase` round-trip on a
  known exposure value.
- `sclk_split_count` — default-delimiter parsing, zero-padding to 4 fields, custom `delim`.
- `sclk_format_count` — **[doc]** docstring says `Returns: int` but it returns a **str**; assert
  exact zero-padded string (`'00012345:01:2:3'`), and that round-trip
  `format(split(x)) == normalized(x)`.
- `get_volume_glob` — `'GO_0xxx' -> 'GO_0[0-9][0-9][0-9]'`.
- `parse_template_name` — `'GO_0xxx_supplemental_index' -> ('GO_0xxx','supplemental', <dir>)`;
  host-with-underscores preserved.
- `_get_range_mod360` (in `test_util_range_mod360.py`) — parametrized over its branches:
  single value `[v,v]`; wrap-around arc `[350,355,5,10] -> [350.,10.]`; full-coverage via
  `diffmin`; 90%-confidence gap accept/reject around `_ninety_percent_gap_degrees(n)`;
  `alt_format='-180'` mapping. **[edge]** empty input raises `IndexError` — assert the current
  behavior and flag that the docstring doesn't promise it.
- `_ninety_percent_gap_degrees` — table lookup `n<1000` vs the `n>=1000` power-law branch; `scale`.
- `append_txt_file` — **[BUG]** writing a *new* file duplicates content (no `return` after the
  `write_txt_file` shortcut): probe showed `['lineA','lineB']` → `lineA\nlineB\nlineA\nlineB\n`.
  Test asserts each line appears **once** on first write; appends-to-existing add exactly once.
- `read_txt_file`/`write_txt_file` — round-trip with `\r\n` and `\n` terminators; `as_string`.
- `expandvars` — `$VAR` expansion preserves `gs://` scheme and the input type (str/FCPath/Path).
- `splitpath` / `get_volume_subdir` / `select_dir` / `get_index_name` / `get_template_name` —
  exact path arithmetic on `FCPath` inputs.
- `convert_mission_table` — monkeypatch `util.sclk_to_ticks`; assert the phase-label column
  (`item[0]`) is dropped and rows become `((t0,t1), excs, primary, secondaries, selections,
  additions)` consumed positionally by `get_primary`.
- `pm`, `smooth` — trivial numeric asserts (cheap coverage).

### `index_support.py`

- `_format_value` — `'A'` format quotes + left-justifies (`'IO' / 'A10' -> '"IO        "'`);
  numeric `F`/`E`/`I` formats produce expected width.
- `_format_parms` — width and `data_type` for `A/E/F/I`; the `'0'`-vs-`0` `TypeError` fallback.
- `_format_column` — multi-item (`ITEMS`) expansion and comma-join; whitespace/quote scrubbing
  of strings; invalid-format path logs a warning and returns `width*'*'` (assert via `caplog`).
- `_get_null_value` — **[BUG]** returns the **last** null-keyword lookup instead of the
  **first/highest-priority** one (`continue` should be `break`): probe showed a column with only
  `NULL_CONSTANT` set returns `None`. Test: highest-priority key present, lower ones empty →
  expect that value; currently fails.
- `_get_column_values` — iterates columns until `IndexError`; builds stub dicts with
  `NAME/FORMAT/ITEMS/NULL_CONSTANT` (fake `pds3_table`).
- `_index_one_value` — dispatch order: built-in `key__*` → `config.key__*` → raw label value →
  `nullval`; `None` from a key function becomes `nullval`; usage flag set only for non-null.
  **[BUG-adjacent]** the `assert value is not None` at line 232 is dead (line 229 already
  replaced `None`) and disabled under `-O` — test documents that the null substitution, not the
  assert, is what guarantees non-null.
- `key__volume_id`, `key__file_specification_name` — via the `host_config` stub.
- `_create_index` — **[BUG]** with a `tmp_volume_tree` and a monkeypatched `IndexTable`: the
  `unused` accumulator is reset inside the walk loop and `logger.close`/task-file write happen
  per-directory rather than once. Test asserts cross-volume `unused` intersection and a single
  close; expected to fail. (Heaviest unit test; uses the fake tree + a recording stub.)

### `geometry_support.py` (function targets named as in Plan 1; pre-split they are `Record`
methods, post-split they are free functions — tests adapt the call but assert the same thing)

- `formatted_column` — real `oops.Scalar`s: 2-value `DEG` (`[0.5,1.0] rad -> '  28.648,  57.296'`,
  verified); single-value (`number_of_values==1`) masked → `null_value`; fully-masked 2-value →
  `[null,null]`; `'360'`/`'-180'` route through `circle_coverage`; `ISO` route via
  `julian.iso_from_tai`; **[warn]** NaN and ±inf inputs emit the documented warnings and
  substitute `null_value` (assert with `pytest.warns`); overflow clipping to `overflow_format`.
- `circle_coverage` — masked Scalar → `[null,null]`; unmasked passes through `_get_range_mod360`
  with `width=sampling+1`.
- `construct_excluded_mask` — fake Backplane: `'P'` masker ORs `where_in_back(target,primary)`;
  `'R'`+`primary=='SATURN'` adds rings; `'M'`+blocker adds blocker; `target==blocker` disables
  self-blocking; `ignore_shadows=True` skips shadower/face; non-existent target → returns `True`.
  **[BUG]** the trailing `if np.any: return excluded` precedes the unreachable
  `if np.all: return True`; assert that an all-True mask returns the **array** (not scalar `True`)
  and document the dead branch + the gridless-`#!!!!` TODO.
- `get_backplane_key` — **[doc]** docstring says `Returns: None`; actually returns the key
  (`('phase_angle','X') tuple -> 'phase_angle'`, verified). Assert the real contract.
- `get_key_map` — caches `backplane_keys` per qualifier; slices the last `ndata` columns; handles
  the `dict`-of-named-column-lists case (`column_descs[next(iter(...))]`).
- `postprocess` / `link_null` — build a record stub with `dicts`/`backplane_keys` covering
  `center_coordinate` (the only `link_id` column); a null in one linked column propagates to all
  linked columns. **[fragility]** note `links` is keyed by link-function name, so two distinct
  backplane keys sharing a link would collide (only one survives) — add a test that documents
  this if a second linked column is ever introduced.
- `get_primary` — converted-table lookup by SCLK ticks (monkeypatch `sclk_to_ticks`); in-range
  row returns `(primary,secondaries,selections,additions)`; no match → `('',[],[],[])`; an
  excluded observation short-circuits to the fail tuple.
- `obs_excluded` — **[BUG]** for an exceptions list mixing an identifier (config function) and a
  regex, the function `return`s the **first** identifier function's bool immediately, never
  checking later regex entries. Test: `['always_false_fn', '.*CAL']` against an ID matching
  `.*CAL` → intended `True`, current `False`. Also: empty exceptions → `False`; regex match → `True`.
- `prep_row` — fake Backplane producing small boolean tiles: summary path writes exactly one row;
  detailed path with a tuple of tiles writes one row per non-empty subregion; `tiling_min`
  suppression collapses to summary; `allow_zero_rows=False` forces a null row. **[BUG]** the
  `override` dict is built from whatever `null_value/valid_minimum/valid_maximum` survived the
  **last** column iteration, and the parameter `target` is overwritten by the per-column
  `event_key[1]`; assert the override reflects the intended per-column value (expected to fail /
  to characterize).
- `append_body_prefix` — name shorter than width is right-padded inside quotes; longer is
  truncated; `None` → blank quoted field of `length` spaces.
- `InventoryTable/SkyTable/SunTable/RingTable/BodyTable.add` (fake `record_stub`) — Inventory
  joins prefixes + quoted inventory list; Sky uses `no_body=True`; Ring only emits when
  `record.primary and record.rings_present`; Body iterates `record.bodies` with `target=name`.
- `Suite.get_override`/`get_overrides` — override dicts per column from `FORMAT_DICT`/
  `ALT_FORMAT_DICT`; `add_tables` builds the expected table set; `make_records` one per level.
  (`Suite.create`/`__init__` full path is SPICE-bound → covered only at the import/`add_tables`
  seam, or marked `integration`.)
- **[BUG]** detailed-path dict selection: the contract test already guards the names; add a
  `Record`-level test (record stub with `level='detailed'`) asserting `dicts['ring'] is
  col.RING_DETAILED_DICT` and `dicts['body'] is col.BODY_DETAILED_DICT` (the fix the critique
  marked resolved — lock it in).

### `common.py`

- `Table.__init__` filename composition (`<vol><suffix>` vs `_<qualifier>_<level>.tab`);
  early-return when `output_dir` is falsy.
- `Table.write` — `labels_only` skips table write; empty `rows` returns early; otherwise calls
  `util.write_txt_file` + `lab.create` (monkeypatch both, assert args). **[smell]** asserts the
  shipped `util.dbprint` debug line is invoked (documents the §2 finding).
- `PathAction` — collapses `//`, preserves `gs://`.
- `get_common_args` — optional arg groups appear/disappear with `volume_arg=None` etc.; parse a
  sample argv.
- `add_task`/`task_source`/`write_task_file` — task dict shape; generator yields appended tasks;
  JSON file content. **[state]** note `task_list` is a module global (parallel-unsafe) — keep
  these tests in one module and reset the global in a fixture.
- `init_logger` — monkeypatch `pdslogger` handlers; assert handler registration and the header
  log (no real file via `FCPath` needed beyond `tmp_path`).

### `label_support.py`

- `create` — non-existent `filepath` returns immediately (assert no template work); volume-id
  slice from filename; `inventory` filenames disable the preprocessor; global-vs-host template
  path derivation (monkeypatch `PdsTemplate` to capture the resolved `template_path`).

### `cumulative_support.py`

- `_cat_rows` — `tmp_volume_tree` with two volumes' `.tab` stubs: concatenation order, `__skip`
  and cumulative-dir exclusion, `exclude`/`volumes` filtering, `.csv` extension for `inventory`,
  the `IndexError`-when-missing skip. Monkeypatch `lab.create`.
- `get_args`/`create_cumulative_indexes` — argparser wiring; the eight `_cat_rows` calls fire
  with the right `(TableClass, level)` (monkeypatch `_cat_rows` to record calls).

### `host_config.py` / `index_config.py` key functions (`test_config_keys.py`)

- `_spacecraft_clock_start_count_from_label` / `_stop_count_from_label` — pure `util` math
  (no SPICE): a known `SPACECRAFT_CLOCK_START_COUNT` + `EXPOSURE_DURATION` produces the expected
  formatted start/stop counts. **This is where the `add_by_base`/`rebase` bug surfaces
  end-to-end** — add a case whose exposure triggers the carry collision and assert the correct
  stop count (expected to fail until the util bug is fixed).
- `key__on_chip_mosaic_flag` — SL9 date-window returns `'Y'`; outside window falls through to the
  label value or `None`. Monkeypatch nothing (uses `julian`, importable).
- `key__compression_quantization_table_id` — present/absent keyword.
- `key__start_time`/`key__stop_time`/`_event_tai` — `'UNK'` passthrough; center-of-exposure
  offset sign. Monkeypatch `julian` only if needed.
- `key__product_creation_time` — **[robustness]** `FileNotFoundError` re-raise drops context
  (ruff B904); VICAR error path emits a `RuntimeWarning` and returns `None`. Mock `vicar`.

---

## 5. Reaching ≥90%

- `util.py` (802 lines, ~half of which is the inert `NINETY_PERCENT_RANGE_DEGREES` table that
  counts as covered on import) and `index_support.py` (623) are the big movers and are almost
  fully hermetic — prioritize them.
- The genuinely SPICE-bound seams (`Suite.create`, `Record.__init__` inventory/backplane build,
  the `*_cloud.py` async `main`, host entry scripts) are excluded from the 90% denominator by
  marking them `integration` and/or adding targeted `# pragma: no cover` only where a line is
  unreachable without kernels — documented, not blanket.
- After Plan 1, the extracted free functions (`formatted_column`, `construct_excluded_mask`,
  `prep_row`, `bodies_select.*`) become directly callable, lifting `geometry_support` coverage
  from "constructor-gated" to "near-complete" — the two plans compound.
- Measure with `pytest -m "not integration and not requires_archive" --cov=src
  --cov-report=term-missing`; iterate on the `term-missing` lines until ≥90%.

---

## 6. FINAL REPORT — code believed incorrect, and how the tests target it

Four bugs were **reproduced during planning** (probe scripts, not assumptions); the rest are
read-from-code suspicions to be pinned by the tests above. None are fixed here.

### Confirmed by execution

1. **`util.add_by_base` drops a carry** — *correctness, High.*
   When `carry_in + (xdigit+ydigit) % base == base`, the digit is left equal to `base` and the
   carry is not propagated. Reproduced: `add_by_base([9,9],[0,1],[10,10])` returns `[0,10,0]`;
   correct is `[1,0,0]`. Feeds `_spacecraft_clock_stop_count_from_label`, so a stop SCLK can be
   malformed for exposures that land on the boundary.
   *Test:* `test_util_math.py::test_add_by_base_propagates_chained_carry` asserts `[1,0,0]`
   (xfail→bug) plus passing no-carry/single-carry cases; `test_config_keys.py` adds an
   end-to-end stop-count case that triggers it.

2. **`util.append_txt_file` duplicates content on first write** — *correctness, Medium.*
   The "no file → `write_txt_file`" shortcut lacks a `return`, so it falls through and appends
   the same content again. Reproduced: a new file written with `['lineA','lineB']` contains
   `lineA\nlineB\nlineA\nlineB\n`.
   *Test:* `test_util_textfile.py::test_append_to_new_file_writes_content_once` asserts one
   occurrence (xfail→bug); a separate append-to-existing test asserts exactly-once growth.

3. **`IndexTable._get_null_value` returns the last, not the first, null keyword** —
   *correctness, High.*
   The priority loop uses `continue` where it means `break`, so `nullval` ends as the lookup of
   the **last** keyword (`NOT_APPLICABLE_CONSTANT`), not the highest-priority present one.
   Reproduced: a column with only `NULL_CONSTANT='-999'` set returns `None`.
   *Test:* `test_index_support.py::test_get_null_value_prefers_highest_priority_key` (fake
   `pds3_table`) asserts `'-999'` (xfail→bug); plus a case where only a lower-priority key is set.

4. **`Record.get_backplane_key` docstring is wrong** — *doc, Low.*
   Docstring `Returns: None`; the function returns the backplane key. Reproduced: returns
   `'phase_angle'`.
   *Test:* `test_geometry_record.py::test_get_backplane_key_returns_key` asserts the real
   contract for both tuple and non-tuple event keys.

### Suspected from docstring/name/call-site review (tests written to intent)

5. **`Record._obs_excluded` short-circuits on the first identifier exception** —
   *correctness, Medium.* Returns `fn(observation)`'s bool immediately, so a `False` from the
   first config-function exception prevents any later regex exception from ever matching.
   Intended (per docstring "True if the observation is excluded" + the table semantics): an
   observation is excluded if **any** exception matches.
   *Test:* mixed `['always_false_fn', '.*CAL']` vs a `.*CAL` ID → expect `True`.

6. **`Record._prep_row` builds the label `override` from the last column only, and reuses
   `target`** — *correctness, Medium.* The `override` dict (NULL_VALUE/VALID_MINIMUM/MAXIMUM) is
   assembled after the per-column loop from whichever values survived the final iteration, and
   the parameter `target` is overwritten by `event_key[1]` mid-loop. Intended: per-column
   overrides. *Test:* `test_geometry_prep.py` asserts overrides differ per column for a
   two-column descriptor with different formats (characterization → likely xfail).

7. **`Record._construct_excluded_mask` dead branch + scalar/array return inconsistency** —
   *robustness, Medium.* `if np.any(excluded): return excluded` precedes the unreachable
   `if np.all(excluded): return True`; the function returns a numpy array in some paths and a
   Python `bool` in others, and the `#!!!!` comment admits gridless backplanes are unhandled.
   *Test:* asserts all-True returns the array (documenting the unreachable `True`), all-False
   returns `False`, and a missing-target returns `True`.

8. **`index_support.py:_create_index` accumulator/scope bug** — *correctness, High.*
   `unused = None` is reset inside the `walk` loop, and `logger.close(force=True)` + the
   task-file write + the unused-columns warning run **inside** the per-directory loop. So the
   cross-volume "unused columns" intersection never accumulates and the log/task file are written
   repeatedly. *Test:* fake two-volume tree + recording `IndexTable` stub asserts a single close
   and a correctly intersected `unused`.

9. **`util.sclk_format_count` return-type mismatch** — *doc, Low.* Docstring `Returns: int`; it
   returns a delimited **string**. *Test:* asserts the exact string and `isinstance(result, str)`.

10. **`index_support.py:232` dead `assert` / `-O` fragility** — *robustness, Low.* The
    `assert value is not None` can never fire (line 229 already substituted `nullval`) and would
    be stripped under `python -O`. *Test:* documents that null-substitution, not the assert,
    enforces the invariant (no behavior assertion on the assert itself).

> Severity tags mirror `code_critique.md`. Items 3, 5, 6, 7, 8 are the same defects the critique
> listed as "Still open"; items 1, 2, 4, 9, 10 are additional findings from this review (1 and 2
> independently reproduced).

---

## 7. Risks & notes

- **`filterwarnings=["error"]` will surface third-party warnings** (numpy, oops, pdstemplate).
  Add narrowly-scoped, commented `ignore` entries as they appear; never blanket-ignore.
- **Global `task_list` in `common.py`** is mutated by tests — reset it in a fixture and keep its
  tests in one file to stay parallel-safe under `-n auto`.
- **`oops.Scalar` realism:** formatting tests use *real* polymath Scalars (verified to work
  kernel-free); only Backplane/Observation interactions are faked. This keeps the
  number-formatting tests honest rather than mock-shaped.
- **xfail vs hard-fail:** mark the ten bug tests `@pytest.mark.xfail(strict=True, reason=...)`
  so the suite stays green while documenting the defects; flip each to a passing test in the same
  commit that fixes the bug. This satisfies "write the test even if it fails" without redding CI.
- **Sequencing:** Plan 2 is independent of Plan 1 and is best done **first** — its
  characterization tests for `formatted_column`/`construct_excluded_mask`/`prep_row` are the
  behavior fence that makes Plan 1's extraction safe.
