# Final Report — Full-Codebase Analysis

**Generated:** 2026-07-08
**Branch:** `jns-updates-claude`
**Method:** Three parallel agents each read every file in the repository (source, tests,
docs, cloud scripts, CI workflows, rule files) and produced the three sub-reports.
This report synthesises those findings and provides a single prioritised action list.

---

## Overall health

The package has improved substantially since its initial state. The most dangerous
problems — broken packaging (`dependencies = ["TODO"`), missing wheel data, the
`exec()`-loaded column files, 293 ruff errors, zero test coverage, and the
SPICE-dependent import-time side effects — were all resolved in earlier sessions
(documented in `code_critique.md §2026-06-15 / §2026-06-16` completed tasks).

As of 2026-07-08 the pipeline is **functional** for Galileo SSI (`GO_0xxx`), test
coverage is 93.6 %, `ruff check` and `mypy --strict` both pass, and the Sphinx build
passes with `-W`. **However, the package is not yet production-ready** because:

1. The user guide actively instructs users to run scripts that do not exist
   (`python GO_0xxx_index.py` from the host directory) while hiding the seven
   console scripts that actually exist.
2. Several standards violations and one weak CI configuration remain open.
3. Three GitHub-tracked deferred issues (#109, #111, #115) still affect correctness,
   cleanliness, and cloud-worker reliability.

The three sub-reports and this document share a finding numbering scheme:

- **CODE-§n.m** — finding in `code_critique.md`
- **TEST-§n.m** — finding in `tests_critique.md`
- **DOC-§n** — finding in `documentation_critique.md`

---

## Cross-cutting themes

These issues span more than one sub-report and should be resolved together:

### Theme A — Console scripts vs. old-style per-host scripts

The seven console scripts (`metadata-index`, `metadata-geometry`, `metadata-cumulative`,
`metadata-index-cloud`, `metadata-geometry-cloud`, `metadata-cumulative-cloud`,
`metadata-task-list`) are correctly wired in `pyproject.toml:116-123`, but:

- The user guide *installation* section says "The package does not install console
  scripts" (DOC-C2).
- All user guide *example* sections instruct users to `cd src/metadata_tools/hosts/GO_0xxx`
  and run `python GO_0xxx_*.py` (DOC-H6).
- The `cumulative_cloud.py` module docstring says "GCP runs are not yet working"
  (CODE-§7.7) — stale since commit `1f334bc`.
- The per-host legacy `GO_0xxx_*_cloud.py` scripts still have `sys.path.append('')`
  shims (CODE-§3.2) that are now handled by `cli/`.

Fix together: update the user guide (DOC fix 2 and fix 7), update `cumulative_cloud.py`
docstring (CODE-§7.7), and remove or quarantine legacy per-host entry scripts.

### Theme B — `Args:` → `Parameters:` docstring format

Both `cli/_host.py::run_cloud_worker` (CODE-§2.10, DOC-H5) and
`tests/archive_support.py` (CODE-§7.2) use `Args:` instead of the project-mandated
`Parameters:`. Fix both in the same pass.

### Theme C — Missing `filterwarnings = ["error"]`

`pyproject.toml [tool.pytest.ini_options]` is missing `filterwarnings = ["error"]`
(TEST-§16.3 / TEST-§22.1, CODE-§4.8). This is a one-line fix that surfaces any
unhandled warnings in the test suite.

### Theme D — Sphinx nitpicky mode not enforced

`sphinx-build` is run with `-W` (warnings-as-errors) but not `-n` (nitpicky), both
locally (`scripts/run-all-checks.sh`) and in CI (`run-tests.yml`) (CODE-§5.7). The
stale cross-references in `dev_guide_support_subsystem.rst` (DOC-C1) only surface
under `-n`. Add `-n` to both places and fix the cross-references to make the combined
`-W -n` gate pass.

---

## Open findings by priority

### CRITICAL — Fix before next PR merge

#### CODE-§5.5 — `publish_to_test_pypi.yml` references non-existent action versions

**File:** `.github/workflows/publish_to_test_pypi.yml`

`actions/checkout@v6` and `actions/setup-python@v6` do not exist; current stable is
`v4`. This workflow will fail on every invocation.

**Fix:**
```yaml
uses: actions/checkout@v4
uses: actions/setup-python@v4
```

---

#### DOC-C1 — Stale cross-references cause `sphinx-build -n` failures

**File:** `docs/dev_guide/dev_guide_support_subsystem.rst:29-33`

The RST cross-references `:func:`~metadata_tools.common.add_task``,
`:func:`~metadata_tools.common.write_task_file``, and
`:func:`~metadata_tools.common.task_source`` point to functions that do not exist in
`metadata_tools.common`. They live in `metadata_tools.task_list_support`. Under
`sphinx-build -n` these emit unresolved-reference warnings; combined with `-W` they
become errors.

**Fix (in `dev_guide_support_subsystem.rst`):**

1. Run `grep -n "def " src/metadata_tools/task_list_support.py` to see the actual
   function names.
2. Replace the three stale `:func:` cross-references with the correct ones pointing to
   `metadata_tools.task_list_support`.
3. Also remove any claim in the `common.py` bullet that it contains cloud-task plumbing
   (that responsibility has moved to `task_list_support.py`).

After fixing, run `sphinx-build -W -n -b html docs /tmp/sphinx-out` and confirm zero
warnings.

---

#### DOC-C2 — User guide says "The package does not install console scripts" — opposite of truth

**File:** `docs/user_guide/user_guide_installation.rst:137-154`

Current text instructs users to `cd src/metadata_tools/hosts/GO_0xxx` and run
`python GO_0xxx_index.py`. This is wrong: the package installs seven console scripts.

**Fix:** Replace lines 137-154 with:

```rst
Running the programs
====================

Installing the package registers seven console scripts. Each takes ``HOST_ID``
(e.g. ``GO_0xxx``) as its first argument and can be run from any working
directory:

.. code-block:: text

   metadata-index HOST_ID [options] volume_tree metadata_tree output_tree
   metadata-geometry HOST_ID [options] metadata_tree output_tree
   metadata-cumulative HOST_ID [options] cumulative_dir

   metadata-index-cloud HOST_ID [options] ...
   metadata-geometry-cloud HOST_ID [options] ...
   metadata-cumulative-cloud HOST_ID [options] ...
   metadata-task-list HOST_ID tree_dir --output FILE

See the per-program chapters for the full option reference.
```

Also update every example section that uses `python GO_0xxx_*.py` (see DOC-H6 below).

---

#### TEST-§2.4 / CODE-§4.5 — `test_geometry_cumulative` is dead code

**File:** `tests/test_geometry.py:34`

```python
def test_geometry_cumulative() -> None:
    return   # function exits here; all code below is unreachable
    ...
```

This test will never fail or assert anything. It provides false confidence.

**Fix:**
```python
def test_geometry_cumulative() -> None:
    pytest.skip('Not yet implemented: cumulative geometry table validation')
```

---

### HIGH — Fix in the current sprint

#### TEST-§16.3 / CODE-§4.8 — Missing `filterwarnings = ["error"]`

**File:** `pyproject.toml`, `[tool.pytest.ini_options]`

Per `python_testing.mdc §4`, warnings that reach the test runner should surface as
failures. Currently they are silently swallowed.

**Fix:**
```toml
filterwarnings = [
  "error",
  # oops/polymath may emit NumPy deprecation warnings we cannot control:
  "ignore::DeprecationWarning:oops",
  "ignore::DeprecationWarning:polymath",
]
```

After adding, run the full suite. For each new failure, either fix the source or add a
narrowly scoped ignore with a comment.

---

#### CODE-§5.1 — GCP startup scripts clone from feature branch `jns-updates-claude`

**File:** `cloud/gcp_common_startup.sh`

```bash
git clone -b jns-updates-claude --single-branch https://github.com/SETI/rms-metadata-tools.git
```

This clones a work-in-progress branch. Any GCP worker created from this script runs
whatever code is on that branch at clone time — not `main`.

**Fix (before any production run):**
```bash
git clone --branch main --single-branch https://github.com/SETI/rms-metadata-tools.git
```

Consider using a pinned release tag for reproducibility.

---

#### CODE-§5.2 — GCP startup scripts run `pip install -r requirements.txt` which contains `-e .`

**Files:** All three GCP startup scripts (index, geometry, cumulative)

`requirements.txt` contains `-e .[dev,cloud]`. On a GCP instance there is no editable
install; the `-e` flag is inappropriate and may fail or produce an unexpected install.

**Fix:** Replace `pip install -r requirements.txt` with:
```bash
pip install ".[cloud]"
```

---

#### CODE-§2.1 — `.exists()` used as pre-flight check (violates `filecache.mdc`)

**Rule:** `filecache.mdc` — prefer `try/except FileNotFoundError` over `.exists()`.

**Location 1:** `src/metadata_tools/label_support.py:34`
```python
if not filepath.exists():
    return
```
**Fix:** Wrap the body of the function (the `PdsTemplate()` construction and
`template.write()` call) in `try: ... except FileNotFoundError: return`.

**Location 2:** `src/metadata_tools/index_support/table.py` — `self.primary_index_label_path.exists()` check
**Fix:** Replace the `.exists()` guard with `try: ... except FileNotFoundError` around
the code that reads the primary index label path.

---

#### CODE-§2.2 — `logger.error(traceback.format_exc())` instead of `logger.exception()`

**File:** `src/metadata_tools/geometry_support/suite.py:97`

**Rule:** `logging.mdc` — inside an `except` block, use `logger.exception()` which
automatically captures the current exception and traceback.

**Fix:**
```python
# BEFORE:
import traceback
...
except FileNotFoundError:
    logger.error(traceback.format_exc())

# AFTER (also remove `import traceback` at top if no other usage):
except FileNotFoundError:
    logger.exception('Failed to load index for %s', self.volume_id)
    return
```

---

#### DOC-H1 — `src/metadata_tools/__init__.py` module docstring is completely stale

The package docstring (lines 4-84) references old per-host entry scripts that no longer
exist, uses `####` RST headers inside a Python docstring (invalid Google style), and
refers to `geometry_support.py` as a single file (it is now a package).

**Fix:** Replace the entire docstring content with a concise Google-style description:

```python
"""PDS Ring-Moon Systems Node metadata table generator.

``rms-metadata-tools`` generates PDS3 index, geometry, and cumulative metadata
tables (and their PDS3 labels) for planetary science data collections.

Three stages run in order for each collection:

1. **Index** — supplemental index columns sourced from PDS labels
   (``metadata-index HOST_ID ...``).
2. **Geometry** — geometric quantities computed from SPICE via ``oops``
   (``metadata-geometry HOST_ID ...``).
3. **Cumulative** — per-volume table concatenations across a volume tree
   (``metadata-cumulative HOST_ID ...``).

Per-collection configuration lives in
``src/metadata_tools/hosts/<HOST>/`` (e.g. ``GO_0xxx/`` for Galileo SSI).
"""
```

---

#### DOC-H2/H3 — `geometry_support` package and its 9 submodules lack module docstrings

**Files:** `src/metadata_tools/geometry_support/__init__.py` and all 9 submodules
(`bodies_select.py`, `masks.py`, `prep.py`, `formatting.py`, `formats.py`,
`record.py`, `tables.py`, `suite.py`, `process.py`)

Each has only a `#`-style banner comment; `ast.get_docstring()` returns `None`, so
autodoc renders blank module descriptions.

**Fix:** Insert a one-sentence `"""..."""` module docstring immediately after the `#`
banner and before the first `import` in each file. Use the banner text as source
material. Example:
```python
# geometry_support/formats.py - Geometry column format dictionaries.
################################################################################
"""Master format dictionaries (FORMAT_DICT, ALT_FORMAT_DICT) for geometry columns."""
```

---

#### DOC-H6 — All user guide example sections use obsolete `python GO_0xxx_*.py` syntax

**Files:** `docs/user_guide/user_guide_examples.rst`, `user_guide_index.rst`,
`user_guide_geometry.rst`, `user_guide_cumulative.rst`, `user_guide_cloud.rst`

Every example instructs users to `cd src/metadata_tools/hosts/GO_0xxx` and run
`python GO_0xxx_index.py` etc. No such scripts exist in the installed package.

**Fix:** In each file, replace:
- `cd src/metadata_tools/hosts/GO_0xxx` → remove (not needed)
- `python GO_0xxx_index.py ...` → `metadata-index GO_0xxx ...`
- `python GO_0xxx_geometry.py ...` → `metadata-geometry GO_0xxx ...`
- `python GO_0xxx_cumulative.py ...` → `metadata-cumulative GO_0xxx ...`
- `<HOST>_index.py` / `<HOST>_geometry.py` / `<HOST>_cumulative.py` in prose →
  `metadata-index HOST_ID` / `metadata-geometry HOST_ID` / `metadata-cumulative HOST_ID`
- `*_cloud.py` counterparts → the corresponding console scripts

---

#### DOC-H7 — `dev_guide_layout.rst` source tree omits core modules

**File:** `docs/dev_guide/dev_guide_layout.rst:28-43`

Missing from the source tree listing: `cli/` (7 modules + `_host.py`),
`task_list_support.py`, `config.py`, `_version.py`. Also shows `index_support.py`
as a single file when it is now a package (`index_support/`).

**Fix:** Update the `.. code-block:: text` block for `src/` to include all of the above.
Run `ls src/metadata_tools/` and `ls src/metadata_tools/cli/` to verify current layout
before editing. Also update the `common.py` inline description to remove "task plumbing"
(that moved to `task_list_support.py`).

---

#### CODE-§5.6 / CODE-§5.7 — CI gate gaps

**5.6 — `ruff format --check` not run in CI:**
`ENABLE_RUFF_FORMAT=false` by default in `scripts/run-all-checks.sh`, so formatting
drift is never caught. Either enable it or document explicitly why it is excluded.

> **Note:** The code critique documents this as a team decision (ruff format is
> intentionally not a gate). The documentation critique found a contradiction in
> `dev_guide_conventions.rst` — that contradiction should be resolved: the conventions
> chapter should match the actual team policy (format is NOT gated).

**5.7 — Sphinx not built with `-n` in CI:**
Add `-n` to `SPHINXOPTS` in both `scripts/run-all-checks.sh` and
`.github/workflows/run-tests.yml`:
```
SPHINXOPTS="-W -n"
```
This catches unresolved cross-references (like DOC-C1) automatically.

---

#### TEST-§2.1 — `config.py` error paths not tested

**File:** `src/metadata_tools/config.py` — `current_host_id()`, `get_host_config()`,
`get_index_config()`, `get_geometry_config()` all raise `RuntimeError` when no host is
registered. None of these paths are tested.

**Fix:** Create `tests/test_config.py`:
```python
import types
import pytest
import metadata_tools.config as cfg


def _clear_config(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_set_current_registers_all_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    host = types.ModuleType('host')
    idx = types.ModuleType('idx')
    geom = types.ModuleType('geom')
    cfg.set_current(host_id='X', host_config=host, index_config=idx,
                    geometry_config=geom)
    assert cfg.current_host_id() == 'X'
    assert cfg.get_host_config() is host
    assert cfg.get_index_config() is idx
    assert cfg.get_geometry_config() is geom
```

**Important:** Use `monkeypatch` (not direct assignment) so the config is restored
after each test — the conftest installs a fake host at module-import time and must
remain in place for other tests running in the same worker.

First, verify the actual RuntimeError message by reading `config.py`; update `match=`
patterns to match exactly.

---

#### TEST-§3.1 — `exists_true` fixture duplicated in two test files

**Files:** `tests/test_geometry_masks.py:14-17` and `tests/test_geometry_prep.py:14-17`

Both define an identical fixture:
```python
@pytest.fixture
def exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oops.Body, 'exists', staticmethod(lambda name: True))
```

**Fix:**
1. Add the fixture to `tests/conftest.py` (import `oops` at the top if not already there).
2. Delete both local definitions.
3. Verify: `pytest tests/test_geometry_masks.py tests/test_geometry_prep.py --collect-only -q`

---

#### TEST-§12.1 — Exception assertions missing `match=`

**File:** `tests/test_index_support.py` — `test_indextable_init_supplemental_missing_primary_raises`

```python
with pytest.raises(FileNotFoundError):   # no match= — type only
    IndexTable(...)
```

Per `python_testing.mdc §7`, always assert on exception message content.

**Fix:**
```python
with pytest.raises(FileNotFoundError, match='No primary index for GO_0001'):
    IndexTable(...)
```

Then run `grep -n 'pytest.raises(' tests/*.py tests/**/*.py | grep -v 'match='` and add
`match=` to every remaining unguarded `pytest.raises` call.

---

### MEDIUM — Schedule within the next few sessions

#### CODE-§3.1 — Module-level SPICE-dependent code

**Files:** `src/metadata_tools/bodies.py` (runs `BODIES = get_bodies(defs.BODY_NAMES)` at
import time), `src/metadata_tools/columns/body.py` (builds dicts at module level over
`BODIES`)

Any test that imports these modules triggers the SPICE body registry. The `conftest.py`
works around this with a fake stub that must be kept in sync by hand.

**Fix:** Lazy initialization — replace module-level execution with a `get_bodies_registry()`
function that is called once and cached:

```python
# bodies.py
_BODIES: dict[str, Any] | None = None

def get_bodies_registry() -> dict[str, Any]:
    global _BODIES
    if _BODIES is None:
        _BODIES = _build_bodies(defs.BODY_NAMES)
    return _BODIES
```

This removes the import-time side effect and makes the conftest stub unnecessary.

---

#### CODE-§2.3 — Mutable module-level globals

**`src/metadata_tools/common.py`:**
```python
task_list: list[dict[str, Any]] = []
```
This list is mutated by `add_task()` and cleared between runs. Under `pytest-xdist`
parallel workers it is not thread-safe. At minimum document the single-threaded
contract; ideally encapsulate in an explicit `TaskQueue` passed to callers.

**`src/metadata_tools/defs.py`:**
```python
TRANSLATIONS: dict[str, str] = {}
```
Document who populates this and when, or replace with an explicit parameter.

---

#### CODE-§2.4 — `assert` used for runtime validation

**File:** `src/metadata_tools/common.py:239`
```python
assert table_type is not None  # nosec B101
```
`assert` is stripped by Python's optimizer (`-O`). On cloud workers this could silently
bypass the guard.

**Fix:**
```python
if table_type is None:
    raise ValueError('table_type must not be None')
```

---

#### CODE-§2.6 — `locals()` used for dynamic attribute lookup

**File:** `src/metadata_tools/geometry_support/record.py:~207`
```python
locals()['link_' + link]
```
`locals()` is not reliable in all Python implementations and mypy cannot type-check it.

**Fix:** Replace with an explicit dict:
```python
_link_handlers: dict[str, Callable[..., Any]] = {
    'ring': link_ring,
    'body': link_body,
    # ...
}
_link_handlers[link](...)
```

---

#### CODE-§2.9 — Backwards-compatibility alias `resolve_task_file`

**File:** `src/metadata_tools/cli/_host.py:87-89`

```python
def resolve_task_file(host_dir: Path) -> None:
    """Alias for :func:`resolve_host_paths`; kept for backwards compatibility."""
    resolve_host_paths(host_dir)
```

`python.mdc` forbids backwards-compatibility code without explicit request. The `cli/`
package is new and has no published callers.

**Fix:** Run `grep -r 'resolve_task_file' src/ tests/`; update any callers to use
`resolve_host_paths` directly; delete `resolve_task_file`.

---

#### CODE-§2.10 / DOC-H5 — `Args:` instead of `Parameters:` in `cli/_host.py`

**File:** `src/metadata_tools/cli/_host.py:173`

The `run_cloud_worker` docstring uses `Args:` instead of the project-mandated
`Parameters:`. Also fix `tests/archive_support.py` which has the same issue.

**Fix:** Change `Args:` → `Parameters:` in both files.

---

#### CODE-§3.2 — `sys.path.append('')` in legacy per-host cloud scripts

**Files:** `src/metadata_tools/hosts/GO_0xxx/GO_0xxx_*_cloud.py`, `host_init.py`

Inserting the CWD onto `sys.path` is a security risk (any same-named file in the CWD
shadows stdlib). The new `cli/` package centralizes this; the per-host scripts are now
redundant.

**Fix option 1:** Replace `sys.path.append('')` with an explicit host-directory path:
```python
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
```
**Fix option 2:** Remove the per-host cloud scripts entirely (they are superseded by
`cli/`). Verify GCP startup scripts reference `cli/` entry points, not the per-host ones.

---

#### CODE-§4.2 — Commented-out code should be removed or tracked

(Tracked partially in GitHub issue #111.)

| File | Block |
|------|-------|
| `geometry_support/suite.py` | `# SunTable` in `add_tables()` |
| `geometry_support/suite.py` | `# Run post-processor` and `# self.post()` |
| `geometry_support/record.py` | `self.overrides += overrides  ## future development` |
| `hosts/GO_0xxx/geometry_config.py` | Legacy MISSION_TABLE block |
| `tests/hosts/GO_0xxx/test_geometry.py` | Commented-out imports and `support.bounds(...)` calls |

**Fix:** For each block: decide to delete (preferred) or open a GitHub issue and add a
single reference comment. `python.mdc §4` forbids history-keeping comments.

---

#### CODE-§4.7 — `SKY_TILES` not tested

**File:** `src/metadata_tools/columns/sky.py:55` contains `###TODO: not tested...`

**Fix:** Remove the TODO comment. Add a test in `tests/columns/test_sky.py` that
verifies `SKY_TILES` has the expected structure (list of tile descriptors with correct
key names), analogous to the ring tile tests.

---

#### CODE-§5.4 — PyPI publishing uses long-lived API tokens

**Files:** `.github/workflows/publish_to_pypi.yml`, `.github/workflows/publish_to_test_pypi.yml`

**Fix:** Configure PyPI Trusted Publishers (OIDC) for SETI/rms-metadata-tools on
pypi.org and test.pypi.org, then update both workflows:

```yaml
permissions:
  id-token: write

- name: Publish package
  uses: pypa/gh-action-pypi-publish@release/v1
  # No credentials needed — OIDC authentication is automatic
```

---

#### CODE-§6.1 — `pyproject.toml` commented-out entry point placeholder

**File:** `pyproject.toml`
```toml
#TODO = "main.metadata_tools:main"
```
This line is commented out and references a non-existent module.

**Fix:** Remove the line entirely. Console scripts are now correctly declared via
`metadata_tools.cli.*:main`.

---

#### CODE-§6.2 — `py.typed` comment contradicts shipped marker file

**File:** `pyproject.toml:78-79`

The comment says `py.typed is intentionally NOT declared` but the file
`src/metadata_tools/py.typed` exists and is listed in `package-data`.

**Fix:** Remove the misleading comment and replace with:
```toml
# py.typed ships PEP 561 inline type information to downstream type-checkers
```

---

#### CODE-§7.7 — `cumulative_cloud.py` docstring says "GCP runs are not yet working"

**File:** `src/metadata_tools/cli/cumulative_cloud.py` (module docstring)

After commit `1f334bc` this statement is stale and discourages users from using a
feature that now functions.

**Fix:** Update the module docstring to describe the command's purpose without the
"not yet working" caveat. If residual issues remain, document them specifically.

---

#### DOC-H4 — Seven CLI `main()` functions have no docstrings

**Files:** `cli/index.py`, `cli/geometry.py`, `cli/cumulative.py`, `cli/task_list.py`,
`cli/index_cloud.py`, `cli/geometry_cloud.py`, `cli/cumulative_cloud.py`

**Fix:** Add a one-line docstring to each `main() -> None`:
```python
def main() -> None:
    """Entry point for the ``metadata-index`` console script."""
```

---

#### DOC-M1 — Missing API reference pages for `config` and `task_list_support`

**Fix:** Create `docs/dev_guide/api/config.rst` and
`docs/dev_guide/api/task_list_support.rst` following the same pattern as
`docs/dev_guide/api/core.rst`. Add both to the toctree in `docs/dev_guide/api/api.rst`.

---

#### DOC-M3/M4 — `CONTRIBUTING.md` issues

- Replace `cd docs && make html` with `scripts/read-docs.sh`.
- Replace the commit message example (`"Add feature: description"`) with the Conventional
  Commits form: `feat: add ring-plane geometry support for GO_0xxx`.
- Add a pointer to `docs/dev_guide/dev_guide_conventions.rst`.

---

#### CODE-§4.9 / DOC-M4 — CONTRIBUTING.md commit example does not follow Conventional Commits

(Same fix as DOC-M3/M4 above.)

---

### LOW — Clean up when passing through nearby code

| ID | File | Fix |
|----|------|-----|
| CODE-§2.5 | `index_support/table.py`, `process.py`, `prep.py` | Introduce `*` keyword-only separator for functions with >3 positional args |
| CODE-§2.7 | Multiple files | Review each `from pathlib import Path` import; replace with `FCPath` where the value is an `FCPath` |
| CODE-§2.8 | `src/metadata_tools/columns/body.py` | Strengthen `BODY_TILE_DICT: dict[str, object]` to the actual value type |
| CODE-§4.1 | `geometry_support/bodies_select.py` | Build index lookup once: `bodies_order = {n: i for i, n in enumerate(col.BODIES.keys())}` before sort |
| CODE-§4.4 | `geometry_support/prep.py` | Extract sub-operations from `prep_row()` into private functions |
| CODE-§4.6 | `columns/ring.py` | Verify `OUTER_RING_TILES['SATURN']` tiles 7 and 8 are not duplicates |
| CODE-§4.10 | `index_support/__init__.py` | Remove `_create_index` from `__all__` or rename to `create_index` |
| CODE-§4.11 | `util.py:replace()` | Change `type(leaf) in (tuple, list)` → `isinstance(leaf, (tuple, list))` |
| CODE-§5.3 | `gcp_geometry_startup.sh` | Remove duplicate `export OOPS_RESOURCES=` on line 34 |
| CODE-§7.1 | `tests/archive_support.py` | Replace `os.walk`/`glob.glob`/`os.path.join` with FCPath equivalents |
| CODE-§7.3 | `src/metadata_tools/__init__.py` | Convert RST-style module docstring to plain Google-style prose |
| CODE-§7.4 | `hosts/GO_0xxx/geometry_config.py` | Document or remove the `except_test()` always-False hook |
| CODE-§7.5 | `hosts/GO_0xxx/templates/GO_0xxx_supplemental_index.lbl:159,186` | Add quotes to unquoted `NAME` values for consistency |
| CODE-§7.6 | `geometry_support/masks.py:~95` | Replace `#!!!!` with a proper TODO comment referencing issue #109 |
| TEST-§3.2 | `tests/test_cumulative_support.py` | Convert `_silent_logger` helper to a proper `silent_logger` fixture in conftest |
| TEST-§5.1 | `tests/test_task_list.py` | Remove redundant `test_make_task_data_volume_id` (covered by `test_make_task_structure`) |
| TEST-§15.1 | `tests/test_util_math.py:124` | Seed numpy: `np.random.seed(0)` before `util.range_of_n_angles(...)` |
| TEST-§22.5 | `pyproject.toml` | Add `pytest-randomly>=3.0` to dev deps |
| DOC-L1 | `README.md` | Rename `## Licensing` → `## License` |
| DOC-L3 | `pyproject.toml:78-79` | Fix contradictory `py.typed` comment (see CODE-§6.2 above) |

---

## GitHub-tracked deferred issues

| Issue | Topic | Status |
|-------|-------|--------|
| #109 | `construct_excluded_mask` dead branch, mixed return type, gridless-backplane handling | Needs upstream design decision |
| #110 | `eval()` in `util.py:replace` — RESOLVED (2026-06-29); `_resolve_dict_ref` replaced eval | Closed |
| #111 | Commented-out/dead code cleanup (Sun-table disable decision, legacy MISSION_TABLE, host-test dead assertions) | Design decision pending |
| #112 | Host config import decoupling — RESOLVED via config registry | Closed |
| #113 | Console entry points — RESOLVED via `cli/` package | Closed |
| #114 | GCP/cloud deployment files out of the package | Open |
| #115 | Cloud workers access `worker._data` private attribute — deep redesign needed | Open |

---

## Compound AI-agent prompt

The following prompt is self-contained. Give it to a fresh agent (with no prior context)
to apply all findings above in priority order.

---

```
You are working in the `rms-metadata-tools` Python repository.

  Repository root: /home/spitale/rms-/rms-metadata-tools
  Branch: jns-updates-claude
  Package: src/metadata_tools/ (src-layout, Python 3.11+)
  Tests: tests/ (pytest, --strict-markers, -n auto, --cov=src)
  Rules: .cursor/rules/ (authoritative coding standards)

Do NOT alter PDS3 table/label byte-for-byte output. After every group of changes run:
  ruff check src tests
  mypy src tests
  pytest --tb=short
All three must pass before you proceed to the next group.

════════════════════════════════════════════════════════════════════
GROUP 1 — CRITICAL (do first; each blocks a correct build or release)
════════════════════════════════════════════════════════════════════

1a. Fix action versions in .github/workflows/publish_to_test_pypi.yml
    Change: actions/checkout@v6 → actions/checkout@v4
            actions/setup-python@v6 → actions/setup-python@v4

1b. Fix stale Sphinx cross-references in docs/dev_guide/dev_guide_support_subsystem.rst
    - Read that file and find the bullet that mentions add_task, write_task_file,
      task_source with :func:`~metadata_tools.common.*` roles.
    - Run: grep -n "def " src/metadata_tools/task_list_support.py
      to find the actual function names.
    - Replace the three :func: roles with the correct ones pointing to
      metadata_tools.task_list_support.
    - Remove any claim from the common.py description that it contains cloud-task
      plumbing (that moved to task_list_support).
    After editing: sphinx-build -W -n -b html docs /tmp/sphinx-out
    Must produce zero warnings.

1c. Rewrite "Running the programs" in docs/user_guide/user_guide_installation.rst
    - Read the file; find the section around line 137 that says "The package does not
      install console scripts".
    - Read pyproject.toml lines 116-123 for the actual installed script names.
    - Replace that section entirely with correct text documenting all seven console
      scripts (metadata-index HOST_ID ..., metadata-geometry HOST_ID ..., etc.) that
      can be run from any directory.

1d. Fix dead test in tests/test_geometry.py
    - Find test_geometry_cumulative.
    - Its first statement is `return`. Replace the entire body with:
        pytest.skip('Not yet implemented: cumulative geometry table validation')

════════════════════════════════════════════════════════════════════
GROUP 2 — HIGH (fix before next PR merge)
════════════════════════════════════════════════════════════════════

2a. Add filterwarnings = ["error"] to pyproject.toml
    In [tool.pytest.ini_options], add:
      filterwarnings = [
        "error",
        "ignore::DeprecationWarning:oops",
        "ignore::DeprecationWarning:polymath",
      ]
    Run pytest; fix or narrow-ignore any new failures.

2b. Update GCP startup scripts (cloud/gcp_common_startup.sh and all three
    cloud/GO_0xxx/gcp_*_startup.sh):
    - Change git clone branch from jns-updates-claude to main.
    - Change `pip install -r requirements.txt` to `pip install ".[cloud]"`.
    - Remove duplicate `export OOPS_RESOURCES=` in cloud/GO_0xxx/gcp_geometry_startup.sh.

2c. Fix .exists() pre-flight checks (violates filecache.mdc):
    - src/metadata_tools/label_support.py: wrap the PdsTemplate() construction and
      template.write() call in try: ... except FileNotFoundError: return
      instead of the if not filepath.exists(): return guard.
    - src/metadata_tools/index_support/table.py: find the self.primary_index_label_path.exists()
      check and replace with try/except FileNotFoundError.

2d. Fix logger.error(traceback.format_exc()) in src/metadata_tools/geometry_support/suite.py
    Find the except FileNotFoundError block. Change to:
      logger.exception('Failed to load index for %s', self.volume_id)
      return
    Remove `import traceback` from the top of the file if no other usage.

2e. Add missing Sphinx -n flag
    In scripts/run-all-checks.sh: change SPHINXOPTS="-W" to SPHINXOPTS="-W -n"
    In .github/workflows/run-tests.yml: find the sphinx build step and add -n.
    After this change, sphinx-build must still pass with zero warnings (you fixed C1 above).

2f. Update all user guide example sections (docs/user_guide/):
    In user_guide_examples.rst, user_guide_index.rst, user_guide_geometry.rst,
    user_guide_cumulative.rst, user_guide_cloud.rst:
    Replace every `python GO_0xxx_*.py` invocation with the equivalent console script:
      metadata-index GO_0xxx ...
      metadata-geometry GO_0xxx ...
      metadata-cumulative GO_0xxx ...
    Remove every `cd src/metadata_tools/hosts/GO_0xxx` step.

2g. Update dev_guide_layout.rst source tree
    Read docs/dev_guide/dev_guide_layout.rst.
    Run: ls src/metadata_tools/ and ls src/metadata_tools/cli/
    Add cli/, task_list_support.py, config.py, _version.py to the src/ block.
    Fix index_support.py (file) → index_support/ (package).
    Update common.py description to remove "task plumbing" (now in task_list_support).

2h. Replace stale __init__.py module docstring
    File: src/metadata_tools/__init__.py
    Read the file; the docstring (lines 4-84) references old per-host scripts and uses
    RST headers inside a Python docstring. Replace the entire docstring content with a
    concise Google-style description covering:
    - what the package does
    - the three pipeline stages and their console scripts
    - where per-collection config lives

2i. Add module docstrings to geometry_support package and submodules
    For each of these files, insert a one-sentence """...""" docstring immediately after
    the ################################################################################
    banner and before the first import:
      src/metadata_tools/geometry_support/__init__.py
      src/metadata_tools/geometry_support/bodies_select.py
      src/metadata_tools/geometry_support/masks.py
      src/metadata_tools/geometry_support/prep.py
      src/metadata_tools/geometry_support/formatting.py
      src/metadata_tools/geometry_support/formats.py
      src/metadata_tools/geometry_support/record.py
      src/metadata_tools/geometry_support/tables.py
      src/metadata_tools/geometry_support/suite.py
      src/metadata_tools/geometry_support/process.py
    Use the existing banner text as source material for each docstring.

2j. Create tests/test_config.py for config.py error paths
    (Full code in tests_critique.md §2.1 "Fix" block — copy verbatim.)
    Important: use monkeypatch (not direct assignment) to clear the config,
    so the conftest fake host is restored after each test.
    Verify the match= patterns match the actual RuntimeError messages in config.py.

2k. Move exists_true fixture to tests/conftest.py
    The fixture is duplicated in tests/test_geometry_masks.py:14-17 and
    tests/test_geometry_prep.py:14-17.
    1. Add it to tests/conftest.py (import oops at top if needed).
    2. Delete both local definitions.
    3. Verify: pytest tests/test_geometry_masks.py tests/test_geometry_prep.py --collect-only -q

2l. Add exception message assertions (match=) to bare pytest.raises calls
    grep -n 'pytest.raises(' tests/*.py tests/**/*.py | grep -v 'match='
    For each result, read the source exception message and add match= to the assertion.
    At minimum fix test_indextable_init_supplemental_missing_primary_raises in
    tests/test_index_support.py:
      with pytest.raises(FileNotFoundError, match='No primary index for GO_0001'):

2m. Add docstrings to CLI main() functions; fix Args: → Parameters:
    For each cli/*.py file, read it and add one-line docstrings to main().
    In src/metadata_tools/cli/_host.py: change Args: → Parameters: in run_cloud_worker.
    Also fix Args: → Parameters: in tests/archive_support.py.

2n. Add API reference pages for config and task_list_support
    Create docs/dev_guide/api/config.rst and docs/dev_guide/api/task_list_support.rst
    (see documentation_critique.md §2 "Fix M1" for the exact RST content).
    Add both to the toctree in docs/dev_guide/api/api.rst.

2o. Fix cumulative_cloud.py stale docstring
    File: src/metadata_tools/cli/cumulative_cloud.py
    Find and remove or update the sentence "GCP runs are not yet working."
    Replace with a description of what the command does.

════════════════════════════════════════════════════════════════════
GROUP 3 — MEDIUM (schedule within next few sessions)
════════════════════════════════════════════════════════════════════

3a. Add assert table_type guard → explicit raise in src/metadata_tools/common.py
    Find: assert table_type is not None  # nosec B101
    Replace with: if table_type is None: raise ValueError('table_type must not be None')

3b. Fix locals() dynamic lookup in src/metadata_tools/geometry_support/record.py
    Find: locals()['link_' + link]
    Replace with an explicit dict mapping string key → handler function.

3c. Delete resolve_task_file backwards-compat alias in src/metadata_tools/cli/_host.py
    Run: grep -r 'resolve_task_file' src/ tests/
    Update any callers to resolve_host_paths, then delete resolve_task_file.

3d. Fix pyproject.toml issues:
    - Remove the commented-out #TODO = "main.metadata_tools:main" line.
    - Remove the contradictory comment about py.typed not being declared;
      replace with: # py.typed ships PEP 561 inline type information

3e. Fix CONTRIBUTING.md:
    - Replace `cd docs && make html` with `scripts/read-docs.sh`.
    - Replace the commit message example with Conventional Commits form:
        feat: add ring-plane geometry support for GO_0xxx
    - Add a note pointing to docs/dev_guide/dev_guide_conventions.rst.

3f. Seed the non-deterministic test in tests/test_util_math.py
    Find test_range_of_n_angles_is_bounded.
    Add `np.random.seed(0)` before the util.range_of_n_angles(...) call.

3g. Remove redundant test in tests/test_task_list.py
    Delete test_make_task_data_volume_id (fully covered by test_make_task_structure).

3h. Convert _silent_logger to a fixture in tests/conftest.py
    (Full instructions in tests_critique.md §3.2 "Fix" block.)

3i. Update PyPI publish workflows to use OIDC Trusted Publishers
    Configure Trusted Publisher for SETI/rms-metadata-tools on pypi.org and test.pypi.org,
    then update both publish_to_*.yml workflows to drop user/password and use
    pypa/gh-action-pypi-publish with id-token: write permission.

════════════════════════════════════════════════════════════════════
GROUP 4 — LOW (opportunistic cleanup)
════════════════════════════════════════════════════════════════════

4a. Add module docstring to README section: rename "## Licensing" → "## License".

4b. Seed numpy in test_range_of_n_angles (covered in 3f above).

4c. Add pytest-randomly>=3.0 to [project.optional-dependencies].dev in pyproject.toml.

4d. In util.py:replace(), change `type(leaf) in (tuple, list)` → `isinstance(leaf, (tuple, list))`.

4e. Remove _create_index from index_support/__init__.__all__ (or rename to create_index).

4f. Add #!!!!  comment in geometry_support/masks.py → proper TODO(#109) comment.

4g. In geometry_support/bodies_select.py: build the bodies_order index once before sort
    instead of rebuilding on each comparison (O(n²) → O(n log n)).

4h. Add one-line docstrings to each cli/main() function (see GROUP 2 item 2m).

4i. Delete commented-out code blocks (see code_critique.md §4.2 table); open issue #111
    for any that need a design decision before deletion.

4j. Add SKY_TILES test in tests/columns/test_sky.py.

════════════════════════════════════════════════════════════════════
VERIFICATION CHECKLIST (run after all groups are complete)
════════════════════════════════════════════════════════════════════

ruff check src tests                 # must pass with 0 errors
mypy src tests                       # must pass (strict)
pytest --tb=short                    # all hermetic tests pass, ≥90% coverage
sphinx-build -W -n -b html docs /tmp/sphinx-out   # zero warnings

grep -n 'pytest.raises(' tests/*.py tests/**/*.py | grep -v 'match='
  # must return no results (all raises have match=)

grep -rn "Args:" src/metadata_tools/
  # must return no results (all docstrings use Parameters:)

grep -n "python GO_0xxx_" docs/user_guide/
  # must return no results (old-style scripts removed from docs)

grep -n "does not install console scripts" docs/user_guide/
  # must return no results

grep -n "GCP runs are not yet working" src/metadata_tools/cli/
  # must return no results

grep -n "actions/checkout@v6\|actions/setup-python@v6" .github/workflows/
  # must return no results
```

---

## Change log

| Date | Change |
|------|--------|
| 2026-06-15 | Initial analysis; geometry_support split; hermetic test suite to 93.1% coverage |
| 2026-06-16 | Ruff backlog cleared; mypy strict; dbprint deleted; builtin-shadow renames; correctness bugs fixed; host tests moved; bandit/vulture enabled |
| 2026-06-29 | eval() replaced with _resolve_dict_ref(); ring summary template variable fixed; suite.py FileNotFoundError handling fixed; local/cloud geometry script divergence fixed |
| 2026-06-30 | index_support.py split into package; generic cli/ package added |
| 2026-07-08 | Comprehensive re-read of all files; issues #112/#113 confirmed resolved; new findings: §2.9 (resolve_task_file alias), §2.10 (Args:), §5.1 (GCP branch), §7.7 (stale docstring). Documentation critique: C1 (stale cross-refs), C2 (false "no console scripts"), H1-H7 (stale docstrings, missing modules, wrong examples). Test critique: §2.4 (dead test), §16.3 (filterwarnings), §2.1 (config.py paths untested). This final_report.md updated. |
