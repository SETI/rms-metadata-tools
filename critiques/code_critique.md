# Code Critique: rms-metadata-tools

Generated after reading every file in the repository, including all source modules,
tests, CI workflows, GCP startup scripts, PDS3 label templates, and configuration
files. Findings are grouped by severity and type. Each item includes a precise
location, the problem, and complete instructions for fixing it.

**Authoritative rules:** `.cursor/rules/python.mdc`, `filecache.mdc`, `logging.mdc`, `dependency_management.mdc`, `environment.mdc`, `security.mdc`, `git_workflow.mdc`

---

## 1. Critical Bugs

### 1.1 Broken shell command in `gcp_cumulative_startup.sh` — RESOLVED (2026-06-29)

**File:** `src/metadata_tools/hosts/GO_0xxx/gcp_cumulative_startup.sh`, lines 26–28

**Problem:** The `--task-file` argument is on its own line without a `\` continuation.
Bash treats it as a separate command (`--task-file ...`), which fails silently or with
a "command not found" error; the cumulative cloud worker is invoked without its task file.

```bash
# CURRENT (broken):
python3 src/metadata_tools/hosts/GO_0xxx/GO_0xxx_cumulative_cloud.py \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/
                --task-file src/metadata_tools/hosts/GO_0xxx/cumulative_tasks.json
```

**Fix:** Add the missing `\` at the end of the GCS path line:

```bash
python3 src/metadata_tools/hosts/GO_0xxx/GO_0xxx_cumulative_cloud.py \
                gs://rms-metadata-jspitale/metadata_test/GO_0xxx/GO_0999/ \
                --task-file src/metadata_tools/hosts/GO_0xxx/cumulative_tasks.json
```

---

### 1.2 Template variable inconsistency in `GO_0xxx_ring_summary.lbl` — RESOLVED (2026-06-29)

**File:** `src/metadata_tools/hosts/GO_0xxx/templates/GO_0xxx_ring_summary.lbl`, line 37

**Problem:** The ring summary template uses `$IF(TABLE_TYPE == 'CUMULATIVE')` but the
body summary template (`GO_0xxx_body_summary.lbl`, line 40) uses `$IF(index_type ==
'CUMULATIVE')`. `TABLE_TYPE` is a template field injected by `label_support.create()`
(passed as `table_type`), whereas `index_type` is a locally-scoped `$ONCE` variable.
These check different values and will produce different behavior, meaning one of the
two templates generates the wrong description text.

**Fix:** Verify which variable is intended (the `$ONCE` local `index_type` is defined
at the top of the ring template on line 14, so it should be used):

In `GO_0xxx_ring_summary.lbl`, replace:
```
$IF(TABLE_TYPE == 'CUMULATIVE')
```
with:
```
$IF(index_type == 'CUMULATIVE')
```

---

### 1.3 Silent loss of `self.observations` after logging an error — RESOLVED (2026-06-29)

**File:** `src/metadata_tools/geometry_support/suite.py`, lines 93–97

**Problem:** When `config.from_index()` raises `FileNotFoundError`, the code logs the
traceback but does not raise, return, or set `self.observations` to an empty list.
Execution continues to `add_tables()` and `meshgrids()` on lines 100–104. Later,
`self.create()` accesses `self.observations` (line 242), but the attribute was never
assigned, causing an `AttributeError` at runtime instead of a clean error.

**Fix applied:** Replaced `logger.error(traceback.format_exc())` with
`logger.exception('Index file not found for %s', self.volume_id)` (per `logging.mdc`)
and added `return` to halt `__init__` on missing index. Removed unused `import traceback`.

---

## 2. Standards Violations (`.cursor/rules/`)

### 2.1 `filecache.mdc` — `.exists()` used as pre-flight check

**Rule:** Never use `fcpath.exists()` as a pre-flight check; use try/except
`FileNotFoundError` (EAFP pattern).

**Location 1:** `src/metadata_tools/label_support.py`, line 34

```python
if not filepath.exists():
    return
```

**Fix:** Replace with:

```python
try:
    # proceed with template work
except FileNotFoundError:
    return
```

Concretely, wrap the `PdsTemplate()` construction and `template.write()` call in the
try block and catch `FileNotFoundError` rather than pre-checking.

**Location 2:** `src/metadata_tools/index_support/table.py` (previously `index_support.py`)

```python
if not self.primary_index_label_path.exists():
```

**Fix:** Replace the exists() check with a try/except around the code that reads the
primary index label path, catching `FileNotFoundError`.

---

### 2.2 `logging.mdc` — `logger.error(traceback.format_exc())` instead of `logger.exception()`

**File:** `src/metadata_tools/geometry_support/suite.py`, line 97

**Rule:** Inside an `except` block, use `logger.exception()` which automatically
captures the current exception and traceback. Never use `logger.error(traceback.format_exc())`.

**Fix:**
```python
# BEFORE:
import traceback
...
except FileNotFoundError:
    logger.error(traceback.format_exc())

# AFTER (also remove `import traceback` at line 5 if no other usage):
except FileNotFoundError:
    logger.exception('Failed to load index for %s', self.volume_id)
    return
```

---

### 2.3 `python.mdc` — Mutable module-level globals

**Location 1:** `src/metadata_tools/common.py`

```python
task_list: list[dict[str, Any]] = []
```

This mutable list is a module-level singleton. Under `pytest-xdist` parallel workers
or any multi-threaded use, concurrent `add_task()` / `task_list.clear()` calls are
not thread-safe. The `python.mdc` rule prohibits mutable globals.

**Fix:** Encapsulate task state in a class or use a context-local object. At minimum,
document the single-threaded requirement and add a threading lock if the module is ever
used concurrently:

```python
import threading
_task_list_lock = threading.Lock()
task_list: list[dict[str, Any]] = []
```

Or redesign `add_task` / `task_source` / `write_task_file` to accept an explicit list
parameter rather than mutating the global.

**Location 2:** `src/metadata_tools/defs.py`

```python
TRANSLATIONS: dict[str, str] = {}
```

This empty mutable dict is populated by callers. Document who owns it and when it is
populated, or replace it with an immutable default and a function-level parameter.

---

### 2.4 `python.mdc` — `assert` in library code

**File:** `src/metadata_tools/common.py`, line 239

```python
assert table_type is not None  # nosec B101 - type-narrowing invariant, not validation
```

The `nosec B101` suppressor and the comment explain the intent, but `assert` is stripped
by Python's optimizer (`-O` flag). In library code called from cloud workers, use an
explicit `if/raise` guard instead:

```python
if table_type is None:
    raise ValueError('table_type must not be None')
```

---

### 2.5 `python.mdc` — Functions with more than 3 positional parameters

The following functions exceed the 3-positional-argument limit from `python.mdc`:

| Function | File | Approx. param count |
|---|---|---|
| `IndexTable.__init__` | `index_support/table.py` | ~10 |
| `_create_index()` | `index_support/process.py` | ~10 |
| `process_index()` | `index_support/process.py` | ~8 |
| `prep_row()` | `geometry_support/prep.py` | ~12 |
| `create` (of various Table classes) | multiple | varies |

**Fix for each:** Introduce a dataclass or keyword-only parameters (`*` separator) to
force callers to name arguments and reduce accidental positional mismatches:

```python
# Example for _create_index:
def _create_index(
    volume_tree: FCPath,
    output_tree: FCPath,
    template_path: FCPath,
    *,
    qualifier: str = '',
    volumes: list[str] | None = None,
    ...
) -> None:
```

---

### 2.6 `python.mdc` — `locals()` dictionary for dynamic attribute lookup

**File:** `src/metadata_tools/geometry_support/record.py`, line ~207

```python
locals()['link_' + link]
```

**Problem:** `locals()` is not guaranteed to reflect the actual local scope in all
Python implementations; it creates a hidden coupling between a variable name and string
concatenation. This is fragile and mypy cannot type-check it.

**Fix:** Replace with an explicit dict:

```python
_link_handlers = {
    'ring': link_ring,
    'body': link_body,
    # etc.
}
_link_handlers[link](...)
```

---

### 2.7 `filecache.mdc` — Multiple `from pathlib import Path` imports in library code

The following library source files import `pathlib.Path` instead of using `FCPath`
exclusively:

- `src/metadata_tools/util.py` (line 8)
- `src/metadata_tools/index_support.py` (line 8)
- `src/metadata_tools/label_support.py` (line 6)
- `src/metadata_tools/common.py` (line 13)
- `src/metadata_tools/cumulative_support.py` (line 7)
- `src/metadata_tools/geometry_support/suite.py` (line 6)
- `src/metadata_tools/geometry_support/tables.py` (line 4)
- `src/metadata_tools/hosts/GO_0xxx/host_config.py` (line 6)
- `src/metadata_tools/hosts/GO_0xxx/index_config.py` (line 7)

In each case, review whether the `Path` usage could be replaced with `FCPath`. Where
`Path` is needed for a third-party API that does not accept `FCPath`, use
`fcpath.get_local_path()` to get a real local path and `fcpath.upload()` afterwards.
At the very least, never downcast an `FCPath` to a plain `Path` or `str`.

---

### 2.8 `python.mdc` — Weak type annotation `dict[str, object]`

**File:** `src/metadata_tools/columns/body.py`

```python
BODY_TILE_DICT: dict[str, object] = {}
```

`object` is the root type and carries no useful information for type checkers or readers.

**Fix:** Determine the actual value type. If the values are tile-list structures, annotate
them precisely:

```python
from metadata_tools.geometry_support.tiles import TileList  # or whatever the type is
BODY_TILE_DICT: dict[str, TileList] = {}
```

---

## 3. Architecture / Import Issues

### 3.1 Module-level SPICE-dependent code

**Files:**
- `src/metadata_tools/bodies.py`: `BODIES = get_bodies(defs.BODY_NAMES)` — runs on import
- `src/metadata_tools/columns/body.py`: `BODY_SUMMARY_DICT` and `BODY_TILE_DICT` built at
  module level in for-loops over `BODIES` — runs on import, SPICE-dependent

**Problem:** Any test or tool that imports these modules (even transitively) triggers
the SPICE body registry, which fails without a fully-initialized `oops` host. The
`conftest.py` works around this with a fake `metadata_tools.bodies` stub, but the
stub must be kept in sync with the real module's interface by hand.

**Fix:** Lazy initialization. Replace module-level execution with a
`get_bodies()` / `get_body_summary_dict()` function that is called once and cached:

```python
# bodies.py
_BODIES: dict[str, Any] | None = None

