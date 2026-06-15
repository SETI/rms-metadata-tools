# Plan 1 — Split `geometry_support.py` into files under 500 lines

**Goal:** Resolve `code_critique.md` §1 (module size). `src/metadata_tools/geometry_support.py`
is **1654 lines**; split it so every resulting file is **< 500 lines**, with **no change to
observable table/label output** and **no change to the public import surface**.

**Status of the target today:** still a single 1654-line module (listed as "Still open" in the
critique's 2026-06-15 status update).

---

## 1. Constraints that shape the split

1. **Preserve the public import path.** Convert `geometry_support.py` (a module) into
   `geometry_support/` (a package) so `import metadata_tools.geometry_support as geom` keeps
   working unchanged.
2. **Preserve the public API.** External references (verified by grep) are exactly:
   - `geom.process_tables`, `geom.get_args` — `hosts/GO_0xxx/GO_0xxx_geometry.py`,
     `GO_0xxx_geometry_cloud.py`.
   - `geom.SkyTable`, `geom.BodyTable`, `geom.RingTable`, `geom.InventoryTable` —
     `cumulative_support.py:159-180`.
   - No external code references `Record`, `Suite`, `SunTable`, `FORMAT_DICT`,
     `ALT_FORMAT_DICT`, `MISSION_TABLE`, but they are part of the module's surface and are
     re-exported for safety and for Plan 2's tests.
3. **Keep the host-config plugin convention.** The module imports `geometry_config` as a
   *top-level* module (`import geometry_config as config`). Only the submodules that actually
   use it should import it (`formats.py`, `record.py`, `suite.py`, `process.py`); `masks.py`,
   `formatting.py`, `prep.py` must stay config-free so they are import-clean and unit-testable.
4. **Byte-for-byte output.** No reordering of `FORMAT_DICT`/`ALT_FORMAT_DICT`, no change to the
   column-iteration order, no change to formatting/rounding. Extraction is mechanical.
5. **Do not fix bugs here.** The latent correctness bugs in `_prep_row`,
   `_construct_excluded_mask`, `_obs_excluded`, `postprocess` (see Plan 2's report) are
   **moved verbatim**, not repaired, so this refactor is reviewable as a pure structural change.
   Bug fixes land in a separate commit after Plan 2's tests pin the current behavior.

---

## 2. Current contents and approximate sizes

| Region | Lines (approx) | Destination |
|---|---:|---|
| Header + imports | 1–20 | distributed |
| `FORMAT_DICT`, `ALT_FORMAT_DICT`, `MISSION_TABLE` + doc comment | 22–128 (~107) | `formats.py` |
| `Record.__init__` | 138–216 (~80) | `record.py` |
| `Record._inventory` | 219–254 (~36) | `bodies_select.py` |
| `Record._select_bodies` | 257–313 (~57) | `bodies_select.py` |
| `Record.get_backplane_key` (static) | 316–328 (~13) | `record.py` |
| `Record.get_key_map` | 331–360 (~30) | `record.py` |
| `Record.postprocess` (+ `link_null`) | 363–420 (~58) | `record.py` |
| `Record._meshgrid` | 423–433 (~11) | `record.py` |
| `Record._get_system` | 436–452 (~17) | `bodies_select.py` |
| `Record.add` | 455–528 (~74) | `record.py` |
| `Record._prep_row` | 531–756 (~226) | `prep.py` |
| `Record._append_body_prefix` (static) | 759–784 (~26) | `prep.py` |
| `Record._construct_excluded_mask` (static) | 787–879 (~93) | `masks.py` |
| `Record._circle_coverage` | 882–909 (~28) | `formatting.py` |
| `Record._formatted_column` | 912–1004 (~93) | `formatting.py` |
| `Record._obs_excluded` | 1007–1031 (~25) | `bodies_select.py` |
| `Record._get_primary` | 1034–1060 (~27) | `bodies_select.py` |
| `InventoryTable/SkyTable/SunTable/RingTable/BodyTable` | 1063–1227 (~165) | `tables.py` |
| `Suite` | 1229–1497 (~270) | `suite.py` |
| `get_args`, `process_tables` | 1499–1654 (~156) | `process.py` |

---

## 3. Target package layout (10 files, all < 500 lines)

```
metadata_tools/geometry_support/
├── __init__.py        (~45)  re-export the public API; package docstring
├── formats.py         (~115) FORMAT_DICT, ALT_FORMAT_DICT, MISSION_TABLE, format-tuple docs
├── masks.py           (~115) construct_excluded_mask()                [config-free, oops+np]
├── formatting.py      (~150) formatted_column(), circle_coverage()    [config-free]
├── prep.py            (~250) prep_row(), append_body_prefix()         [config-free]
├── bodies_select.py   (~200) inventory(), select_bodies(), get_system(),
│                              get_primary(), obs_excluded()
├── record.py          (~310) class Record: __init__, _meshgrid, get_backplane_key,
│                              get_key_map, postprocess, add
├── tables.py          (~190) InventoryTable, SkyTable, SunTable, RingTable, BodyTable
├── suite.py           (~290) class Suite
└── process.py         (~165) get_args(), process_tables()
```

### Design choice: free functions for the pure helpers

The five genuinely state-light helpers — `construct_excluded_mask`, `formatted_column`,
`circle_coverage`, `prep_row`, and the `bodies_select` cluster — become **module-level
functions** rather than methods. Rationale:

- They are already effectively static. `_construct_excluded_mask`, `_append_body_prefix`,
  `get_backplane_key` are `@staticmethod` today; `_formatted_column`/`_circle_coverage` use
  only `self.sampling`; `_select_bodies` is even *called* statically already
  (`Record._select_bodies(self, col.BODIES)` at line 201).
- Free functions with explicit parameters are **directly unit-testable** without constructing
  a SPICE-backed `Record` — which is exactly what Plan 2 needs for coverage. This is the main
  reason to prefer functions over a mixin here.
- `Record` stays a real, cohesive class for the orchestration methods (`add`, `get_key_map`,
  `postprocess`) that genuinely thread instance state.

**Alternative considered (documented, not recommended):** keep everything as methods and split
`Record` across files using mixins (`RecordBodiesMixin`, `RecordRowsMixin`). Zero call-site
churn, but the mixins reference attributes they don't define (`self.pointing_available`, …),
which is awkward under `mypy --strict` and leaves the helpers un-testable in isolation. Use
this only if review prefers minimal call-site edits over testability.

---

## 4. Function signatures after extraction

```python
# masks.py
def construct_excluded_mask(backplane, target, primary, mask_desc, *,
                            blocker=None, ignore_shadows=True): ...

# formatting.py
def formatted_column(values, fmt, sampling): ...          # was _formatted_column(self, values, format)
def circle_coverage(angles, null_value, sampling, flag=None): ...  # was _circle_coverage

# prep.py
def prep_row(record, prefixes, backplane, blocker, column_descs, *,
             primary=None, target=None, name_length=defs.NAME_LENGTH,
             tiles=None, tiling_min=100, ignore_shadows=False,
             start_index=1, allow_zero_rows=True, no_mask=False, no_body=False): ...
def append_body_prefix(prefix_columns, body, length): ...

# bodies_select.py  (record passed explicitly; read-only access to record state)
def inventory(record, bodies): ...
def select_bodies(record, bodies): ...
def get_system(body): ...                # pure: depends only on oops registry
def get_primary(record, table, sclk): ...
def obs_excluded(record, exceptions): ...
```

Note `fmt`/`sampling` replace the builtin-shadowing `format` and the `self` lookups — this also
clears the §2 `A002` "redefining `format`" finding for these functions as a free side effect
(do not rename anything else; that is a separate cleanup).

---

## 5. Call-site rewrites inside the package

| Old (inside `Record`) | New |
|---|---|
| `Record._construct_excluded_mask(...)` (in `prep_row`) | `masks.construct_excluded_mask(...)` |
| `self._formatted_column(values, format)` (in `prep_row`) | `formatting.formatted_column(values, fmt, record.sampling)` |
| `self._circle_coverage(...)` (in `formatted_column`) | `formatting.circle_coverage(...)` |
| `Record._append_body_prefix(...)` (in `prep_row`) | `prep.append_body_prefix(...)` |
| `self._prep_row(...)` (in `Record.add`) | `prep.prep_row(self, ...)` |
| `Record._select_bodies(self, …)` / `self._inventory(…)` (in `__init__`) | `bodies_select.select_bodies(self, …)` / `bodies_select.inventory(self, …)` |
| `self._get_primary(MISSION_TABLE, sclk)` (in `__init__`) | `bodies_select.get_primary(self, formats.MISSION_TABLE, sclk)` |
| `self._get_system(...)` (several) | `bodies_select.get_system(...)` |

`prep_row`'s internal recursion (`self._prep_row(...)`, lines 609, 620, 753) becomes
`prep_row(record, ...)`. `formatted_column` and `circle_coverage` reference each other within
`formatting.py`.

`record.py` imports: `from metadata_tools.geometry_support import formats, masks, formatting,
prep, bodies_select`. To avoid an import cycle (`__init__` imports `record`, `record` imports
siblings), submodules import each other **directly by submodule** (`from metadata_tools.
geometry_support import masks`), never from the package `__init__`.

---

## 6. `__init__.py` re-export

```python
from metadata_tools.geometry_support.formats import (
    FORMAT_DICT, ALT_FORMAT_DICT, MISSION_TABLE)
from metadata_tools.geometry_support.record import Record
from metadata_tools.geometry_support.tables import (
    InventoryTable, SkyTable, SunTable, RingTable, BodyTable)
from metadata_tools.geometry_support.suite import Suite
from metadata_tools.geometry_support.process import get_args, process_tables

__all__ = ['FORMAT_DICT', 'ALT_FORMAT_DICT', 'MISSION_TABLE', 'Record',
           'InventoryTable', 'SkyTable', 'SunTable', 'RingTable', 'BodyTable',
           'Suite', 'get_args', 'process_tables']
```

`tables.py`, `suite.py`, `process.py`, `cumulative_support.py` must continue to see the same
names. `cumulative_support.py` is unaffected (`geom.SkyTable` etc. resolve through `__init__`).

---

## 7. Import-cycle / load-order notes

- `formats.py` runs `MISSION_TABLE = util.convert_mission_table(config.MISSION_TABLE, config.SC)`
  at import — keep that module-level statement intact (it is why importing the package needs
  `geometry_config` on `sys.path`, unchanged from today).
- `record.py` does `import metadata_tools.columns as col` (the BODIES registry) — unchanged.
- Submodule import graph is a DAG: `formats` ← (record, suite, process); `masks`,`formatting` ←
  `prep` ← `record`; `bodies_select` ← `record`; `tables` ← (suite, __init__); `suite` ←
  (process, __init__). No cycles as long as nobody imports the package `__init__` internally.

---

## 8. The one test that must be updated

`tests/test_geometry_columns_contract.py` reads the source **as a file path**:
`_GEOMETRY_SUPPORT = _SRC / 'geometry_support.py'`. After the split, the `col.<NAME>`
references live in `record.py`. Update the test to point at
`geometry_support/record.py` (or, better, glob every `*.py` in the package directory and union
the `col.*` attributes). This is the only existing test that touches the file directly.

---

## 9. Step-by-step execution order

1. Create the package dir; move `FORMAT_DICT`/`ALT_FORMAT_DICT`/`MISSION_TABLE` into
   `formats.py`. Add a temporary `from .formats import *`-style shim only if needed mid-refactor.
2. Extract `masks.py`, then `formatting.py`, then `prep.py` (each config-free), updating
   call sites as you go. Run `ruff check` after each extraction.
3. Extract `bodies_select.py`; rewrite `Record.__init__`'s body-selection calls.
4. Move the remaining `Record` methods into `record.py`.
5. Move the five table classes into `tables.py`; move `Suite` into `suite.py`; move `get_args`
   /`process_tables` into `process.py`.
6. Write `__init__.py` re-exports; delete the original `geometry_support.py`.
7. Update `tests/test_geometry_columns_contract.py` path.
8. Verify (see §10).

Land as one commit (or a short stack), message e.g. `refactor: split geometry_support into a
package`.

---

## 10. Verification (no behavior change)

- **Import smoke test (hermetic):** with the Plan 2 mocks in place,
  `import metadata_tools.geometry_support as g; g.FORMAT_DICT; g.SkyTable; g.process_tables`
  must succeed; `len(g.FORMAT_DICT) == 52`.
- **Contract test:** `pytest tests/test_geometry_columns_contract.py` green after the path fix.
- **Line budget:** `find src/metadata_tools/geometry_support -name '*.py' | xargs wc -l` — every
  file < 500.
- **Lint/type:** `ruff check src` no new findings; `ruff format --check`. (`mypy` is not green
  repo-wide today; do not regress the files that already pass.)
- **Output equivalence (strongest, SPICE-gated):** if a SPICE environment is available, generate
  one volume's geometry tables before and after the split and `diff` the `.tab`/`.lbl` output —
  must be identical. If SPICE is unavailable in CI, rely on the import + contract + Plan 2 unit
  tests (which pin `formatted_column`, `construct_excluded_mask`, `prep_row`, `get_primary`
  behavior) as the behavior fence.
- **Grep regression:** confirm no remaining references to the old method names
  (`_formatted_column`, `_prep_row`, `_construct_excluded_mask`, `_select_bodies`, …) outside
  the package.

---

## 11. Risks

- **Hidden state coupling:** `prep_row` mutates `target` and reuses loop-scoped names (a known
  bug). Moving it verbatim preserves that behavior — **do not "tidy" it** during the move, or you
  risk changing output. Plan 2 pins it first.
- **`locals()['link_' + link]` in `postprocess`** depends on the nested `link_null` being a
  local of `postprocess`. Keep `link_null` nested inside `postprocess` in `record.py`; do not
  hoist it to module scope or the `locals()` lookup breaks.
- **Import order:** `formats.MISSION_TABLE` executes config-dependent code at import; keep it in
  the single module that the package `__init__` imports first.
