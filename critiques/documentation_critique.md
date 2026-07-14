# Documentation Critique Report

**Generated:** 2026-07-14
**Scope:** README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, docs/ (user guide, developer guide),
every docstring in `src/metadata_tools/` (engine, CLI, columns, geometry_support, index_support,
hosts/GO_0xxx config modules), docs/conf.py, and the Sphinx build. Every file in scope was read
in full; the docs were built for real (not just statically reviewed).
**Rules applied:** `doc_python.mdc`, `doc_readme.mdc`, `doc_user_guide.mdc`, `doc_dev_guide.mdc`,
`doc_how_to.mdc` — all five rule files are present and applied.

---

## Executive summary

**Build health:** The docs build clean with **zero warnings** under `sphinx-build -W`,
`sphinx-build -n`, and the combined `sphinx-build -W -n` (verified by running all three against
a scratch output directory in this pass, using the project's own venv). Cross-reference hygiene,
`nitpick_ignore_regex` entries, README structure, and docstring *format* (Google style,
`Parameters:` not `Args:`) are all now clean — the `Args:` finding from the prior critique pass
is fixed (`_host.py` uses `Parameters:` throughout).

**However, this pass found that the developer guide contains a serious, previously-unflagged
architecture regression**: four separate pages (`dev_guide_architecture.rst`,
`dev_guide_environment.rst`, `dev_guide_extending.rst`, `dev_guide_layout.rst`) describe an
obsolete pre-issue-#112 design in which each host has its own runnable `<HOST>_index.py`-style
scripts that only work when the current working directory is the host's own directory. That
design was replaced (see `src/metadata_tools/config.py`'s own docstring, which explicitly
references issue #112): `config.set_host()` now does a package-qualified import
(`metadata_tools.hosts.<host_id>.host_config`) that works from any current working directory.
None of the `<HOST>_*.py` scripts these pages tell a developer to run or copy exist anywhere in
`src/` (a stale copy is visible only in the untracked `build/lib/` directory from an old build).
A developer who follows `dev_guide_environment.rst`'s literal example command will get
`python: can't open file 'GO_0xxx_index.py': No such file or directory`.

**Other confirmed, still-open issues from the prior critique** (re-verified against current
file contents, not assumed): `CONTRIBUTING.md` is stale (PEP 8, wrong docs-build command, no
Conventional Commits, a `NDArrayFloatType` type that doesn't exist anywhere in the codebase);
`columns/{body,ring,sky,sun}.py` module-level column-definition constants are undocumented and
two `columns/body.py` functions have thin one-line docstrings; `docs/conf.py`'s `source_suffix`
is still list form; `_host.py::resolve_task_file` still carries "kept for backwards
compatibility" framing that `doc_python.mdc` §2 forbids; no `pipx` install note; no dedicated
how-to articles.

**New findings from this pass, beyond the architecture regression above:** the "Task file
schema" JSON example in `user_guide_cloud.rst` shows a `task_id` format
(`"geometry-task-GO_0017"`) that does not match what `task_list_support.make_task()` actually
generates (`"task-GO_0017"`); the `--ssh-paste` CLI flag (implemented in all three `*_cloud.py`
modules and `_host.py::build_startup_script`) is undocumented in `user_guide_cloud.rst`'s
option tables; `hosts/GO_0xxx/geometry_config.py::target_name`'s docstring describes SKY/CIMS
fallback logic that the three-line implementation does not contain; `cli/__init__.py` is an
empty file with no module docstring.

**High-priority fixes:** the four-page stale-architecture narrative (§6, §9); `CONTRIBUTING.md`
(§6, §9); the `task_id` schema mismatch and missing `--ssh-paste` docs in `user_guide_cloud.rst`
(§5, §9).
**Nice-to-have:** `pipx` note, `columns/` docstring completeness, `source_suffix` dict form,
`resolve_task_file` wording, `cli/__init__.py` docstring, how-to articles.

---

## 1. Documentation system and build

**Single source tree:** All docs live under `docs/` with a single `conf.py`. Build outputs
(`_build/`) are gitignored. ✓

**`conf.py` extensions:** Autodoc, viewcode, napoleon, intersphinx, sphinxcontrib.mermaid, and
myst_parser are all enabled (`docs/conf.py:79-86`). The source root is on `sys.path`
(`docs/conf.py:14`). The version is derived from `importlib.metadata.version` with a fallback
(`docs/conf.py:71-74`). A hand-rolled `oops` import shim (`docs/conf.py:32-62`) lets `autodoc`
import every engine module headlessly without SPICE; `host_config`/`index_config`/
`geometry_config` are separately mocked via `autodoc_mock_imports` (`docs/conf.py:120-124`)
because they are plugin-injected at runtime. Both mechanisms are correct and well-commented. ✓

**Build cleanliness (verified by actually running the build in this pass):**

```
source venv/bin/activate
sphinx-build -W -b html docs /tmp/docbuild-w    # build succeeded, zero warnings
sphinx-build -n -b html docs /tmp/docbuild-n    # build succeeded, zero warnings
sphinx-build -W -n -b html docs /tmp/docbuild-wn  # build succeeded, zero warnings
```

All three succeeded with **zero warnings**. ✓

**[LOW] `source_suffix` still uses the deprecated list form.**
`docs/conf.py:101` reads `source_suffix = ['.rst', '.md']`. This still triggers Sphinx's
internal "Converting `source_suffix` to dict form" implicit-conversion path on every build
(harmless, but it is the deprecated form `doc_python.mdc` §3 asks for the dict form to avoid).

**Fix:** In `docs/conf.py`, replace line 101:
```python
source_suffix = ['.rst', '.md']
```
with:
```python
source_suffix = {'.rst': 'restructuredtext', '.md': 'restructuredtext'}
```

**[LOW] `_host.py::resolve_task_file` still carries "backwards compatible" framing.**
`src/metadata_tools/cli/_host.py:89-91`:
```python
def resolve_task_file(host_dir: Path) -> None:
    """Alias for :func:`resolve_host_paths`; kept for backwards compatibility."""
    resolve_host_paths(host_dir)
```
`doc_python.mdc` §2 explicitly forbids "backwards compatible" and similar time-anchored framing
in docstrings (this text is rendered verbatim into the API reference).

**Fix:** Change the docstring on `src/metadata_tools/cli/_host.py:90` to:
```python
    """Alias for :func:`resolve_host_paths`."""
```

**Prose conventions:** American spelling, one-space-after-period, and no time-anchored language
were otherwise observed cleanly across the guide chapters actually read in this pass (the
`resolve_task_file` case above is the only violation found). No unicode smart quotes / em-dashes
/ arrows were found inside any `.py` file in `src/`. ✓

---

## 2. Docstrings and API reference

**Coverage:** Every module, class, method, and function across the entire `src/metadata_tools/`
tree that was read in this pass (`cli/`, `columns/`, `geometry_support/`, `index_support/`,
`hosts/GO_0xxx/`, and every top-level module: `bodies.py`, `common.py`, `config.py`,
`cumulative_support.py`, `defs.py`, `label_support.py`, `task_list_support.py`, `util.py`,
`__init__.py`) has a docstring, and the format is uniformly Google-style with `Parameters:` /
`Returns:` / `Raises:` where applicable. **No `Args:` header remains anywhere in the codebase**
(verified with `grep -rn "Args:" src/metadata_tools`, zero hits) — the prior critique's finding
that `_host.py::build_startup_script` and `_host.py::dispatch_cloud_run_if_config` used `Args:`
is **already fixed**; both now read `Parameters:` (`src/metadata_tools/cli/_host.py:150,276`).
Do not re-open that finding.

**[HIGH] `hosts/GO_0xxx/geometry_config.py::target_name` docstring describes logic the function
does not implement.**
`src/metadata_tools/hosts/GO_0xxx/geometry_config.py:196-209`:
```python
def target_name(snapshot: dict[str, Any]) -> str:
    """Determine the target name from the snapshot's dictionary.

    If the given name is "SKY", it checks the CIMS ID and the TARGET_DESC for
    something different.

    Parameters:
        snapshot: Snapshot observation dictionary.

    Returns:
        Target name.
    """

    return cast(str, snapshot["TARGET_NAME"])
```
The docstring's second paragraph claims special-case handling for a `"SKY"` target name (CIMS ID
/ `TARGET_DESC` fallback), but the implementation is an unconditional one-line passthrough of
`snapshot["TARGET_NAME"]`. This is either dead documentation left over from a removed code path,
or a genuine bug where the described fallback logic was accidentally deleted. Either way the
docstring is currently false and will mislead anyone reading the API reference or the source.

**Fix:** First check with the maintainer (or `git log -p -- src/metadata_tools/hosts/GO_0xxx/geometry_config.py`)
whether the SKY/CIMS/TARGET_DESC fallback logic was intentionally removed:
- If it was intentionally removed: delete the second paragraph of the docstring so it reads only:
  ```python
      """Determine the target name from the snapshot's dictionary.

      Parameters:
          snapshot: Snapshot observation dictionary.

      Returns:
          Target name.
      """
  ```
- If it was accidentally lost: this is a functional bug, not just a doc bug — flag it to the
  code-critique track rather than papering over it with a docstring edit; do not silently delete
  the paragraph in that case.

**[MEDIUM] `get_body_summary_dict` / `get_body_detailed_dict` have thin, one-line docstrings.**
`src/metadata_tools/columns/body.py:100-118`:
```python
def get_body_summary_dict() -> dict[str, Any]:
    """Return the per-body summary column replacement dict, building it on first call."""
    ...

def get_body_detailed_dict() -> dict[str, Any]:
    """Return the per-body detailed column replacement dict, building it on first call."""
    ...
```
Neither has a `Returns:` section describing the dict's key/value shape, and neither documents
that the underlying registry requires `oops` to already be initialized (a real, easy-to-hit
precondition — see `dev_guide_support_subsystem.rst`'s "Import order" invariant).

**Fix:** Expand both docstrings in `src/metadata_tools/columns/body.py`:
```python
def get_body_summary_dict() -> dict[str, Any]:
    """Return the per-body summary column replacement dict, building it on first call.

    Requires the oops body registry to already be populated (see
    :func:`~metadata_tools.bodies.get_bodies_registry`).

    Returns:
        Mapping from body name to its summary column-description list, with
        each occurrence of :data:`~metadata_tools.defs.BODYX` substituted for
        that body's name.
    """
```
```python
def get_body_detailed_dict() -> dict[str, Any]:
    """Return the per-body detailed column replacement dict, building it on first call.

    Requires the oops body registry to already be populated (see
    :func:`~metadata_tools.bodies.get_bodies_registry`).

    Returns:
        Mapping from body name to its detailed column-description list, with
        each occurrence of :data:`~metadata_tools.defs.BODYX` substituted for
        that body's name.
    """
```

**[MEDIUM] Column-definition module-level constants are undocumented, unlike `defs.py`'s
established convention.**
`src/metadata_tools/defs.py` documents every module-level constant with a trailing docstring
literal, e.g. (`src/metadata_tools/defs.py:18-19`):
```python
PARENT_DIR = FCPath(_metadata.__file__).parent
"""Directory containing the installed package."""
```
None of the column-definition constants in the `columns/` subpackage follow this convention,
even though they are re-exported as part of the public `metadata_tools.columns` surface
(`src/metadata_tools/columns/__init__.py:46-74`) and rendered in the API reference via
`automodule ... :undoc-members:`:
- `src/metadata_tools/columns/body.py`: `BODY_COLUMNS` (line 52), `BODY_GRIDLESS_COLUMNS`
  (line 73), `BODY_SUMMARY_COLUMNS` / `BODY_DETAILED_COLUMNS` (line 93-94), `BODY_TILES`
  (line 126), `BODY_TILE_DICT` (line 142).
- `src/metadata_tools/columns/ring.py`: `RING_COLUMNS` (line 53), `ANSA_COLUMNS` (line 76),
  `RING_GRIDLESS_COLUMNS` (line 86), `RING_SUMMARY_COLUMNS` / `RING_DETAILED_COLUMNS`
  (line 116-118), `RING_TILES` (line 138), `OUTER_RING_TILES` (line 157), `RING_TILE_DICT`
  (line 175), `OUTER_RING_TILE_DICT` (line 179).
- `src/metadata_tools/columns/sky.py`: `SKY_COLUMNS` (line 44), `SKY_TILES` (line 56).
- `src/metadata_tools/columns/sun.py`: `SUN_COLUMNS` (line 44), `SUN_GRIDLESS_COLUMNS`
  (line 56), `SUN_SUMMARY_COLUMNS` / `SUN_DETAILED_COLUMNS` (line 67-68).

**Fix:** Add a one-line trailing docstring to each constant above, following the `defs.py`
pattern, e.g. in `src/metadata_tools/columns/body.py` immediately after line 52's list literal
closes (line 71, before the blank line):
```python
BODY_COLUMNS = [
    ...
    (("event_time",             defs.BODYX),                    ("RM", "", ""))]
"""Per-pixel body-surface column descriptions, keyed by backplane call."""
```
Repeat for each constant listed above with a one-sentence description of what it contains (the
module docstrings at the top of each file already describe the constants in prose — reuse that
wording per-constant rather than inventing new text).

**[LOW] `columns/sky.py::SKY_TILES` still carries a `###TODO` comment in production code.**
`src/metadata_tools/columns/sky.py:55`:
```python
###TODO: not tested...
SKY_TILES = [
```
`doc_python.mdc` and general project hygiene call for TODOs to be tracked as issues, not left as
comments with no owner or ticket reference.

**Fix:** File a GitHub issue describing what "not tested" refers to (the sky-tile detailed
tabulation path), then delete line 55 from `src/metadata_tools/columns/sky.py` and reference the
issue number in the PR description, not in a source comment.

**[LOW] `cli/__init__.py` is an empty file with no module docstring.**
`src/metadata_tools/cli/__init__.py` is 0 bytes. `doc_python.mdc` §4 requires every module to
have a descriptive docstring. The `cli` package is intentionally excluded from the Sphinx API
reference (documented instead via the user guide's command-line-program chapters — see
`docs/dev_guide/api/api.rst:6-10`), so this does not affect the rendered API surface, but it is
still a rule violation for anyone reading the source.

**Fix:** Add to `src/metadata_tools/cli/__init__.py`:
```python
"""Console-script entry points for metadata_tools (see the user guide for usage)."""
```

**[LOW] `index_support`'s API reference page is structured differently from its sibling
subpackages, and exposes a private-named function.**
`docs/dev_guide/api/index_support.rst` uses a single `automodule:: metadata_tools.index_support`
directive for the whole subpackage, while `docs/dev_guide/api/geometry_support.rst` and
`docs/dev_guide/api/columns.rst` — the other multi-module subpackages — each get one
`automodule` block per submodule with its own heading. This is not a build error (the page
still renders every member because `index_support/__init__.py`'s `__all__` re-exports them,
`src/metadata_tools/index_support/__init__.py:20-27`), but the inconsistent presentation makes
`index_support` harder to navigate than its siblings. Separately, `__all__` re-exports
`_create_index` (an underscore-prefixed, conventionally-private name) into the public API
surface, so it appears in the rendered API reference next to genuinely public names like
`IndexTable` and `process_index`.

**Fix (optional, low priority):** Either (a) split `docs/dev_guide/api/index_support.rst` into
per-submodule sections (`key_fns`, `process`, `table`) matching the `geometry_support.rst`
pattern, or (b) leave the single-page structure but add a one-sentence note explaining why
`index_support` is documented as one page while `geometry_support` is documented as several.
Separately, decide whether `_create_index` is meant to be called externally: if not, remove it
from `src/metadata_tools/index_support/__init__.py`'s `__all__` (line 22) and the import at
line 14; if it is meant to be public, rename it without the leading underscore.

**API-reference coverage:** Every other public engine module (`common`, `config`, `defs`,
`bodies`, `label_support`, `task_list_support`, `cumulative_support`, and the `geometry_support`
submodules) appears in `docs/dev_guide/api/*.rst` with `automodule ... :members: :undoc-members:
:show-inheritance:`. The `cli/` and `hosts/` packages are deliberately excluded and documented
in prose instead (`docs/dev_guide/api/api.rst:6-10`), which is an acceptable, explicitly-stated
design choice. ✓

---

## 3. Cross-reference completeness

**Build under nitpicky mode:** `sphinx-build -n` passes with zero unresolved cross-references
(re-verified in this pass, see §1). ✓

**`nitpick_ignore_regex` entries** (`docs/conf.py:169-197`): every entry targets a genuine
third-party symbol (`FCPath`, `pdstable.*`, `oops(\..*)?`, `numpy.typing.*`, `pytest.*`, etc.)
with an inline comment explaining why it has no resolvable Sphinx inventory. No entry suppresses
a symbol the project owns. ✓

**Cross-reference style in narrative prose:** Every dev-guide and user-guide chapter read in
this pass uses `:class:`, `:func:`, `:meth:`, `:mod:`, `:data:`, and `:doc:` roles correctly for
API-symbol mentions; no bare CamelCase or `module.symbol` text was found used as prose (as
opposed to inside `.. code-block::`/`::` literal blocks, where roles are correctly omitted). ✓

---

## 4. README

**Format and inclusion:** `README.md` is Markdown with a `<!-- start-after-point -->` marker at
line 27; the badge block above it is excluded from the Sphinx-rendered version via
`docs/index.rst:7-9`'s `:start-after:`. Single top-level `#` title. ✓

**Required sections, in order (`README.md`):** Title (1) → Badges (3-26) → Introduction (29-46)
→ Features (48-62) → Installation (64-88) → Quick Start (90-113) → Documentation (115-127) →
Contributing (129-132) → License (141-145). All nine required sections present, in order. ✓

**[LOW] Not every console script is individually named in the README.**
`README.md`'s Quick Start (lines 90-113) shows only `metadata-index`, `metadata-geometry`, and
`metadata-cumulative`. The Features section (line 59-60) gestures at the six additional
worker/cloud scripts collectively ("Run on one machine, or distribute per-volume work across
Google Cloud with the included `rms-cloud-tasks` workers") and `metadata-task-list` is not
mentioned anywhere in the README. `doc_readme.mdc` §3 says "every command-line program... should
be mentioned at least once with a pointer to its detailed documentation" — the README does link
to the user guide's full program list (line 110-113), which satisfies the spirit of the rule
collectively, but no individual script name beyond the core three appears.

**Fix (optional, low priority):** In the Features bullet at `README.md:59-60`, name the actual
script family instead of only "workers": e.g. "Run on one machine with the `*-worker` scripts,
or distribute per-volume work across Google Cloud with the `*-cloud` scripts and
`metadata-task-list`." This keeps the README a summary (per `doc_readme.mdc` §3, "NOT a
manual") while giving every program name at least one mention.

**Content quality:** Quickstart examples reference `$RMS_VOLUMES` / `$RMS_METADATA`, defined in
`docs/user_guide/user_guide_installation.rst`. Badge claims, supported Python versions
(3.11-3.13), and the install command match `pyproject.toml`. All links point to real,
resolvable targets. ✓

---

## 5. User guide

**Layout:** `docs/user_guide/user_guide.rst` is the landing page with a `toctree` listing all
nine chapters, prefixed `user_guide_*`. ✓

**Required content coverage:** introduction/workflow (`user_guide_overview.rst`, including a
Mermaid pipeline diagram), installation (`user_guide_installation.rst`), configuration
(`user_guide_configuration.rst`), one chapter per program family (`user_guide_index.rst`,
`user_guide_geometry.rst`, `user_guide_cumulative.rst`, `user_guide_cloud.rst`), examples
(`user_guide_examples.rst`), and a host appendix (`user_guide_appendix_hosts.rst`). ✓

**Command-line program references (`user_guide_index.rst`, `user_guide_geometry.rst`,
`user_guide_cumulative.rst`):** cross-checked against the actual argparsers
(`src/metadata_tools/common.py::get_common_args`, `index_support/process.py::get_args`,
`geometry_support/process.py::get_args`, `cumulative_support.py::get_args`) in this pass — every
documented option (`--volumes`, `--pattern`/`-p`, `--labels`/`-l`, `--type`/`-t`,
`--selection`, `--sampling`/`-s`, `--exclude`/`-e`, `--new_only`/`-n`, `--first`/`-f`) matches
the parser exactly, including defaults and short flags. ✓

**[HIGH] "Task file schema" example does not match the actual `task_id` format.**
`docs/user_guide/user_guide_cloud.rst:269-280`:
```json
[
  {
    "task_id": "geometry-task-GO_0017",
    "data": { "volume_id": "GO_0017" }
  },
  ...
```
The actual generator is `src/metadata_tools/task_list_support.py:21-30`:
```python
def make_task(volume_id: str) -> dict[str, Any]:
    """Build a single task dict for *volume_id*."""
    return {'task_id': f'task-{volume_id}', 'data': {'volume_id': volume_id}}
```
which produces `"task_id": "task-GO_0017"` — there is no `"geometry-"` prefix, and the prefix
does not vary by stage (index/geometry/cumulative all use the same `task-<volume_id>` form,
except the single-task cumulative case in `_host.py:374` which uses the literal string
`'cumulative'`). A user who inspects a real generated task file will see a different shape than
the documentation shows.

**Fix:** In `docs/user_guide/user_guide_cloud.rst`, replace the JSON block at lines 269-280 with:
```json
[
  {
    "task_id": "task-GO_0017",
    "data": { "volume_id": "GO_0017" }
  },
  {
    "task_id": "task-GO_0018",
    "data": { "volume_id": "GO_0018" }
  }
]
```
Also fix the prose sentence immediately below the block (currently "The `task_id` prefix
identifies the stage that produced the file") — this is no longer accurate since the prefix is
always `task-` (or the literal `cumulative` for the single-task cumulative case) regardless of
stage. Replace it with: "Each `task_id` is `task-<volume_id>`, except the single-task cumulative
run, whose worker uses the fixed id `cumulative` (see
:func:`~metadata_tools.task_list_support.make_task` and
:func:`metadata_tools.cli._host.single_task_as_task_file`)."

**[MEDIUM] `--ssh-paste` is implemented but undocumented.**
All three `*_cloud.py` entry points accept `--ssh-paste` and document it in their own module
docstrings, e.g. `src/metadata_tools/cli/index_cloud.py:33-34`:
```
  --ssh-paste                 With --create-startup-file: replace ``cd /root`` with ``cd ~``
                              so the script can be pasted into an SSH terminal as a non-root user.
```
and it is implemented via `_host.py::build_startup_script`'s `for_ssh` parameter
(`src/metadata_tools/cli/_host.py:137-239`, notably lines 167-172, 194-214, and 220-238). But
`docs/user_guide/user_guide_cloud.rst`'s "Cloud-only overrides" table
(lines 156-179) lists only `--create-startup-file`, `--startup-template`, `--oops-resources`,
`--service-account`, and `--debug-branch` — `--ssh-paste` is missing entirely, including from
the "Previewing the startup script" example (lines 100-112), which would be the natural place
to mention it.

**Fix:** In `docs/user_guide/user_guide_cloud.rst`, add a row to the "Cloud-only overrides"
list-table at line 158-179:
```rst
   * - ``--ssh-paste``
     - With ``--create-startup-file``: produce an SSH-pastable variant of the script (replaces
       ``cd /root`` with ``cd ~`` and prepends ``set +e`` around the worker command so a
       failure does not close the SSH session). Has no effect without
       ``--create-startup-file``.
```
Also add a short example to the "Previewing the startup script" section (after line 109's code
block):
```rst
To produce a variant that can be pasted directly into an interactive SSH session on the
instance, add ``--ssh-paste``:

.. code-block:: bash

   metadata-index-cloud GO_0xxx "$RMS_VOLUMES_GCP/GO_0xxx/" "$RMS_METADATA_GCP/GO_0xxx/" \
       "$RMS_METADATA_TEST_GCP/GO_0xxx/" --create-startup-file startup.sh --ssh-paste
```

**[LOW] No `pipx` install instruction.**
`docs/user_guide/user_guide_installation.rst`'s "Installation" section (lines 26-59) documents
only `pip install rms-metadata-tools` and `pip install -e ".[dev]"`. `doc_user_guide.mdc` §2
requires `pipx` to be shown "when command-line programs should be available system-wide" — this
package installs ten console scripts, so it qualifies.

**Fix:** In `docs/user_guide/user_guide_installation.rst`, immediately after the
`pip install rms-metadata-tools` code block (after line 34), add:
```rst
To make the console scripts available system-wide without affecting other Python
environments, install with `pipx <https://pipx.pypa.io/>`_ instead:

.. code-block:: bash

   pipx install rms-metadata-tools
```

**[LOW] No "API usage" section.**
`doc_user_guide.mdc` §2 requires an "API usage" section for any importable surface. The guide
covers only the CLI. Given the package is primarily a CLI tool and the engine API is documented
in the developer guide (aimed at contributors, not API consumers), this is a soft gap; consider
a short "Using the engine directly" note in `user_guide_overview.rst` or a new short section
pointing to `docs/dev_guide/dev_guide_architecture.rst` and the API reference, rather than
duplicating developer-guide content.

---

## 6. Developer guide

**Layout:** `docs/dev_guide/dev_guide.rst` is the landing page with a full-guide `toctree`
ending in `api/api`. Chapters are consistently prefixed `dev_guide_*`. ✓

**Required chapters present:** introduction, repository layout, environment setup, architecture
(with a Mermaid class diagram), one chapter per subsystem (index/geometry/cumulative/support),
extending, conventions, and the API reference. ✓ (structurally)

### [CRITICAL] Four developer-guide pages describe an architecture the codebase no longer has

This is the highest-priority finding in this report. `src/metadata_tools/config.py`'s own module
docstring (`src/metadata_tools/config.py:4-11`) says explicitly:

> Generic engine modules ... call `get_host_config()`, `get_index_config()`, and
> `get_geometry_config()` instead of doing a top-level `import host_config`. Entry points call
> `set_host()` once, before touching any engine code, to populate the registry for the host
> being processed.

and `set_host()` (`src/metadata_tools/config.py:22-40`) does a **package-qualified import**
(`importlib.import_module(f'metadata_tools.hosts.{host_id}.host_config')`) that works from *any*
current working directory — CLAUDE.md confirms this is the fix for "issue #112" and states "This
works from any current working directory — no `sys.path` manipulation is involved." There are no
`<HOST>_index.py`-style runnable scripts anywhere in `src/metadata_tools/hosts/GO_0xxx/`
(confirmed: `find src/metadata_tools/hosts -name "*.py"` lists only `geometry_config.py`,
`host_config.py`, `host_init.py`, `index_config.py`, `__init__.py`) — the only place such files
exist is the stale, untracked `build/lib/metadata_tools/hosts/GO_0xxx/` directory from an old
build.

Four pages still describe the pre-fix design:

**6a. `docs/dev_guide/dev_guide_architecture.rst:16-21`** ("Engine and host configuration"):
```rst
The engine never imports a specific host. Instead, the host's runnable scripts
set the current working directory to the host package and import their
configuration as the top-level modules ``host_config``, ``index_config``, and
``geometry_config``; the engine modules then import those same top-level names.
This is why host scripts only work when run from inside the host directory, and
why the documentation build mocks those three module names (see ``docs/conf.py``).
```
This paragraph is simply false as a description of the current code.

**Fix:** Replace `docs/dev_guide/dev_guide_architecture.rst:16-21` with:
```rst
The engine never imports a specific host's config modules directly (see issue #112).
Instead, console-script entry points call :func:`metadata_tools.config.set_host`
once, which package-qualifies the import of ``metadata_tools.hosts.<host_id>.host_config``
and ``index_config`` (``geometry_config`` is imported lazily, on first use, to avoid
paying the SPICE startup cost for stages that do not need it). Engine modules then
call :func:`~metadata_tools.config.get_host_config`,
:func:`~metadata_tools.config.get_index_config`, and
:func:`~metadata_tools.config.get_geometry_config` instead of importing those modules
directly. This works from any current working directory — no ``sys.path`` manipulation
is involved — and is why the documentation build mocks the three module names as
plugin-injected surfaces (see ``docs/conf.py``) rather than needing a working directory
trick.
```

**6b. `docs/dev_guide/dev_guide_environment.rst:46-59`** ("Running the entry points"):
```rst
Run a host's programs from inside its directory, because they import their
configuration as top-level modules:

.. code-block:: bash

   cd src/metadata_tools/hosts/GO_0xxx
   python GO_0xxx_index.py "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" -vv GO_0017
```
This is a literally broken instruction: `GO_0xxx_index.py` does not exist in `src/`, and `-vv`
is not a flag accepted by any argument parser in the codebase (verified: no `-v`/`-vv`/
`verbose`/`log-level` argument exists anywhere in `common.py` or any `cli/*.py` module).

**Fix:** Replace `docs/dev_guide/dev_guide_environment.rst:46-59` with:
```rst
Running the entry points
=========================

Run any console script from any directory; pass the host id as the first
argument (see :doc:`/user_guide/user_guide_installation`):

.. code-block:: bash

   metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
       "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017

A fast smoke test is to add ``--first 5`` to the geometry stage so it stops
after five images. See :doc:`/user_guide/user_guide_examples`.
```
(This also removes the now-redundant duplicate sentence about `--first 5` that follows at
lines 58-59 in the original — fold it into the replacement as shown, do not leave two copies.)

**6c. `docs/dev_guide/dev_guide_extending.rst:9-27`** ("Adding a new host"):
```rst
#. Copy the Python modules and the ``<HOST>_*`` scripts from an existing host and
   rename the scripts for the new collection.
...
The configuration modules form the contract the engine relies on. The host
scripts import them as the top-level names ``host_config``, ``index_config``, and
``geometry_config``, so they only resolve when the current working directory is
the host directory.
```
Same obsolete model: there are no `<HOST>_*` scripts to copy, and config resolution is not
tied to the current working directory.

**Fix:** In `docs/dev_guide/dev_guide_extending.rst`, replace lines 15-27 with:
```rst
#. Create ``src/metadata_tools/hosts/<HOST>/`` (named for the PDS volume set,
   e.g. ``COISS_xxxx``). Copy ``host_config.py``, ``index_config.py``,
   ``geometry_config.py``, ``host_init.py``, and ``__init__.py`` from an existing
   host (e.g. ``GO_0xxx``) as a starting point.
#. Edit the configuration modules (below) and ``host_init.py``.
#. Create a ``templates/`` subdirectory, copy the templates, rename them, edit
   ``host_defs.lbl`` and the summary templates, and define the supplemental
   metadata in the supplemental template.

The configuration modules form the contract the engine relies on. Console-script
entry points call :func:`metadata_tools.config.set_host` with the host id, which
package-imports ``metadata_tools.hosts.<HOST>.host_config`` and ``index_config``
(``geometry_config`` is imported lazily on first use); the engine then reads them
through :func:`~metadata_tools.config.get_host_config`,
:func:`~metadata_tools.config.get_index_config`, and
:func:`~metadata_tools.config.get_geometry_config`. No current-working-directory
convention is involved.
```

**6d. `docs/dev_guide/dev_guide_layout.rst:88,95-101`** (repository layout tree) — already
flagged in the prior critique for the `cloud/` section; this pass confirms it is still open and
finds a second, related staleness in the **same page**:

Line 88, inside the "A host directory contains configuration, templates, and runnable scripts"
tree:
```rst
     GO_0xxx_*_cloud.py        # rms-cloud-tasks (GCP) counterparts
```
No such files exist anywhere in `src/metadata_tools/hosts/GO_0xxx/` (confirmed above).

Lines 95-101, the `cloud/` deployment tree:
```rst
   cloud/
     gcp_common_startup.sh     # shared VM bootstrap header
     generate_startup_scripts.py  # regenerates gcp_*_startup.sh from tail fragments
     GO_0xxx/
       gcp_*_config.yml        # GCP machine/queue configuration
       gcp_*_startup.sh        # GCP instance start-up scripts (generated)
       gcp_*_startup.tail.sh   # host-specific command fragments (edit these)
```
The actual `cloud/` tree (confirmed via `find cloud -type f`) is:
```
cloud/gcp_common_startup.sh
cloud/GO_0xxx/gcp_cumulative_config.yml
cloud/GO_0xxx/gcp_geometry_config.yml
cloud/GO_0xxx/gcp_index_config.yml
cloud/GO_0xxx/tasks.json
```
There is no `generate_startup_scripts.py`, no per-host `gcp_*_startup.sh`, and no
`gcp_*_startup.tail.sh` — startup scripts are generated at runtime by
`metadata_tools.cli._host.build_startup_script`.

**Fix:** In `docs/dev_guide/dev_guide_layout.rst`:
1. Delete line 88 (`GO_0xxx_*_cloud.py        # rms-cloud-tasks (GCP) counterparts`) from the
   host-directory tree entirely — there is nothing to list there beyond what is already shown
   (`host_config.py`, `index_config.py`, `geometry_config.py`, `host_init.py`, `templates/`).
2. Replace lines 93-101 with:
```rst
GCP deployment files live outside the package and are not installed with the wheel:

.. code-block:: text

   cloud/
     gcp_common_startup.sh     # shared VM bootstrap template
     GO_0xxx/
       gcp_index_config.yml        # GCP machine/queue config for the index stage
       gcp_geometry_config.yml     # GCP machine/queue config for the geometry stage
       gcp_cumulative_config.yml   # GCP machine/queue config for the cumulative stage
       tasks.json                 # example/output task file

GCP instance startup scripts are generated at runtime by
:func:`metadata_tools.cli._host.build_startup_script` (invoked by the ``*-cloud``
entry points, or previewed directly with ``--create-startup-file``); they are never
stored in the repository.
```

**[HIGH] `dev_guide_conventions.rst` contradicts the project's actual tooling — and contradicts
another page in the same guide.**
`docs/dev_guide/dev_guide_conventions.rst:31-33`:
```rst
Python style and typing
=======================

Maximum line length is 100. The project does not run ``ruff format`` as a gate;
``ruff check`` is the linter.
```
This is false. `ruff format --check` **is** run as a gate:
- `docs/dev_guide/dev_guide_environment.rst:102` (the same developer guide, a different page)
  lists `ruff format --check src tests` among the individual quality-gate commands.
- `CLAUDE.md:46` lists the same command.
- `scripts/run-all-checks.sh:383-384` actually executes `python -m ruff format --check src
  tests`.
- `scripts/run-all-checks.sh:58` and its `--ruff-format` flag (line 23) exist specifically to
  run this check.

**Fix:** In `docs/dev_guide/dev_guide_conventions.rst`, replace lines 31-33:
```rst
Python style and typing
=======================

Maximum line length is 100. ``ruff check`` is the linter and ``ruff format --check``
enforces formatting (both are run by ``scripts/run-all-checks.sh``); code is
formatted with ``ruff format`` using single quotes.
```

**Architecture diagram (`dev_guide_architecture.rst`):** the Mermaid `classDiagram`
(lines 31-86) accurately reflects the current `Table`/`IndexTable`/`InventoryTable`/`SkyTable`/
`SunTable`/`RingTable`/`BodyTable`/`Suite`/`Record` class relationships — cross-checked against
`src/metadata_tools/common.py`, `geometry_support/tables.py`, `geometry_support/suite.py`, and
`geometry_support/record.py` in this pass. ✓ (Only the prose section immediately above the
diagram is stale — see 6a.)

**Per-subsystem chapters** (`dev_guide_index_subsystem.rst`, `dev_guide_geometry_subsystem.rst`,
`dev_guide_cumulative_subsystem.rst`, `dev_guide_support_subsystem.rst`): all four were
cross-checked against the corresponding source modules in this pass (the value-resolution
contract in the index chapter against `index_support/table.py::_index_one_value`; the
format-dictionary contract in the geometry chapter against `geometry_support/formats.py`; the
cumulative table-object list against `cumulative_support.py::create_cumulative_indexes`; the
`common`/`task_list_support`/`label_support`/`columns`/`bodies`/`util`/`defs` summaries in the
support chapter). All four accurately describe current behavior. ✓

**API reference:** see §2 above (`index_support.rst` structural inconsistency is the only
finding here).

---

## 7. How-to articles

No dedicated how-to articles exist. `user_guide_examples.rst` (not fully reproduced here, but
present in the `toctree`) functions as an informal examples page rather than a structured
how-to per `doc_how_to.mdc` (no explicit "Prerequisites" / numbered steps with observed results
/ "Troubleshooting" / "Related material" sections). `dev_guide_extending.rst`'s three recipes
("Adding a new host", "Adding an index column", "Adding a geometry column") are close to how-to
structure already but live in the developer guide, which is appropriate for their contributor
audience — they do not need to move, but converting user-facing workflows ("run geometry
generation on GCP", "generate a task file and dispatch to GCP") into how-to articles per
`doc_how_to.mdc`'s required-elements list (prerequisites, numbered steps with observed results,
troubleshooting) would materially help a first-time user of `user_guide_cloud.rst`, which is
currently the guide's most complex chapter.

This is unchanged from the prior critique and remains a lower priority than the architecture
and CONTRIBUTING.md fixes above.

---

## 8. Diagrams and figures

**Architecture diagram:** the Mermaid `classDiagram` in `dev_guide_architecture.rst` renders
correctly in the build (confirmed via the successful `-W -n` build in this pass) and is followed
by narrative prose walking each class group. ✓

**Pipeline diagram:** `user_guide_overview.rst:62-72` contains a Mermaid `flowchart` of the
three-stage pipeline (index → geometry → cumulative), placed immediately after the "Workflow"
heading and before the numbered stage descriptions — correct placement per `doc_how_to.mdc` §5's
placement guidance (used here in the user guide, where the same rule applies by extension from
`doc_python.mdc`). ✓

No other diagrams or images exist in the docs tree. Appropriate for a prose-and-diagram-only
technical manual. ✓

---

## 9. Change discipline and consistency

**Four-page architecture regression (§6a-6d):** the single highest-impact change-discipline
failure in this repository's documentation. `src/metadata_tools/config.py` was rewritten to fix
issue #112 (per its own docstring), and `CLAUDE.md` was updated to describe the fix accurately,
but the developer guide was never brought into sync. This violates `doc_python.mdc` §7 ("Any
code change MUST update the affected docstrings, narrative pages, and the README in the same
change... NEVER leave stale or contradictory documentation").

**`CONTRIBUTING.md` vs. the actual toolchain — confirmed still stale in this pass:**
`CONTRIBUTING.md:64` says "Follow PEP 8" instead of naming ruff/mypy; `CONTRIBUTING.md:121-124`
documents `cd docs && make html` instead of `scripts/read-docs.sh`; `CONTRIBUTING.md:46-50`'s
commit example (`git commit -m "Add feature: description of your changes"`) does not follow
Conventional Commits and the guide never mentions the `feat:`/`fix:`/`docs:` convention that
`.cursor/rules/git_workflow.mdc` requires; `CONTRIBUTING.md:73` uses the type
`NDArrayFloatType`, confirmed via `grep -rn "NDArrayFloatType" src/ tests/` to not exist
anywhere in this codebase (it appears to be copied from an unrelated project's contributing
guide template). This file is `.. include::`-d directly into `docs/contributing.rst`, so all
four issues are also live on the published docs site.

**Fix:** Rewrite `CONTRIBUTING.md`:
1. Replace line 64 (`* **Python Style**: Follow PEP 8`) with:
   `* **Python Style**: \`ruff check\` (linting) and \`ruff format\` (formatting); \`mypy\` runs in strict mode.`
2. Replace lines 121-124:
   ```
   ```bash
   cd docs
   make html
   ```
   ```
   with:
   ```
   ```bash
   scripts/read-docs.sh
   ```
   ```
   (and update the surrounding prose at line 126 which says "The generated documentation will be
   in `docs/_build/html`" — this is still true and can stay, but note that `read-docs.sh` also
   opens the result in a browser).
3. In the "Development Workflow" section (after step 4, before step 5 at line 46), add a new
   step describing Conventional Commits:
   ```markdown
   5. Use a Conventional Commits subject line (`feat:`, `fix:`, `docs:`, `refactor:`,
      `test:`, `chore:`, `ci:`, ...), 50 characters or fewer, imperative mood:

      ```bash
      git commit -m "fix: correct off-by-one in volume glob matching"
      ```
   ```
   and renumber the subsequent steps.
4. Replace the code example at lines 72-85 (which uses `NDArrayFloatType`) with a real signature
   from this codebase, e.g. adapted from `src/metadata_tools/geometry_support/masks.py`:
   ```python
   def construct_excluded_mask(backplane: Any, target: str, primary: str | None,
                               mask_desc: tuple[str, str, str], *,
                               blocker: str | None = None,
                               ignore_shadows: bool = False) -> polymath.Boolean:
       """Return a mask of excluded pixels for the given target.

       Parameters:
           backplane: The backplane defining the target surface.
           target: The name of the target surface.
           ...

       Returns:
           polymath.Boolean mask; scalar True/False for all-excluded/none-excluded,
           array otherwise.
       """
       ...
   ```
   (abbreviate the `Parameters:` block as shown with `...`; the point of the example is to show
   real, in-repo style, not to reproduce the whole function).

**`_version.py` / `py.typed` comment (unchanged from prior critique, re-verified in this pass):**
`pyproject.toml:82-85` reads:
```toml
# py.typed is intentionally NOT declared: the package is not yet fully annotated, so
# advertising it as typed would mislead downstream type checkers.
...
"py.typed",
```
The comment says `py.typed` is "intentionally NOT declared," but the very next non-comment line
includes `"py.typed"` in `[tool.setuptools.package-data]`, and the marker file
`src/metadata_tools/py.typed` does exist on disk (confirmed via the `git ls-files` listing).
The comment is simply wrong about the current state — the package **is** shipping `py.typed`.
This is in `pyproject.toml`, not `docs/`, but it is exactly the kind of change-discipline gap
this section covers, and it actively misleads a reader of the packaging config who is trying to
understand the project's typing posture (the mypy-strict setup elsewhere in `pyproject.toml`
suggests the package is, in fact, intended to be fully typed).

**Fix:** In `pyproject.toml`, delete or correct the comment at lines 82-84 to match reality,
e.g.:
```toml
# py.typed marks the package as fully type-annotated for downstream type checkers
# (mypy runs in strict mode across src/ and tests/; see [tool.mypy] below).
```

**`util.py` `### move to utilities` comments:** seven functions in `src/metadata_tools/util.py`
carry inline `### move to utilities` / `### add to FCPath?` comments (`pm` at line 113, `smooth`
at line 127, `splitpath` at line 142, `expandvars` at line 310, `read_txt_file` at line 335,
`write_txt_file` at line 366, `append_txt_file` at line 399, `rebase` at line 438). These are
code-organization TODOs, not documentation defects per se, but they represent acknowledged,
unlinked technical debt that `doc_python.mdc`'s spirit (no stale, unowned intent left in the
source) argues should be resolved one way or the other. Not re-detailed here since it overlaps
with the code-critique track's module-size findings; noted for completeness.

**`geometry_support/formats.py` comment perpetuates the same stale script-name convention.**
`src/metadata_tools/geometry_support/formats.py:35-41`:
```python
# Adding a geometry column:
#   1. Add a column definition to a column definition file, e.g. columns/body.py.
#   2. Add a corresponding function to appropriate backplane module.
#   3. Add a row to the format dictionary below.
#   4. Add column description(s) to the label template, e.g., body_summary.lbl.
#   5. Run the host-specific geometry program, e.g., GO_xxxx_geometry.py.
#   6. Update the unit tests.
```
Step 5 names `GO_xxxx_geometry.py`, a script that (per §6 above) does not exist. The correct,
current instructions already exist in `docs/dev_guide/dev_guide_extending.rst`'s "Adding a
geometry column" section, which correctly says "Run the host's geometry program" without naming
a nonexistent script.

**Fix:** In `src/metadata_tools/geometry_support/formats.py:39`, change:
```python
#   5. Run the host-specific geometry program, e.g., GO_xxxx_geometry.py.
```
to:
```python
#   5. Run the host's geometry console script, e.g., metadata-geometry GO_0xxx.
```

**Console-script count consistency:** `user_guide_installation.rst:139` and
`dev_guide_layout.rst` both correctly reflect the ten `[project.scripts]` entries in
`pyproject.toml:119-129`. ✓ (re-verified in this pass, all ten names match exactly)

---

## Recommended priorities

1. **Fix the four-page architecture regression** (§6a-6d: `dev_guide_architecture.rst`,
   `dev_guide_environment.rst`, `dev_guide_extending.rst`, `dev_guide_layout.rst`). This is the
   highest-impact fix — the current text gives a new contributor a command that will fail
   outright, and the underlying architectural claim contradicts the code's own docstrings and
   CLAUDE.md.
2. **Fix `dev_guide_conventions.rst`'s false claim about `ruff format`** (§6) — a one-line, high
   -confidence fix that removes a direct self-contradiction within the same guide.
3. **Fix `CONTRIBUTING.md`** (§9) — stale tooling references, missing Conventional Commits
   guidance, and a type name (`NDArrayFloatType`) that does not exist in this codebase.
4. **Fix the `user_guide_cloud.rst` task-schema example and add `--ssh-paste` documentation**
   (§5) — both are concrete, verifiable mismatches between docs and implemented behavior.
5. **Fix or triage the `geometry_config.py::target_name` docstring** (§2) — determine whether
   the described SKY/CIMS fallback behavior was intentionally removed (doc fix) or accidentally
   lost (functional bug) before editing.
6. **Round out `columns/` docstrings and constants** (§2), fix `source_suffix` (§1), remove
   the "backwards compatible" framing in `_host.py::resolve_task_file` (§1), and add the
   `pipx` note (§5) — all low-risk, independent, low-effort fixes.

---

## Prompt for an AI agent to fix the documentation

```
You are a documentation engineer tasked with fixing the issues identified in the
documentation critique for the `rms-metadata-tools` Python package (package
`metadata_tools`) at /home/spitale/rms-/rms-metadata-tools/. Do not change any
production code behavior — only docstrings, narrative documentation pages,
CONTRIBUTING.md, and comments. Read the `.cursor/rules/doc_*.mdc` files before
making changes; they are the authoritative documentation standards.

**BUILD GATE:** The docs must build clean under BOTH of the following commands
before the work is considered done:
  source venv/bin/activate
  sphinx-build -W -n -b html docs /tmp/sphinx-out
Zero warnings, zero errors. Run this after every batch of changes, not just at
the end.

Do not change any file under tests/. Do not change `pyproject.toml` except for
the `py.typed` comment fix explicitly listed below. When you rename or move any
cross-referenced symbol or page, update every reference to it in the same change
(toctrees, :doc:, :class:, :func:, :meth:, :mod:, :attr:, :data:, :ref: roles).

Fix the following issues in priority order. Each references the exact file,
line numbers, current (wrong) content, and the replacement — apply them exactly
as specified; do not improvise additional rewording beyond what's shown.

### Fix 1 (CRITICAL): Four developer-guide pages describe an obsolete architecture

Context: `src/metadata_tools/config.py`'s own docstring says the engine resolves
host config via `metadata_tools.config.set_host(host_id)`, which does a
package-qualified import of `metadata_tools.hosts.<host_id>.host_config` /
`index_config` (and lazily `geometry_config`) — this works from ANY current
working directory (see the "issue #112" reference in config.py and in
CLAUDE.md's "Config registry" section). There are NO per-host runnable scripts
like `GO_0xxx_index.py` anywhere in `src/metadata_tools/hosts/GO_0xxx/` — only
`host_config.py`, `index_config.py`, `geometry_config.py`, `host_init.py`, and
`__init__.py`. All console-script entry points live in `src/metadata_tools/cli/`
and are invoked as `metadata-index HOST_ID ...` etc. from any directory.

1a. File `docs/dev_guide/dev_guide_architecture.rst`, lines 16-21. Replace the
paragraph starting "The engine never imports a specific host. Instead, the
host's runnable scripts set the current working directory..." through
"...why the documentation build mocks those three module names (see
``docs/conf.py``)." with:

    The engine never imports a specific host's config modules directly (see issue #112).
    Instead, console-script entry points call :func:`metadata_tools.config.set_host`
    once, which package-qualifies the import of ``metadata_tools.hosts.<host_id>.host_config``
    and ``index_config`` (``geometry_config`` is imported lazily, on first use, to avoid
    paying the SPICE startup cost for stages that do not need it). Engine modules then
    call :func:`~metadata_tools.config.get_host_config`,
    :func:`~metadata_tools.config.get_index_config`, and
    :func:`~metadata_tools.config.get_geometry_config` instead of importing those modules
    directly. This works from any current working directory — no ``sys.path`` manipulation
    is involved — and is why the documentation build mocks the three module names as
    plugin-injected surfaces (see ``docs/conf.py``) rather than needing a working directory
    trick.

1b. File `docs/dev_guide/dev_guide_environment.rst`, lines 46-59 (the "Running
the entry points" section, from the heading through the "-vv GO_0017" example
and the sentence about --first 5). Replace the whole section with:

    Running the entry points
    =========================

    Run any console script from any directory; pass the host id as the first
    argument (see :doc:`/user_guide/user_guide_installation`):

    .. code-block:: bash

       metadata-index GO_0xxx "$RMS_VOLUMES/GO_0xxx/" "$RMS_METADATA/GO_0xxx/" \
           "$RMS_METADATA_TEST/GO_0xxx/" --volumes GO_0017

    A fast smoke test is to add ``--first 5`` to the geometry stage so it stops
    after five images. See :doc:`/user_guide/user_guide_examples`.

1c. File `docs/dev_guide/dev_guide_extending.rst`, lines 15-27 (from "#. Copy
the Python modules and the ``<HOST>_*`` scripts..." through "...so they only
resolve when the current working directory is the host directory."). Replace
with:

    #. Create ``src/metadata_tools/hosts/<HOST>/`` (named for the PDS volume set,
       e.g. ``COISS_xxxx``). Copy ``host_config.py``, ``index_config.py``,
       ``geometry_config.py``, ``host_init.py``, and ``__init__.py`` from an existing
       host (e.g. ``GO_0xxx``) as a starting point.
    #. Edit the configuration modules (below) and ``host_init.py``.
    #. Create a ``templates/`` subdirectory, copy the templates, rename them, edit
       ``host_defs.lbl`` and the summary templates, and define the supplemental
       metadata in the supplemental template.

    The configuration modules form the contract the engine relies on. Console-script
    entry points call :func:`metadata_tools.config.set_host` with the host id, which
    package-imports ``metadata_tools.hosts.<HOST>.host_config`` and ``index_config``
    (``geometry_config`` is imported lazily on first use); the engine then reads them
    through :func:`~metadata_tools.config.get_host_config`,
    :func:`~metadata_tools.config.get_index_config`, and
    :func:`~metadata_tools.config.get_geometry_config`. No current-working-directory
    convention is involved.

1d. File `docs/dev_guide/dev_guide_layout.rst`. Delete line 88
(`GO_0xxx_*_cloud.py        # rms-cloud-tasks (GCP) counterparts`) from the host
directory tree. Then replace lines 93-101 (the "GCP deployment files..." section
through the end of that code block) with:

    GCP deployment files live outside the package and are not installed with the wheel:

    .. code-block:: text

       cloud/
         gcp_common_startup.sh     # shared VM bootstrap template
         GO_0xxx/
           gcp_index_config.yml        # GCP machine/queue config for the index stage
           gcp_geometry_config.yml     # GCP machine/queue config for the geometry stage
           gcp_cumulative_config.yml   # GCP machine/queue config for the cumulative stage
           tasks.json                 # example/output task file

    GCP instance startup scripts are generated at runtime by
    :func:`metadata_tools.cli._host.build_startup_script` (invoked by the ``*-cloud``
    entry points, or previewed directly with ``--create-startup-file``); they are never
    stored in the repository.

### Fix 2 (HIGH): dev_guide_conventions.rst false claim about ruff format

File `docs/dev_guide/dev_guide_conventions.rst`, lines 31-33. Replace:

    Maximum line length is 100. The project does not run ``ruff format`` as a gate;
    ``ruff check`` is the linter.

with:

    Maximum line length is 100. ``ruff check`` is the linter and ``ruff format --check``
    enforces formatting (both are run by ``scripts/run-all-checks.sh``); code is
    formatted with ``ruff format`` using single quotes.

### Fix 3 (HIGH): CONTRIBUTING.md is stale

File `CONTRIBUTING.md`.
- Line 64: replace `* **Python Style**: Follow PEP 8` with
  `* **Python Style**: \`ruff check\` (linting) and \`ruff format\` (formatting); \`mypy\` runs in strict mode.`
- Lines 121-124 (the ```bash / cd docs / make html / ``` block): replace with a
  block containing just `scripts/read-docs.sh`.
- After step 4 in the "Development Workflow" numbered list (before the current
  step 5, "Commit your changes..."), insert a new step requiring Conventional
  Commits subject lines (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
  `chore:`, `ci:`), 50 characters or fewer, imperative mood, with an example
  `git commit -m "fix: correct off-by-one in volume glob matching"`. Renumber
  the remaining steps.
- Lines 72-85 (the `calculate_offset` example using `NDArrayFloatType`, which
  does not exist anywhere in this codebase): replace with a real function
  signature and Google-style docstring adapted from
  `src/metadata_tools/geometry_support/masks.py::construct_excluded_mask`
  (read that function first, then adapt a short excerpt as the example).

### Fix 4 (HIGH): user_guide_cloud.rst task schema and --ssh-paste

File `docs/user_guide/user_guide_cloud.rst`.
- Lines 269-280 (the "Task file schema" JSON example): the real format from
  `src/metadata_tools/task_list_support.py::make_task` is
  `{'task_id': f'task-{volume_id}', 'data': {'volume_id': volume_id}}` — replace
  the JSON example's `task_id` values (`"geometry-task-GO_0017"` etc.) with
  `"task-GO_0017"` / `"task-GO_0018"`, and fix the sentence below the block
  (currently claiming the prefix identifies the producing stage) to explain
  that every `task_id` is `task-<volume_id>`, except the single-task cumulative
  run which uses the literal id `cumulative`
  (see :func:`metadata_tools.cli._host.single_task_as_task_file`).
- In the "Cloud-only overrides" list-table (around lines 158-179), add a new
  row documenting `--ssh-paste`: "With ``--create-startup-file``: produce an
  SSH-pastable variant of the script (replaces ``cd /root`` with ``cd ~`` and
  prepends ``set +e`` around the worker command so a failure does not close the
  SSH session). Has no effect without ``--create-startup-file``." Also add a
  short example invocation using `--ssh-paste` after the existing
  `--create-startup-file` example (around line 109).

### Fix 5 (MEDIUM): geometry_config.py::target_name docstring mismatch

File `src/metadata_tools/hosts/GO_0xxx/geometry_config.py`, lines 196-209.
First run `git log -p -- src/metadata_tools/hosts/GO_0xxx/geometry_config.py`
and check whether SKY/CIMS_ID/TARGET_DESC fallback logic was intentionally
removed from `target_name`, since the docstring's second paragraph ("If the
given name is \"SKY\", it checks the CIMS ID and the TARGET_DESC for something
different") describes behavior the current one-line implementation
(`return cast(str, snapshot["TARGET_NAME"])`) does not have.
- If intentionally removed: delete that second paragraph from the docstring.
- If accidentally lost: do NOT edit the docstring to match — instead, stop and
  report this as a probable functional regression rather than a documentation
  issue, since editing the docstring would hide a real bug.

### Fix 6 (MEDIUM): columns/ docstrings

Files `src/metadata_tools/columns/body.py`, `ring.py`, `sky.py`, `sun.py`.
- In `body.py`, expand the one-line docstrings of `get_body_summary_dict`
  (line 100-101) and `get_body_detailed_dict` (line 114-115) to include a
  note that the oops body registry must already be populated, and a
  `Returns:` section describing the dict shape (body name -> column
  description list, BODYX substituted). Use Google-style `Parameters:` /
  `Returns:` sections.
- Add a one-line trailing docstring (string literal immediately after the
  closing bracket, following the pattern already used in
  `src/metadata_tools/defs.py`) to each of these module-level constants:
  `body.py`: BODY_COLUMNS, BODY_GRIDLESS_COLUMNS, BODY_SUMMARY_COLUMNS,
  BODY_DETAILED_COLUMNS, BODY_TILES, BODY_TILE_DICT.
  `ring.py`: RING_COLUMNS, ANSA_COLUMNS, RING_GRIDLESS_COLUMNS,
  RING_SUMMARY_COLUMNS, RING_DETAILED_COLUMNS, RING_TILES, OUTER_RING_TILES,
  RING_TILE_DICT, OUTER_RING_TILE_DICT.
  `sky.py`: SKY_COLUMNS, SKY_TILES.
  `sun.py`: SUN_COLUMNS, SUN_GRIDLESS_COLUMNS, SUN_SUMMARY_COLUMNS,
  SUN_DETAILED_COLUMNS.
  Each docstring is one sentence describing what the constant contains; reuse
  wording from that file's existing module-level docstring where applicable.
- In `sky.py`, delete the `###TODO: not tested...` comment on line 55 (file a
  GitHub issue describing the gap first, and reference the issue number only
  in the commit/PR description, not in the source).

### Fix 7 (LOW, independent, can be done in any order):

- `docs/conf.py` line 101: change `source_suffix = ['.rst', '.md']` to
  `source_suffix = {'.rst': 'restructuredtext', '.md': 'restructuredtext'}`.
- `src/metadata_tools/cli/_host.py` line 90: change the `resolve_task_file`
  docstring from `"""Alias for :func:\`resolve_host_paths\`; kept for backwards
  compatibility."""` to `"""Alias for :func:\`resolve_host_paths\`."""`.
- `docs/user_guide/user_guide_installation.rst`: after the `pip install
  rms-metadata-tools` code block (after line 34), add a `pipx install
  rms-metadata-tools` note as shown in the critique report §5.
- `src/metadata_tools/cli/__init__.py` (currently empty): add the docstring
  `"""Console-script entry points for metadata_tools (see the user guide for usage)."""`.
- `pyproject.toml` lines 82-84: replace the comment claiming `py.typed` is
  "intentionally NOT declared" (which is false — it IS declared at line 85 and
  the marker file exists) with a comment describing the actual mypy-strict,
  fully-typed posture of the package.
- `src/metadata_tools/geometry_support/formats.py` line 39: change
  `#   5. Run the host-specific geometry program, e.g., GO_xxxx_geometry.py.`
  to `#   5. Run the host's geometry console script, e.g., metadata-geometry GO_0xxx.`
- `README.md` lines 59-60: reword the cloud-distribution Features bullet to
  name the `*-worker`, `*-cloud`, and `metadata-task-list` script families
  explicitly instead of only "workers" (see critique report §4 for exact
  wording).

After completing all fixes, run the build gate command:
  source venv/bin/activate && sphinx-build -W -n -b html docs /tmp/sphinx-out

The build must succeed with zero warnings. If it fails, resolve every warning
before considering the work done. Do not proceed to unrelated cleanup beyond
what is listed above.
```