def get_bodies_registry() -> dict[str, Any]:
    global _BODIES
    if _BODIES is None:
        _BODIES = get_bodies(defs.BODY_NAMES)
    return _BODIES
```

This removes the import-time side effect and makes the stub in `conftest.py` unnecessary.

---

### 3.2 `sys.path.append('')` security concern

**Note (2026-06-30):** The new `src/metadata_tools/cli/` package consolidates the GCP
cloud worker entry points. The `sys.path.append('')` shim should be addressed there
rather than in the per-host scripts.

**Files (per-host, superseded by `cli/` for new hosts):**
- `src/metadata_tools/hosts/GO_0xxx/GO_0xxx_index_cloud.py`, line 32
- `src/metadata_tools/hosts/GO_0xxx/GO_0xxx_geometry_cloud.py`, line 33
- `src/metadata_tools/hosts/GO_0xxx/GO_0xxx_cumulative_cloud.py`, line 31
- `src/metadata_tools/hosts/GO_0xxx/host_init.py`, line 12

**Problem:** `sys.path.append('')` inserts the current working directory at the end of
`sys.path`. On a GCP instance this is intentional (needed to resolve the CWD-based
host plugin imports). However, this is a security risk: any file named the same as a
standard library module in the CWD would shadow it.

**Better approach:** Explicitly append the host directory path rather than `''`:

```python
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
```

Or better still, reorganize host plugins as proper package-qualified imports so
`sys.path` manipulation is not needed.

---

### 3.3 `eval()` on column definition strings — RESOLVED (2026-06-29)

**File:** `src/metadata_tools/util.py`

**Problem:** `eval()` executes arbitrary Python. The `nosec` suppressor acknowledged
the risk and issue #110 tracked a fix. The strings evaluated are column-definition
references like `defs.RING_SYSTEM_RADII["bodyx"]`.

**Fix applied:** Replaced `eval(lrep[i])` with `_resolve_dict_ref(lrep[i])`, a private
function that parses the `defs.<ATTR>["<key>"]` pattern with a compiled regex and
performs a safe `getattr(defs, attr_name)[key]` lookup. Only `defs` is accessible;
any other module name raises `ValueError`. The `nosec B307` suppressor is removed.

---

## 4. Code Quality Issues

### 4.1 O(n²) body sort in `bodies_select.py`

**File:** `src/metadata_tools/geometry_support/bodies_select.py`

```python
body_names.sort(key=lambda name: list(col.BODIES.keys()).index(name))
```

**Problem:** `list(col.BODIES.keys())` is rebuilt on every comparison. For N bodies
this is O(N²).

**Fix:** Build the lookup once before sorting:

```python
bodies_order = {name: i for i, name in enumerate(col.BODIES.keys())}
body_names.sort(key=lambda name: bodies_order.get(name, len(bodies_order)))
```

---

### 4.2 Commented-out code that should be removed or resolved

All of the following commented-out blocks violate the convention of keeping the
codebase clean. Each should either be removed (if abandoned) or completed and
uncommented (if needed):

| File | Description |
|---|---|
| `geometry_support/suite.py` | `# SunTable` commented out in `add_tables()`; sun geometry is disabled but still tested in `test_geometry_tables.py` via `SunTable` |
| `geometry_support/suite.py` | `# Run post-processor` and `# self.post()` |
| `geometry_support/suite.py` | `# Build overrides dict` block |
| `geometry_support/record.py` | `self.overrides += overrides  ## this is for future development` |
| `hosts/GO_0xxx/geometry_config.py` | legacy MISSION_TABLE entries (large block) |
| `hosts/GO_0xxx/gcp_geometry_startup.sh` | `### modified unmerged oops branch (TBR)` |
| `tests/hosts/GO_0xxx/test_geometry.py` | Commented-out import and test body code |

**Fix:** For each block, make a decision: remove it (preferred) or create a GitHub
issue tracking the future work and reference it in a single-line comment.

---

### 4.3 `util.py` is too large and has unfulfilled refactor comments

**File:** `src/metadata_tools/util.py` (~775 lines)

Multiple `### move to utilities` comments appear inside the file, indicating planned
refactoring that was never completed. The module mixes SCLK arithmetic, path helpers,
text-file I/O, column-reference evaluation, and statistical range utilities.

**Fix:** Split into focused modules:
- `util_sclk.py` — SCLK tick arithmetic (`add_by_base`, `rebase`, `sclk_split_count`, etc.)
- `util_path.py` — path helpers (`select_dir`, `splitpath`, `get_volume_subdir`, etc.)
- `util_io.py` — text-file helpers (`read_txt_file`, `write_txt_file`, `append_txt_file`)
- Keep `util.py` as a re-export shim while the migration happens

Remove the `### move to utilities` comments as each section is moved.

---

### 4.4 `prep_row()` is too long

**File:** `src/metadata_tools/geometry_support/prep.py`

`prep_row()` is >160 lines and handles summary rows, detailed rows, multiple tile sets,
body prefixes, masking, overrides, and edge cases through a recursive call pattern.

**Fix:** Extract the following sub-operations into private functions:
- `_build_body_prefix_columns(cols, target, primary, no_body, sampling)` 
- `_evaluate_column(backplane, desc, mask, null_format, fmt)` → `str`
- `_collapse_tiles(tiles, tiling_min, backplane)` → `list[Any]`

Each sub-function can then be tested in isolation.

---

### 4.5 `test_geometry_cumulative` always returns immediately

**File:** `tests/test_geometry.py`, lines 34–45

```python
def test_geometry_cumulative() -> None:
    return   # ← always exits here
    # Get labels to test
    ##### this needs to be changed to match cumulative files
    files = support.match(support.METADATA, '*_summary.lbl')
    ...
```

**Problem:** This test never runs its body. The `return` on line 35 means the test
function is a no-op that always passes. The dead code below is unreachable.

**Fix:** Either fix the glob pattern (update the comment and the pattern) and remove the
`return`, or skip explicitly:

```python
def test_geometry_cumulative() -> None:
    pytest.skip('TODO: update glob to match cumulative geometry files')
```

---

### 4.6 Duplicate tile in `ring.py` OUTER_RING_TILES for SATURN

**File:** `src/metadata_tools/columns/ring.py`

In `OUTER_RING_TILES['SATURN']`, indices 7 and 8 appear to have overlapping or
duplicate angular ranges (both around `0.80π` to `1.20π`). Review the tile boundaries
and confirm whether this is intentional or a copy-paste error.

**Fix:** Print or log the tile boundaries and verify against the physical tile
definitions. If duplicate, remove the redundant tile.

---

### 4.7 `SKY_TILES` not tested — `###TODO: not tested...` comment

**File:** `src/metadata_tools/columns/sky.py`, line 55

```python
###TODO: not tested...
```

**Fix:** Remove the `###TODO` comment. Add a test in `tests/columns/test_sky.py`
that verifies `SKY_TILES` has the expected structure (at minimum, a list of tile
descriptors with correct key names), similar to the ring tile tests.

---

### 4.8 `pyproject.toml` missing `filterwarnings = ["error"]`

**File:** `pyproject.toml`, `[tool.pytest.ini_options]` section

**Rule:** `python_testing.mdc` requires `filterwarnings = ["error"]` so that
`DeprecationWarning` and other warnings are promoted to errors in tests.

**Fix:** Add to `[tool.pytest.ini_options]`:

```toml
filterwarnings = [
    "error",
    # add specific ignores here if needed for third-party noise
]
```

---

### 4.9 `CONTRIBUTING.md` commit message example does not follow Conventional Commits

**File:** `CONTRIBUTING.md`, line 49

```bash
git commit -m "Add feature: description of your changes"
```

This format ("Add feature: ...") does not match the Conventional Commits format
required by `git_workflow.mdc` (`feat: imperative summary`).

**Fix:** Replace with:

```bash
git commit -m "feat: add description of your changes"
```

And update the adjacent prose to link to `git_workflow.mdc`.

---

## 5. CI/CD Issues

### 5.1 GCP startup scripts clone from `jns-test-gcp` branch

**Files:** `gcp_index_startup.sh`, `gcp_geometry_startup.sh`, `gcp_cumulative_startup.sh`

All three scripts contain:
```bash
git clone -b jns-test-gcp --single-branch https://github.com/SETI/rms-metadata-tools.git
```

This is a development artifact. Production GCP workers should clone from `main` or a
pinned release tag.

**Fix:** Change to `main` (or a release tag) before deploying to production:

```bash
git clone --branch main --single-branch https://github.com/SETI/rms-metadata-tools.git
```

---

### 5.2 GCP startup scripts use `pip install -r requirements.txt` incorrectly

**Files:** All three GCP startup scripts, line ~22

```bash
pip install -r requirements.txt
```

`requirements.txt` contains only `-e .[dev,cloud]`. The `-e` (editable) flag requires
a proper package structure. On GCP instances the correct invocation is:

```bash
pip install ".[cloud]"
```

---

### 5.3 `gcp_geometry_startup.sh` has duplicate `export OOPS_RESOURCES=` line

**File:** `src/metadata_tools/hosts/GO_0xxx/gcp_geometry_startup.sh`, lines 10 and 34

Line 10 sets `OOPS_RESOURCES` and line 34 sets it again to the same value.

**Fix:** Remove the duplicate on line 34.

---

### 5.4 PyPI publishing uses API tokens, not Trusted Publishers OIDC

**Files:** `.github/workflows/publish_to_pypi.yml`, `.github/workflows/publish_to_test_pypi.yml`

```yaml
user: __token__
password: ${{ secrets.PYPI_API_TOKEN }}
```

**Problem:** API tokens are long-lived credentials. PyPA's recommended approach is
Trusted Publishers (OIDC), which uses short-lived tokens with no stored secret.

**Fix:** Configure PyPI Trusted Publisher for SETI/rms-metadata-tools on pypi.org
and test.pypi.org, then update the workflow:

```yaml
permissions:
  id-token: write   # required for Trusted Publisher

- name: Publish package
  uses: pypa/gh-action-pypi-publish@release/v1
  # No user/password needed — authentication is automatic via OIDC
```

---

### 5.5 `publish_to_test_pypi.yml` references non-existent action versions

**File:** `.github/workflows/publish_to_test_pypi.yml`

```yaml
uses: actions/checkout@v6
uses: actions/setup-python@v6
```

`v6` does not exist. Current stable is `v4`.

**Fix:**

```yaml
uses: actions/checkout@v4
uses: actions/setup-python@v4
```

---

### 5.6 Ruff format check excluded from CI

**File:** `scripts/run-all-checks.sh`

`ENABLE_RUFF_FORMAT=false` by default. `ruff format --check` is not run in CI,
so formatting violations are never caught automatically.

**Fix:** Either change the default to `true` in `run-all-checks.sh`, or add
`ruff format --check src tests` explicitly to the CI lint job in
`.github/workflows/run-tests.yml`.

---

### 5.7 Sphinx built with `-W` but not `-n` (nitpicky mode)

**Files:** `scripts/run-all-checks.sh`, `.github/workflows/run-tests.yml`

Sphinx is invoked with `SPHINXOPTS="-W"` (fail on warnings) but not `-n` (nitpicky
mode, which catches undocumented objects and missing cross-references).

**Fix:** Add `-n` to the Sphinx options in both files:

```
SPHINXOPTS="-W -n"
```

---

## 6. pyproject.toml Issues

### 6.1 Entry point placeholder never defined

**File:** `pyproject.toml`, `[project.scripts]` section

```toml
#TODO = "main.metadata_tools:main"
```

This line is commented out and the module `main.metadata_tools` does not exist.

**Fix:** Either implement a `metadata_tools.__main__` entry point and uncomment with
the correct format, or remove this line entirely.

---

### 6.2 `py.typed` vs. comment contradiction

**File:** `pyproject.toml`

`py.typed` appears in `[tool.setuptools.package-data]`, making the package advertise
PEP 561 type information. However a comment says it is "NOT advertised."

**Fix:** Decide whether the package is typed. If yes, ensure `py.typed` exists in
`src/metadata_tools/` and remove the contradicting comment. If no, remove the
`py.typed` entry from `package-data`.

---

## 7. Minor Issues

### 7.1 `archive_support.py` uses `os`/`glob` instead of FCPath

**File:** `tests/archive_support.py`

The helper uses `os.walk`, `glob.glob`, and `os.path.join`. This works for local
archives but cannot be extended to GCS-backed test archives.

**Fix:** Replace with FCPath-based equivalents if GCS test archive support is needed.

---

### 7.2 `archive_support.py` uses old-style `Args:` docstrings; typo in parameter type

**File:** `tests/archive_support.py`

Docstrings use `Args:` instead of `Parameters:` (the project standard from
`python.mdc`). The `bounds` docstring also has a typo: `key (tstr):` instead of
`key (str):`.

**Fix:** Replace all `Args:` with `Parameters:` and fix the `tstr` typo.

---

### 7.3 `__init__.py` module docstring in RST format

**File:** `src/metadata_tools/__init__.py`

The module docstring uses RST-style formatting (`:mod:`, `:func:`) instead of
Google-style prose (required by `python.mdc`).

**Fix:** Convert to plain Google-style prose without RST directives.

---

### 7.4 `geometry_config.py:except_test()` always returns `False`

**File:** `src/metadata_tools/hosts/GO_0xxx/geometry_config.py`

```python
def except_test() -> bool:
    return False
```

This template stub permanently excludes nothing. If it is only ever `False`,
referencing it in `exclude` lists adds unnecessary complexity.

**Fix:** If no exceptions are needed for GO_0xxx, remove `except_test` from the
`exclude` list and document the purpose of this hook in a comment.

---

### 7.5 `GO_0xxx_supplemental_index.lbl` has unquoted `NAME` values for two columns

**File:** `src/metadata_tools/hosts/GO_0xxx/templates/GO_0xxx_supplemental_index.lbl`, lines 159, 186

```
NAME                        = PRODUCT_VERSION_ID
NAME                        = COMPRESSION_QUANTIZATION_TABLE_ID
```

All other `NAME` assignments in the template are quoted strings (e.g.,
`NAME = "VOLUME_ID"`). The unquoted form is valid PDS3 but inconsistent.

**Fix:** Add quotes for consistency:

```
NAME                        = "PRODUCT_VERSION_ID"
NAME                        = "COMPRESSION_QUANTIZATION_TABLE_ID"
```

---

### 7.6 `geometry_support/masks.py` — `#!!!!` comment signals undocumented known issue

**File:** `src/metadata_tools/geometry_support/masks.py`, line ~95

```python
#!!!!
```

**Fix:** Replace with a proper comment explaining the issue and a reference to a
tracking issue:

```python
# TODO(#NNN): Gridless backplanes return a scalar mask, incompatible with the
# array-based masking below. Handle this case separately.
```

---

## Summary Table

| # | Severity | Category | File(s) |
|---|---|---|---|
| 1.1 | **Critical** ✓ | Bug | `gcp_cumulative_startup.sh` |
| 1.2 | **Critical** ✓ | Bug | `GO_0xxx_ring_summary.lbl` |
| 1.3 | **Critical** | Bug | `geometry_support/suite.py` |
| 2.1 | High | Standards (`filecache.mdc`) | `label_support.py`, `index_support.py` |
| 2.2 | High | Standards (`logging.mdc`) | `geometry_support/suite.py` |
| 2.3 | High | Standards (`python.mdc`) | `common.py`, `defs.py` |
| 2.4 | Medium | Standards (`python.mdc`) | `common.py` |
| 2.5 | Medium | Standards (`python.mdc`) | `index_support.py`, `prep.py` |
| 2.6 | Medium | Standards (`python.mdc`) | `geometry_support/record.py` |
| 2.7 | Medium | Standards (`filecache.mdc`) | multiple |
| 2.8 | Low | Standards (`python.mdc`) | `columns/body.py` |
| 3.1 | High | Architecture | `bodies.py`, `columns/body.py` |
| 3.2 | Medium | Security | cloud scripts, `host_init.py` |
| 3.3 | Medium | Security | `util.py` |
| 4.1 | Low | Performance | `geometry_support/bodies_select.py` |
| 4.2 | Medium | Maintainability | multiple |
| 4.3 | Medium | Maintainability | `util.py` |
| 4.4 | Medium | Maintainability | `geometry_support/prep.py` |
| 4.5 | **High** | Test correctness | `tests/test_geometry.py` |
| 4.6 | Medium | Potential Bug | `columns/ring.py` |
| 4.7 | Low | Test coverage | `columns/sky.py` |
| 4.8 | Medium | Standards | `pyproject.toml` |
| 4.9 | Low | Documentation | `CONTRIBUTING.md` |
| 5.1 | High | CI/CD | GCP startup scripts |
| 5.2 | Medium | CI/CD | GCP startup scripts |
| 5.3 | Low | CI/CD | `gcp_geometry_startup.sh` |
| 5.4 | Medium | Security/CI | publish workflows |
| 5.5 | **High** | CI/CD | `publish_to_test_pypi.yml` |
| 5.6 | Medium | CI/CD | `run-all-checks.sh` |
| 5.7 | Low | CI/CD | Sphinx invocations |
| 6.1 | Low | Config | `pyproject.toml` |
| 6.2 | Low | Config | `pyproject.toml` |
| 7.1–7.6 | Low | Minor | various |

## Summary

The package is functional for its one wired-up host (Galileo SSI) but is **not in a releasable state** and violates many of its own `.cursor/rules`. Three issues are critical and should be fixed before anything else: (1) `pyproject.toml` declares `dependencies = ["TODO"]`, which makes `pip install .` / `pip install -e ".[dev]"` impossible — this breaks CI, ReadTheDocs, and any PyPI install; (2) `ruff check src tests` reports **293 errors**, so the lint gate that `environment.mdc` calls the single source of truth is red; (3) the dynamically `exec()`-ed `column/COLUMNS_*.py` files and the `'detailed'` geometry path reference names that do not exist (`col.RING_SUMMARY_DETAILED`, `col.BODY_SUMMARY_DETAILED`, `col.BODYX`), which are latent `AttributeError`s. Pervasive secondary problems: builtin shadowing (`format`, `id`, `type`, `dict`, `min`, `max`), no type annotations anywhere, `print()`/`dbprint()` in library code, exception-based control flow, and committed runtime artifacts.

Top priorities: **fix packaging metadata so the package installs**, **get the lint/type gate green**, and **fix the broken dynamic-exec / detailed-geometry code paths**.

---

## Completed tasks (running log)

Newest first. Each entry is a discrete unit of work landed on `ai_rewrite`; the
per-finding status tags in §1–§10 are the authoritative detail.

- **2026-06-30 — Added generic host-agnostic `cli/` package.** New
  `src/metadata_tools/cli/` package provides `index.py`, `geometry.py`,
  `cumulative.py` (local runners) and `index_cloud.py`, `geometry_cloud.py`,
  `cumulative_cloud.py` (GCP workers). Each thin wrapper loads the host config
  via `_host.py` and delegates to the engine, removing the need for per-host
  entry scripts to duplicate boilerplate. The `sys.path.append('')` shim in each
  `*_cloud.py` is now in one place (`_host.py` / the cloud wrappers) rather than
  scattered across every host.
- **2026-06-30 — Split `index_support.py` into a package.** `index_support.py`
  (623 lines) → `index_support/` package: `table.py` (435 lines, `IndexTable`),
  `process.py` (185 lines, `process_index()`), `key_fns.py` (43 lines, key-function
  helpers), `__init__.py` (27 lines). All files well under the 500-line preferred
  cap. Public import surface unchanged. Analogous to the 2026-06-15
  `geometry_support.py` split. (A prior split was reverted on 2026-06-16 at the
  user's request; this version organises concerns differently.)
- **2026-06-16 — Retagged stale finding statuses (doc-only).** Reconciled three
  findings whose tags lagged reality: §2 builtin shadowing → **RESOLVED** (`ruff
  --select A001,A002` is clean; renames were done in the ruff backlog pass), §2
  UP031 `%`-formatting → **WON'T FIX** (in `extend-ignore`, team opt-out), and §9
  typos → **DEFERRED #111** (the only typos left are in commented-out code that
  #111 removes). After this the non-deferred open list is just four items:
  exception-flow (PARTIAL, done-by-design), templated docstrings (PARTIAL),
  and the two user-decisions — §6 entry-point divergence and §10 PyPI token.
- **2026-06-16 — Enabled bandit + vulture everywhere (§8).** Added `bandit -c
  pyproject.toml -r src -q` and `vulture src tests` steps to the `lint` CI job so
  both security/dead-code scanners run in CI as well as locally (they were already
  on by default in `run-all-checks.sh`). Cleared the findings to make the gate
  green: `# nosec B307` on the deferred `util.replace` eval (issue #110), `# nosec
  B101` on three type-narrowing invariant asserts (`common.Table.write` + two
  `*_cloud.py` workers), and renamed the unused argparse-API arg `option_string` →
  `_option_string`. B101/B307 remain active elsewhere. 224 tests pass; `ruff`,
  `mypy`, `bandit`, `vulture` all clean.
- **2026-06-16 — Filecache routing + exception-flow + issue deferrals (§2).**
  Routed the two remaining raw `open()` sites through `FCPath`:
  `common.write_task_file` now uses `FCPath(task_file).write_text(json.dumps(...))`,
  and `util.append_txt_file` reads-then-rewrites via `path.read_text`/`write_text`
  (removing the `FCPath`→`Path` downcast and the `exists()` pre-check, and working
  for remote paths). Earlier in the session the `_index_one_value` key-function
  lookup was converted from nested `try/except KeyError/AttributeError` to explicit
  `globals().get()`/`getattr(..., None)` (also fixing a swallowed-error bug). The
  src-side import-location finding is closed: `ruff --select I001,PLC0415` is clean
  across `src`; the only in-function imports left are intentional test ones
  (integration-gated SPICE imports, conftest fake-injection order). Finally, every
  finding tracked by a GitHub issue is now tagged `[DEFERRED — issue #n]` (#109,
  #111 flipped from `[OPEN]`; #110/#112/#113 already deferred). 224 hermetic tests
  pass (93.56% cov); `ruff`/`mypy` clean.
- **2026-06-16 — Removed `dbprint` and made the host tests live (§2, §4).**
  Deleted `util.dbprint` (a `print()`-to-stderr debug helper) and its call site in
  `common.Table.write` — the adjacent `logger.info("Writing: %s", ...)` already
  records the filename — plus the now-unused `datetime`/`sys` imports and the two
  `dbprint` test hooks; no `print()` remains in `src/` (§2 → RESOLVED). The
  uncollected GOSSI host tests were moved from
  `src/metadata_tools/hosts/GO_0xxx/tests/` into the normal suite at
  `tests/hosts/GO_0xxx/` (new `tests/hosts/` package, one subpackage per host),
  so `testpaths=["tests"]` now collects them; each carries the `requires_archive`
  marker (§4 → RESOLVED). While there, every residual `unittest.TestCase` test —
  the two moved host modules **and** the pre-existing `tests/test_index.py` /
  `tests/test_geometry.py` — was converted to plain pytest functions and the
  shared helper dropped its unused `unittest.TestCase` parameter, so `import
  unittest` no longer appears under `tests/`. Finally that helper was renamed
  `tests/unittester_support.py` → `tests/archive_support.py` (imported as
  `support`) to stop implying unittest and to describe its `$RMS_METADATA`
  archive role. 224 hermetic tests still pass (93.57% cov); `ruff`/`mypy` clean.
- **2026-06-16 — Tooling decision: `ruff format` is not used.** The project does
  not run `ruff format`; it stays off via the single `ENABLE_RUFF_FORMAT:=false`
  default in `scripts/run-all-checks.sh` (the source of truth). `ruff check` is the
  enforced lint gate. Pre-existing `ruff format --check` drift is expected and must
  not be "fixed" by reformatting. (Also: mypy is now a real gate — see §3/§8.)
- **2026-06-16 — Full `mypy --strict` typing (§3).** Every function in `src` and
  `tests` is now annotated; `mypy src tests` reports zero issues across 67 files.
  Done in dependency order (foundation → engine → hosts → tests) so boundary types
  stay consistent. Docstrings lost their redundant arg/return type info. `py.typed`
  marker created + re-declared in package-data, so the package ships typed. 225
  hermetic tests still pass; `ruff check` stays clean.
- **2026-06-16 — Ruff backlog cleared (§2/§3).** `ruff check src tests` → All
  checks passed (was 157). Auto-fixes + builtin-shadow renames (`format`→`fmt`,
  `dir`/`type`/`id`/`dict`/`min`/`max` →descriptive), test-name CapWords/lowercase,
  `util.PdsTable`→`util.pds_table`, F401/E402 noqa for side-effect & plugin
  imports, and E501 wrapping. Team-opted-out rules in `extend-ignore`.
- **2026-06-16 — Small-issue sweep.** Cleared a batch of low-risk findings with no
  change to table/label output: `get_volume_id` de-duplicated (§1, now
  `geometry_config` re-exports `host_config.get_volume_id`); `raise ... from None`
  (§2); `open(..., encoding="utf-8")` on both raw `open()` calls (§2); `import math`
  hoisted to the top of `util.py` (§2); `MODE_SIZES` hoisted to a module constant
  and the eight `_cat_rows` calls table-driven (§5); the `_format_column`
  `assert len(value) == count` replaced with a `ValueError` (§7); all live-code
  typos fixed (§9); and the Python minimum reconciled to **3.11** across
  `requires-python`, ruff `target-version`, the CI matrix, the `:: 3.10`
  classifier, `CONTRIBUTING.md`, and `how_to.mdc` (§8, user-confirmed drop of 3.10).
  Net ruff on the touched files 44 → 42; 225 hermetic tests still pass (93.6% cov).
  Dead/commented-out code (§1) was **not** deleted but re-validated and catalogued
  with code samples in **issue #111** (the Sun-table lines flagged there as a
  feature decision, not cruft). The local-vs-cloud entry-point divergence (§6) was
  deliberately skipped at the user's request.
- **2026-06-16 — Fixed the correctness/robustness/doc bugs** surfaced by the test
  suite: `add_by_base` carry, `append_txt_file` double-write, `_get_null_value`
  priority, `obs_excluded` short-circuit, `prep_row` per-column override + `target`
  reuse, `prep_row` tuple-tiles `TypeError`, `get_backplane_key` /
  `sclk_format_count` docstrings, `_get_range_mod360` empty input, `_create_index`
  scope, `_index_one_value` dead assert, and the misplaced `tables.py` class
  docstrings. Each pinning test was flipped to assert the corrected behavior; no
  `xfail`s remain. Two items were **not** fixed and filed as GitHub issues:
  `construct_excluded_mask` smells → **issue #109**; the `util.replace` `eval()`
  → **issue #110**. Catalog in `critiques/final_report.md`.
- **2026-06-16 — Reverted the `util.py` / `index_support.py` splits** (user
  request). Both files were restored byte-for-byte to their pre-split contents and
  the helper modules (`util_ranges.py`, `util_textfiles.py`, `index_formats.py`)
  removed; test references and doc notes reverted. Net effect: the geometry split
  and the test suite stand; `util.py` (802) and `index_support.py` (623) are again
  over 500 lines (still under the 1000-line `python.mdc` cap). **Note:** The
  `index_support.py` split was subsequently redone on 2026-06-30 — see completed
  tasks entry above.
- **2026-06-15 — Hermetic unit-test suite to 93.1% coverage** (Plan 2). New
  `tests/conftest.py` import shim + 16 test modules exercise the engine with no
  SPICE and no `$RMS_METADATA`; `pytest --cov=src` now genuinely meets
  `fail_under = 90`. Ten defects pinned by tests (4 strict `xfail`, 6
  characterization). Full catalog in `critiques/final_report.md`. → resolves §4
  (Critical).
- **2026-06-15 — Split `geometry_support.py` into a package** (Plan 1). 1654-line
  module → 10 files < 500 lines each, public import surface and table/label output
  unchanged. → resolves the §1 module-size finding.
- **2026-06-15 — Earlier sessions:** packaging deps (`dependencies=["TODO"]` →
  real deps), `*.lbl` package-data, dangling `py.typed` removed, `column/` de-`exec()`ed
  into a real `columns/` package (40×F821 gone), detailed-geometry `AttributeError`s
  fixed, committed runtime artifacts removed, bandit/vulture enabled. → resolves
  §8 (Critical), §10 (Critical/High), the §1 exec finding, §3 py.typed, §9
  detailed-path finding.

## Finding status legend

Every finding in §1–§10 is tagged:

- **`[RESOLVED]`** — fixed; behavior/lint verified.
- **`[PARTIAL]`** — partly addressed; remainder noted inline.
- **`[TESTED — NOT FIXED]`** — a test pins the bug, but the production code is
  unchanged. (As of 2026-06-16 every such item has been either fixed or filed as
  an issue, so none remain.)
- **`[OPEN]`** — not yet addressed. An open item tracked as a GitHub issue is
  tagged **`[OPEN — issue #n]`**.
- **`[DEFERRED — issue #n]`** — intentionally parked pending a design decision;
  tracked as a GitHub issue rather than fixed inline.
- **`[WON'T FIX]`** — dispositioned as a non-issue (e.g. by-design behavior the
  user confirmed); closed without a code change.

Note: line numbers in findings that cite `geometry_support.py:NNNN` predate the
Plan 1 split; that code now lives in `geometry_support/<module>.py` (the function
names are unchanged).

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
- **§9** — the correctness/robustness bugs are now **fixed** (2026-06-16):
  `_get_null_value` `continue`→`break`, `append_txt_file` double-write, `add_by_base` carry,
  `obs_excluded` short-circuit, `_prep_row` last-column override + `target` reuse, the
  `prep_row` tuple-tiles `TypeError`, `_create_index` `unused`/loop-scope, and the
  `_index_one_value` dead assert. `construct_excluded_mask` is **not** fixed — filed as
  **issue #109** (gridless-backplane decision needed). Full catalog in
  `critiques/final_report.md`.
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

- **[RESOLVED]** **Finding (High):** The `column/COLUMNS_*.py` files masquerade as importable modules (each has top-of-file `import` statements) but are actually loaded via `exec(open(file).read())` in `columns.py:26-28`. They depend on names injected by the exec'ing namespace (`BODIES`, `np`, `util`) that they never import themselves. **Evidence:** `columns.py:24-28`; `ruff check src/metadata_tools/column --select F821` reports 40 undefined-name errors (`COLUMNS_BODY.py:85 BODIES`, `COLUMNS_RING.py:132 np`, `COLUMNS_RING.py:95 util`). **Suggestion:** Convert these into real modules: add the missing `import numpy as np`, `import metadata_tools.util as util`, and an explicit `from metadata_tools.columns import BODIES` (or pass `BODIES` in as a function argument), then replace the `exec()` loop with normal imports or an explicit registry function. This removes the F821 errors and makes the data analyzable by mypy/ruff.
- **[RESOLVED]** **Finding (High):** Module size. `geometry_support.py` is 1654 lines, exceeding the 1000-line cap in `python.mdc` §2. **Evidence:** `geometry_support.py`. **Suggestion:** Split into e.g. `geometry/record.py` (the `Record` class), `geometry/tables.py` (`InventoryTable`/`SkyTable`/`SunTable`/`RingTable`/`BodyTable`/`Suite`), and `geometry/formats.py` (`FORMAT_DICT`/`ALT_FORMAT_DICT`). **Update:** done — split into a `geometry_support/` package of 10 modules (< 500 lines each), output and import surface preserved. (`util.py` at 802 also exceeds 500 but is under the 1000-line cap and remains as a single file. `index_support.py` (623 lines) was split and then reverted on 2026-06-16 at the user's request; it has since been re-split into `index_support/` package: `table.py` 435 lines, `process.py` 185 lines, `key_fns.py` 43 lines — 2026-06-30.)
- **[DEFERRED — issue #112]** **Finding (Medium):** Host config modules are imported as **top-level** modules (`import host_config`, `import index_config`, `import geometry_config`) rather than package-qualified, so code only works when CWD is the host directory. **Evidence:** `index_support.py:11-12`, `cumulative_support.py:9`, `geometry_support/{formats,record,suite,bodies_select}.py`, `GO_0xxx_index.py:34`. **Suggestion:** This is an intentional plugin pattern, but document it explicitly and consider an import shim that adds the host dir to `sys.path` in one place rather than relying on the user's CWD and scattered `sys.path.append('')` calls (`host_init.py:13`, `*_cloud.py`). **Update:** deferred — tracked as **issue #112**. A `pip install`/`pyproject.toml` change alone cannot make `import host_config` resolve (every host defines a same-named module, so they collide as top-level modules); decoupling needs a real mechanism (env-var host selector vs. runtime config registry) and is complicated by `formats.py` building `MISSION_TABLE` from `config` at import time. The separable `sys.path.append('')` GCP shim removal is folded into the same issue. Needs a design decision on the approach before implementation.
- **[DEFERRED — issue #111]** **Finding (Medium):** Dead/commented-out code throughout. **Evidence:** `geometry_support.py:520, 1191-1196, 1359-1362, 1481-1489`; `geometry_config.py:209-225`; `COLUMNS_*` commented column rows; `index_config.py:109, 222, 240`. **Suggestion:** Delete; rely on git history. `python.mdc` §4 forbids history/cruft comments. **Update:** every block was re-validated against the current tree and catalogued (with code samples) in **issue #111**; the Sun-table lines in `suite.py` are flagged there as a feature-disable decision rather than auto-removable cruft.
- **[RESOLVED]** **Finding (Medium):** `get_volume_id()` is duplicated verbatim in `host_config.py:22-33` and `geometry_config.py:177-188`. **Evidence:** both files. **Suggestion:** Define once (e.g. in `host_config`) and have `geometry_config` import it (DRY, `python.mdc` §2). **Update:** **fixed** — `geometry_config` now does `get_volume_id = host_config.get_volume_id` (package-qualified import, no CWD dependency); the duplicate body is gone.

## 2. Best practices alignment

- **[RESOLVED]** **Finding (High):** Builtin shadowing is pervasive, violating `python.mdc` §1. `ruff` counts 13×A002 + 11×A001. **Evidence:** `format` as a variable in `geometry_support.py:405, 723-727, 912-925` and `index_support.py:299, 322, 351, 367-394`; `id` in `util.py:276` and `geometry_support.py:1020`; `type` in `common.py:24-38` and `util.py:63-83`; `dict` in `util.py:244-246, 251-262` and `geometry_config.py:196-207`; `min`/`max` in `unittester_support.py:51`. **Suggestion:** Rename to `fmt`, `obs_id`, `type_`/`index_type`, `mapping`, `min_val`/`max_val`. **Update:** **fixed** — the builtin-shadow renames were completed during the ruff backlog pass (`format`→`fmt`, `dir`/`type`/`id`/`dict`/`min`/`max` → descriptive names). `ruff check src tests --select A001,A002` now reports **All checks passed** (0 violations), so no builtin shadowing remains in `src`/`tests`. (The earlier "remaining shadowing unchanged" note was itself stale; verified clean 2026-06-16.)
- **[RESOLVED]** **Finding (High):** Library code prints to stdout/stderr instead of logging, violating `logging.mdc`. **Evidence:** `util.py:29` (`print(... file=sys.stderr ...)` in `dbprint`), and `common.py:229` calls `util.dbprint(...)` from `Table.write` — a debug line shipped in production. Many `print()` calls also live in tests. **Suggestion:** Delete `dbprint` and its call site; route any needed output through `com.get_logger()` with `%`-style deferred formatting per `logging.mdc` §2. **Update:** **fixed** (2026-06-16) — `util.dbprint` and its call site in `common.Table.write` are deleted (the adjacent `logger.info("Writing: %s", ...)` already records the filename); the now-unused `datetime`/`sys` imports in `util.py` and the two `dbprint` test hooks were removed too. No `print()` remains in library (`src/`) code.
- **[PARTIAL]** **Finding (Medium):** Exception-based control flow instead of explicit checks (`python.mdc` §1). **Evidence:** `index_support.py:214-226` uses nested `try/except KeyError` / `except AttributeError` to look up key functions; `index_support.py:553-557` and `cumulative_support.py:74-77` use `try/except (IndexError|FileNotFoundError)` for normal flow. **Suggestion:** Use `globals().get(fn_name)` / `hasattr(config, fn_name)` and `list(...)` length checks. **Update:** **the key-function lookup is fixed** (2026-06-16) — `IndexTable._index_one_value` now resolves the key function with `globals().get(fn_name)` then `getattr(config, fn_name, None)`, calling it outside any `try`. Besides removing the exception-as-control-flow, this fixes a latent bug: the old code wrapped the `fn(...)` *call* inside the `try`, so a `KeyError`/`AttributeError` raised *inside* a key function was silently swallowed and fell through to a different branch. All three dispatch paths (built-in / config / raw-label) stay covered by `tests/test_index_support.py` and pass. The other two sites are **deliberately left** as `try/except` and are *not* defects: (1) the `FileNotFoundError` blocks (`index_support` IndexTable construction, `cumulative_support` table read) are the pattern `filecache.mdc` explicitly endorses ("prefer try/except `FileNotFoundError` over `exists()` pre-checks"); (2) the `IndexError`-break loop in `_get_column_values` iterates the *actually-parsed* columns of a possibly-incorrect label — `Pds3Table._column_values` is `[None]` + appended columns, and the only public count (`old_lookup('COLUMNS')`) is the *declared* count, which this API exists to cross-check against, so a length-based loop would trade robustness for a count that can diverge on malformed labels.
- **[RESOLVED]** **Finding (Medium):** `raise FileNotFoundError(image_path)` without `from err` discards context (`python.mdc` §2; ruff B904). **Evidence:** `index_config.py:111-112`. **Suggestion:** `raise FileNotFoundError(image_path) from None` (intentional) or `from err`. **Update:** **fixed** — `from None` added (the re-raise is intentional, mapping the original path to a clean error).
- **[RESOLVED]** **Finding (Medium):** `open()` without `encoding=` and bypassing `FCPath`. **Evidence:** `common.py:90` (`open(task_file, "w")`), `util.py:443` (`open(Path(filespec.as_posix()), "a")`). **Suggestion:** Use `FCPath(task_file).open("w")` / `fcpath.open("a")` per `filecache.mdc` §3c, or at minimum pass `encoding="utf-8"`. **Update:** **fixed** (2026-06-16) — both raw `open()` calls now go through `FCPath`. `common.write_task_file` uses `FCPath(task_file).write_text(json.dumps(...), encoding="utf-8")`. `util.append_txt_file` was rewritten to read any existing content (`path.read_text`; `FileNotFoundError` → empty) and `path.write_text(existing + text, encoding="utf-8")` — this removes both the `FCPath`→`Path` downcast (`filecache.mdc` forbids downcasting) **and** the `exists()` pre-check, and keeps remote paths (`gs://`, `s3://`, ...) working since streaming append is unsupported there. Behavior is unchanged: the new-file and existing-file append tests in `tests/test_util_textfile.py` still pass, as does the full suite (224, 93.56% cov).
- **[RESOLVED]** **Finding (Low):** `import math` inside a function body (`util.py:461`); imports not grouped/sorted (26×I001 from ruff). **Update:** **fixed** — `import math` is at the top of `util.py`; `ruff --select I001` (import sort) and `ruff --select PLC0415` (import outside top level) both report **All checks passed** across `src`. No improperly-located imports remain in library code. The only remaining in-function imports are in `tests/` and are **intentional**: `tests/columns/test_columns_integration.py` is `@pytest.mark.integration` and must defer the SPICE-backed `metadata_tools.columns` import out of collection time, and `tests/conftest.py`'s in-fixture imports depend on the fake-module injection order. **Suggestion:** Move all imports to the top in the three sorted groups (`python.mdc` §2); run `ruff check --fix`.
- **[WON'T FIX]** **Finding (Low):** `%`-formatting used where `python.mdc`/UP031 prefer f-strings for *non-logging* string building (20×UP031). **Evidence:** `index_support.py:94`, `common.py:32,38`, etc. **Suggestion:** Convert non-logging `%` formats to f-strings; keep `%`-style only inside `logger.*()` calls. **Update:** **closed as won't-fix** — the team opted out of UP031; it is listed in `[tool.ruff.lint] extend-ignore` (with the other opted-out rules), so `%`-formatting for non-logging string building is allowed by policy and not a gate failure.

## 3. Types and static checks

- **[RESOLVED]** **Finding (High):** Essentially **no type annotations** in the core library, contradicting `python.mdc` §5 ("annotate all function/method parameters and return values") and the `[tool.mypy] strict = true` setting in `pyproject.toml`. **Evidence:** `util.py`, `common.py`, `index_support.py`, `geometry_support.py`, `cumulative_support.py` — only the `*_cloud.py` `process_task` functions are annotated. **Suggestion:** Add annotations module-by-module starting with public entry points (`process_index`, `process_tables`, `create_cumulative_indexes`, `get_args`) and the `Table`/`Record`/`Suite` constructors. Until then `mypy --strict src` cannot pass. **Update:** **fixed** (2026-06-16) — every function in `src` *and* `tests` is now fully annotated; `mypy src tests` (strict) reports **Success, no issues in 67 source files**. Docstrings had their now-redundant arg/return type info stripped. Most-constrained types throughout; `Any` is reserved for oops/SPICE/untyped-lib objects and heterogeneous PDS label dicts, with `cast()`/scoped `# type: ignore[code]` where a value is known narrower or a test intentionally exercises a bad-type edge case. Third-party no-stub deps and the host top-level-import plugin names are handled via `[tool.mypy.overrides]`.
- **[RESOLVED]** **Finding (High):** `py.typed` is declared in packaging (`pyproject.toml [tool.setuptools.package-data] "metadata_tools" = ["py.typed"]`) but the marker file **does not exist**. **Evidence:** `ls src/metadata_tools/py.typed` → not found. **Suggestion:** Either create an empty `src/metadata_tools/py.typed` (only once the package is actually typed) or remove the declaration. **Update:** the dangling entry was first removed; now that the package is fully annotated and `mypy --strict`-clean (see above), an empty `src/metadata_tools/py.typed` marker was created and re-declared in package-data, so the package ships as a typed module.
- **[RESOLVED]** **Finding (High):** `ruff check src tests` → **293 errors** (W291 51, F821 40, PT009 35, I001 26, E501 26, UP031 20, A002 13, W293 12, A001 11, F401 10, …). The lint gate is red, so CI's `lint` job fails. **Evidence:** ruff run, 2026-06-15. **Suggestion:** Triage in this order: auto-fix the 76 fixable (whitespace, import sort, `list()` comprehensions), fix F821 by de-`exec()`-ing the column files (§1), then the naming/format rules. **Update:** **fixed** (2026-06-16) — `ruff check src tests` reports **All checks passed!**. Cleared via auto-fixes, builtin-shadow renames, test-name fixes, F401/E402 noqa for side-effect/plugin imports, and E501 wrapping. A handful of opinionated rules the team opted out of (`RUF005`, `B028`, `SIM102`, `N999`, `UP031`) are in `[tool.ruff.lint] extend-ignore` with rationale comments.
- **[PARTIAL]** **Finding (Medium):** Docstrings exist on most functions (good) but many are wrong or templated — see §9. **Update:** the two pinned doc/contract mismatches are **fixed** (`Record.get_backplane_key` now documents that it returns the key; `util.sclk_format_count` now says `Returns: str`); the docstring typos in §9 remain.

## 4. Testing

(Full detail in `tests_critique.md`.) Summary for this report:

- **[RESOLVED]** **Finding (Critical):** The test suite does not exercise the library. `tests/test_*.py` only read pre-generated `.lbl` files from `$RMS_METADATA`; they never `import metadata_tools`. Coverage of `src/` is effectively ~0%, yet `pyproject.toml` sets `fail_under = 90` and `--cov=src`. **Suggestion:** Add unit tests that import and call the pure functions in `util.py` (`add_by_base`, `rebase`, `sclk_*`, `get_volume_glob`, `_get_range_mod360`) and the formatting logic in `index_support.py`. **Update:** done (Plan 2) — `tests/conftest.py` import shim + 16 hermetic modules bring engine coverage to **93.1%**, above `fail_under = 90`. The SPICE/GCP-only seams (`hosts/*`, `bodies.py`) are excluded from the denominator with documented `omit` entries.
- **[RESOLVED]** **Finding (High):** Host tests under `src/metadata_tools/hosts/GO_0xxx/tests/` are never collected (`testpaths = ["tests"]`), so they are dead. **Suggestion:** Decide whether host tests run in CI; if so add their path to `testpaths`. **Update:** **fixed** (2026-06-16) — the host tests were moved into the collected tree at `tests/hosts/<HOST>/` (`tests/hosts/GO_0xxx/test_index.py`, `test_geometry.py`), under a new `tests/hosts/` package with one subpackage per host. `testpaths = ["tests"]` recurses, so they are now collected. They read the `$RMS_METADATA` holdings, so each carries `pytestmark = pytest.mark.requires_archive` (matching the generic holdings-backed tests) and is excluded from the default run but opted in by `scripts/run-all-checks.sh --integration`. CLAUDE.md updated to the new location. While moving them, the moved tests **and** the pre-existing holdings-backed `tests/test_index.py`/`tests/test_geometry.py` were converted from `unittest.TestCase` classes to plain pytest functions (per `python_testing.mdc`: "new tests should not be `unittest.TestCase`"); the shared `bounds()` helper dropped its unused `unittest.TestCase` parameter, so `import unittest` no longer appears anywhere under `tests/`. The helper module itself was then renamed `tests/unittester_support.py` → `tests/archive_support.py` (imported as `support`) — it no longer relates to unittest, and the new name reflects its `$RMS_METADATA` archive role while avoiding pytest's `test_*.py` collection pattern.

## 5. Performance and resource use

- **[WON'T FIX]** **Finding (Medium):** `module-level mutable global` `task_list = []` in `common.py:50`, mutated by `add_task()` and read by the `task_source()` generator. Not thread-safe and persists across calls. **Evidence:** `common.py:50-78`. **Suggestion:** Document single-threaded use, or encapsulate in a `TaskQueue` object passed explicitly (the cloud workers already pass `task_source=com.task_source`). **Update:** **closed as won't-fix** (user decision, 2026-06-16) — this code is always run single-threaded, so the shared module-level list is intentional and the thread-safety concern does not apply. No change needed.
- **[RESOLVED]** **Finding (Low):** `meshgrids()` rebuilds the `MODE_SIZES` dict on every call (`geometry_config.py:124-135`). **Suggestion:** Hoist to a module constant. **Update:** **fixed** — `MODE_SIZES` is now a module-level constant above `meshgrids()`.
- **[RESOLVED]** **Finding (Low):** `cumulative_support.py:158-181` issues eight nearly identical `_cat_rows(...)` calls. **Suggestion:** Drive from a list of `(TableClass, level)` tuples. **Update:** **fixed** — the eight calls now iterate over a `tables` list; output order is unchanged.

## 6. Maintainability and extensibility

- **[RESOLVED]** **Finding (High):** Two entry points diverge in behavior. `GO_0xxx_geometry.py:50-54` hardcodes `selection="S", exclude=['GO_0999']` while `GO_0xxx_geometry_cloud.py:44-50` reads `config.selection`/`config.exclude`. **Evidence:** both files vs. `geometry_config.py:18-19`. **Suggestion:** Have the local script read from `config` too, so local and cloud stay consistent. **Update:** **fixed** (2026-06-29) — `GO_0xxx_geometry.py` now passes `selection=config.selection, exclude=config.exclude`. Behavior is unchanged (the config values were already `"S"` and `['GO_0999']`); local and cloud paths now share a single source of truth.
- **[DEFERRED — issue #115]** **Finding (Medium):** `*_cloud.py` access the private attribute `worker._data` (`GO_0xxx_index_cloud.py:66-68`, `GO_0xxx_geometry_cloud.py:78-80`). **Suggestion:** Use a public accessor from `rms-cloud-tasks`; relying on `_data` will break on upstream refactors. **Update:** deferred — tracked as **issue #115**. The user identified this as a deeper design flaw: the cloud workers should be driven by the **task queue**, not by command-line arguments. Issue #115 redesigns the worker to take the host type (and paths) from the task data and use no CLI args, which removes the `worker._data` access entirely. Designed jointly with #112/#113/#114.
- **[RESOLVED]** **Finding (Medium):** Class docstrings are misplaced. In `geometry_support.py:1066-1067, 1101-1102, 1131-1132, 1161-1162, 1201-1202` the `"""..."""` string sits **before** the `class` statement, so it is a no-op expression and the classes (`InventoryTable`, `SkyTable`, `SunTable`, `RingTable`, `BodyTable`) have **no docstring**. **Suggestion:** Move each string to the first line inside the class body. **Update:** fixed in `geometry_support/tables.py` — each string is now the first line of its class body, so all five classes have a real docstring.

## 7. Security and robustness

- **[RESOLVED]** **Finding (High):** `eval()` on template-derived strings. **Evidence:** `util.py:210` (`lrep[i] = eval(lrep[i])` inside `replace()`), reachable from column definitions like `util.replacement_fn("defs.RING_SYSTEM_RADII", defs.BODYX)` (`COLUMNS_RING.py:94-96`). `security.mdc` flags `eval`. **Suggestion:** Replace with an explicit lookup (e.g. resolve `dict_name["key"]` via `getattr(defs, name)[key]`) rather than evaluating arbitrary expressions. **Update:** **fixed (2026-06-29)** — `eval()` replaced with `_resolve_dict_ref()`, a private function that parses the `defs.<ATTR>["<key>"]` pattern with a regex and performs a safe `getattr(defs, attr_name)[key]` lookup. Only the `defs` module is accessible; any other module name raises `ValueError`. The `nosec B307` suppressor is gone. Two new error-path tests cover the unknown-module and unrecognized-pattern cases. 226 hermetic tests pass (93.64% cov); `ruff`/`mypy` clean.
- **[RESOLVED]** **Finding (Medium):** `assert` used for runtime validation (disabled under `python -O`). **Evidence:** `index_support.py:232` (`assert value is not None, ...`) and `index_support.py:376` (`assert len(value) == count`). **Suggestion:** Raise explicit exceptions. Note also that line 232's assert is effectively dead — line 229-230 already replaces `None` with `nullval`. **Update:** **both fixed** — the `_index_one_value` assert (line 232) raises `ValueError` when no null constant is defined, and the `_format_column` `assert len(value) == count` (line 376) now raises a `ValueError` reporting the column name and the expected vs. actual count.
- **[DEFERRED — issue #114]** **Finding (Low):** GCP startup scripts embed a service-account email and personal bucket paths. **Evidence:** `gcp_index_config.yml:5`, `gcp_index_startup.sh:24-26`. Not secrets, but couples published code to one person's infra. **Suggestion:** Parameterize via env vars. **Update:** deferred — folded into **issue #114** (relocating the GCP/cloud deployment files out of the package), since parameterizing the hardcoded infra is a natural companion to moving those files into a common, non-installed directory.

## 8. Dependencies and tooling

- **[RESOLVED]** **Finding (Critical):** `pyproject.toml` runtime dependencies are a placeholder: `dependencies = ["TODO"]` (line 11-12), plus `description`, `keywords`, and `[project.scripts]` are all `TODO`. **Update:** real runtime deps, `description`, and `keywords` are filled in; `requirements.txt` reduced to `-e .[dev,cloud]`; pyroma rates the metadata 10/10. (`[project.scripts]` remains commented — see §10.) This makes `pip install .` and `pip install -e ".[dev]"` fail (pip tries to resolve a package named `TODO`). **Evidence:** `pyproject.toml:8,12,21,89`; the real deps live only in `requirements.txt`/`requirements-cloud.txt`, contradicting `dependency_management.mdc` §1 (pyproject is the single source of truth). **Suggestion:** Move the real runtime deps (numpy, rms-oops, rms-filecache, rms-pdslogger, rms-julian, rms-pdsparser, rms-cloud-tasks, rms-pdstable, rms-vicar, rms-pdstemplate, rms-textkernel, fortranformat, cspyce, json-stream) from `requirements.txt` into `[project.dependencies]` with minimum versions; reduce `requirements.txt` to `-e .`.
- **[RESOLVED]** **Finding (Medium):** CI Python matrix (`run-tests.yml`: 3.10–3.13) matches `requires-python = ">=3.10"`, but `python.mdc` says "Minimum Python version 3.11" and `[tool.ruff] target-version = "py310"`. **Suggestion:** Reconcile the three; pick one minimum and apply it to `requires-python`, ruff `target-version`, and the rule text. **Update:** **fixed** — reconciled to **3.11** (the authoritative `python.mdc` value): `requires-python = ">=3.11"`, ruff `target-version = "py311"`, the CI matrix drops 3.10, the `:: Python :: 3.10` classifier is removed, and `CONTRIBUTING.md` / `how_to.mdc` now say 3.11+. Dropping 3.10 support was confirmed with the user.
- **[RESOLVED]** **Finding (Medium):** `run-tests.yml` lint job runs `mypy src tests`, but the local `scripts/run-all-checks.sh` defaults `ENABLE_MYPY` inconsistently (the docstring says default false, the code sets it true) — and mypy cannot currently pass (§3). **Suggestion:** Make CI and the script enable exactly the same gates (`environment.mdc` §2), and don't enable mypy in CI until the code is annotated. **Update:** the "mypy cannot pass / don't enable until annotated" blocker is **resolved** — `mypy src tests` is now strict-clean (§3), so mypy is a legitimate gate in both CI and the script. **`ruff format` is intentionally NOT part of the check suite** (team decision): it stays disabled via the single `ENABLE_RUFF_FORMAT:=false` default at the top of `run-all-checks.sh` (the source of truth), so the pre-existing `ruff format --check` drift is **not** a gate failure and should not be "fixed" with a reformat. The `ENABLE_MYPY` docstring nit (the comment says "default: false" while the code sets `:=true`) is **closed as won't-fix** (user decision, 2026-06-16) — not worth a change. Otherwise this finding is resolved.
- **[RESOLVED]** **Finding (Low):** Stale tool config: `[tool.bandit]`/`[tool.vulture]` are commented out while `run-all-checks.sh` references them; `flake8` is still in `requirements.txt` though ruff replaces it. **Suggestion:** Remove `flake8`; keep the commented tool blocks only if intended to be enabled soon. **Update:** `[tool.bandit]`/`[tool.vulture]` are now enabled with real config; the `flake8` cleanup is **verified resolved** — `requirements.txt` is reduced to `-e .[dev,cloud]` and no `flake8` reference remains in any `.txt`/`.toml`/`.cfg`/`.sh`. **bandit and vulture are now enabled *everywhere*** (2026-06-16): the `lint` CI job (`run-tests.yml`) gained `bandit -c pyproject.toml -r src -q` and `vulture src tests` steps, matching the `ENABLE_BANDIT`/`ENABLE_VULTURE` defaults in `run-all-checks.sh`, so both run in CI as well as locally. Making the gate green required surgical, documented suppressions: `# nosec B307` on the `util.replace` `eval` (tracked by **issue #110**), `# nosec B101` on three type-narrowing invariant asserts (`common.Table.write`, the two `*_cloud.py` workers), and an underscore rename of the unused argparse-API arg `option_string` → `_option_string` in `common.py`. B101/B307 stay active everywhere else.

## 9. Technical debt and risk

- **[RESOLVED]** **Finding (High):** Latent `AttributeError`s on the geometry `'detailed'` path. `Record.__init__` (`geometry_support.py:167-172`) references `col.RING_SUMMARY_DETAILED` and `col.BODY_SUMMARY_DETAILED`, but `COLUMNS_RING.py`/`COLUMNS_BODY.py` define `RING_DETAILED_DICT`/`BODY_DETAILED_DICT` (and `RING_SUMMARY_DICT`/`BODY_SUMMARY_DICT`) — the `*_SUMMARY_DETAILED` names do not exist. Likewise `geometry_support.py:215-216` uses `col.BODYX`, which is never defined in the `columns` namespace (only `defs.BODYX` exists). **Evidence:** grep of `col.` references vs. names defined in `column/`. **Suggestion:** Fix the names (`col.RING_DETAILED_DICT`, `col.BODY_DETAILED_DICT`, `defs.BODYX`) and add a test that constructs a detailed `Record` so the path is exercised.
- **[RESOLVED]** **Finding (High):** Logic bug in `IndexTable._get_null_value` (`index_support.py:291-295`): the loop assigns `nullval := old_lookup(key)` and `continue`s on truthy, so it returns the null value of the **last** matching key rather than the first; `continue` should be `break`. **Evidence:** lines 291-295. **Suggestion:** `break` on first truthy value. **Update:** **fixed** (`continue`→`break`); verified by `test_index_support.py::test_get_null_value_prefers_highest_priority_key` and companions.
- **[RESOLVED]** **Finding (High):** `_create_index` "unused columns" accumulation never works: `unused = None` is reset **inside** the per-directory `walk` loop (`index_support.py:536`), and `logger.close(force=True)` plus the task-file write are also inside the loop (lines 562-569). **Evidence:** indentation at 536/562-569. **Suggestion:** Initialize `unused` before the loop; move the close/write/warn after it. **Update:** **fixed** exactly as suggested; `test_index_support.py::test_create_index_processes_each_volume` now asserts a single `logger.close` and the cross-volume `unused` intersection.
- **[DEFERRED — issue #109]** **Finding (Medium):** `_construct_excluded_mask` (`geometry_support.py:872-879`) has unreachable code: `if np.any(excluded): return excluded` precedes `if np.all(excluded): return True` (all-True implies any-True), and the `#!!!!` comment admits the gridless case is unhandled. **Suggestion:** Resolve the gridless-backplane TODO and remove the dead branch. **Update:** **not fixed** — filed as **issue #109** (needs an upstream gridless-backplane decision). Now lives in `geometry_support/masks.py`; behavior pinned by `tests/test_geometry_masks.py`. The issue documents all of the smells (dead branch, mixed return type, gridless handling, sentinel/early-return inconsistency, `ignore_shadows` default mismatch).
- **[RESOLVED]** **Finding (Medium):** `_prep_row` reuses the loop variable `target` as both the function parameter and a per-column local (`geometry_support.py:710`), and builds the `override` dict (lines 736-739) from whatever `null_value`/`valid_minimum`/`valid_maximum` happened to survive the last column iteration. **Suggestion:** Use distinct names and build the override per column. **Update:** **fixed** in `geometry_support/prep.py` — a column-local `col_target` no longer clobbers the `target` parameter, and one override dict is built per column; `test_geometry_prep.py::test_override_is_built_per_column` asserts the per-column values.
- **[RESOLVED]** **Finding (High):** `add_by_base` (`util.py:284-301`) drops a carry. When the carry into a position plus that position's `(x_digit + y_digit) % base` equals `base`, the result digit is left equal to `base` and the extra carry is never propagated. **Evidence (reproduced):** `add_by_base([9,9],[0,1],[10,10])` returns `[0, 10, 0]`; the correct base-10 result is `[1, 0, 0]`. This feeds `_spacecraft_clock_stop_count_from_label` (`host_config.py:88`), so a stop SCLK can be malformed for exposures that land on a tick boundary. **Suggestion:** add the incoming carry before taking `% base`, or re-normalize digits in a final carry pass; add a unit test covering the chained-carry case. **Update:** **fixed** with a running carry; `test_util_math.py::test_add_by_base_propagates_chained_carry` now asserts `[1,0,0]`.
- **[RESOLVED]** **Finding (Medium):** `append_txt_file` (`util.py:417-444`) writes the file when it doesn't exist (line 423-424) but does **not** `return`, then falls through and appends again — duplicating content on first write. **Evidence (reproduced):** appending `['lineA','lineB']` to a new path yields `lineA\nlineB\nlineA\nlineB\n`. **Suggestion:** `return` after the `write_txt_file` call. **Update:** **fixed** (`return` added); verified by `test_util_textfile.py::test_append_to_new_file_writes_content_once`.
- **[RESOLVED]** **Finding (Medium; newly identified):** `prep_row`'s multiple-tile-set path (when `tiles` is a `tuple`) recurses passing `primary`/`target`/… positionally, but those parameters are keyword-only (after `*`), so the call always raises `TypeError`. The detailed multi-tile path is therefore dead. Predates the Plan 1 split. **Suggestion:** pass those arguments by keyword in the recursion. **Update:** **fixed** — the recursive calls now pass keyword arguments (and forward `no_mask`/`no_body`); `test_geometry_prep.py::test_multiple_tile_sets_tuple_emits_a_row_per_set` asserts the path produces rows.
- **[DEFERRED — issue #111]** **Finding (Low):** Typo `'Mulitple index files found'` (`geometry_support.py:1279`) and many docstring typos (`messaage`, `degugging`, `occurence`, `exluded`, `dicstionary`, `corresopnding`). **Update:** every typo in **live code** is fixed — `Multiple` (suite.py), `Build`/`dictionary` (suite.py ×2), `occurrence`/`excluded` (bodies_select.py), `corresponding` (index_support.py), and `message`/`debugging`/`Message` (util.dbprint docstring). The only typos left (`implemnt`, `supprted`) live solely inside commented-out blocks tracked by **issue #111**; they will be removed together with that dead code, so the remainder of this finding is deferred to #111.

## 10. Packaging and distribution

- **[RESOLVED]** **Finding (Critical):** Non-Python package data will be missing from the wheel. The runtime `exec()`-loads `column/COLUMNS_*.py` and reads `templates/*.lbl` and `hosts/*/templates/*.lbl`, but `[tool.setuptools.package-data]` lists only `py.typed`. **Evidence:** `pyproject.toml:` package-data block; `defs.py:12-13` (`COLUMN_DIR`, `GLOBAL_TEMPLATE_PATH`), `label_support.py`. **Suggestion:** Add `"*.lbl"` (and confirm `*.py` data) to package-data, or use `include-package-data = true` with a `MANIFEST.in`. Verify with `python -m build` then inspect the wheel. **Update:** `templates/*.lbl` declared for `metadata_tools` and `hosts.GO_0xxx`; the column files ship as a real package; all 12 templates verified present in wheel + sdist.
- **[RESOLVED]** **Finding (High):** Generated runtime artifacts are committed under `hosts/GO_0xxx/`: `metadata-*-job.db` (SQLite), `metadata-*_in_queue_original.json`, `index_tasks.json`/`geometry_tasks.json`/`cumulative_tasks.json`, `cprofile.txt` (1161 lines of profiler output), `log.txt` (639 lines). **Evidence:** `git ls-files`. **Suggestion:** Remove from version control and add patterns to `.gitignore`; they would otherwise ship in the sdist.
- **[DEFERRED — issue #113]** **Finding (Medium):** `[project.scripts]` is commented out (`pyproject.toml:113-114`), so there are no console entry points; users must run host scripts by path. **Suggestion:** Decide whether to expose CLIs and wire them up, or document the by-path invocation. **Update:** deferred — tracked as **issue #113**. The console-entry-point concept needs design first: a **single top-level program** that takes the host as a command-line argument (e.g. `metadata-tools index GO_0xxx ...`), not one script per host. That design is coupled to **issue #112** — the host argument becomes the mechanism for resolving "the config for host X" at runtime, replacing the CWD-coupled top-level `import host_config`. Relatedly, **issue #114** tracks moving the GCP/cloud deployment files out of the `hosts/` package into a higher-level common directory that need not ship in the pip-installed package.
- **[OPEN]** **Finding (Low):** PyPI publish uses a long-lived `PYPI_API_TOKEN` (`publish_to_pypi.yml`). **Suggestion:** Prefer PyPI Trusted Publishers (OIDC) per modern packaging guidance.

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
