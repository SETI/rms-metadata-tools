# rms-metadata-tools — Final Analysis Report

**Generated:** 2026-07-14
**Branch:** jns-updates-claude
**Scope:** Every tracked file in the repository was read in full — all 44 `.py` files under
`src/metadata_tools/`, all 12 PDS3 `.lbl` label templates, all 29 test files plus fixtures, every
narrative doc page and every docstring in `src/`, plus packaging, CI, cloud, and tooling config.
Three independent full-repo passes were run (one per sub-report below), each re-verifying every
claim against current file contents rather than trusting the prior critique cycle.
**Sub-reports:** [`code_critique.md`](code_critique.md) · [`tests_critique.md`](tests_critique.md) · [`documentation_critique.md`](documentation_critique.md)

---

## Overall Assessment

`rms-metadata-tools` remains a well-architected, production-quality pipeline: clean `src/` layout,
consistent use of `FCPath`/`PdsLogger`, mypy-strict typing, a Sphinx build that is genuinely
clean (zero warnings under both `-W` and `-n`, verified by actually building the docs), and a
hermetic test suite with real, freshly-measured **93.02% coverage** (the on-disk `.coverage` file's
22% figure, flagged as suspect in the last cycle, is confirmed stale — not a real problem).

Since the last critique cycle, **eleven code findings, one docstring finding, and several test
findings were confirmed fixed** (see "Findings resolved since the last cycle" in each sub-report).
This fresh, independent pass found a smaller but more consequential set of new issues, concentrated
in four clusters:

1. **CI is currently broken.** `tests/test_geometry_constructors.py::test_inventory_other_error_returns_empty`
   fails on the current `main`-bound branch (`ValueError: boom` propagates instead of being
   swallowed) because a prior fix (commit `c680375`) changed `bodies_select.inventory()`'s contract
   without updating the one test that exercises it. This will fail CI on the next push. **Fix this
   first, before anything else in this report.**
2. **A data-correctness bug in cumulative-index generation.** `create_cumulative_indexes()` builds
   its own `args.exclude` from the `--exclude` CLI flag but then never uses it — every call site
   either passes a separately-supplied `exclude=` parameter (silently discarding what the user
   typed on the command line) or, on the worker/cloud path, passes no `exclude=` at all (silently
   discarding the host's configured default). No test currently catches this.
3. **A stale-documentation architecture regression.** Four developer-guide pages still describe
   the pre-issue-#112 design where a host's scripts only run from inside the host's own directory,
   including a literal example command (`python GO_0xxx_index.py ...`) that references a script
   that does not exist anywhere in `src/`. The actual code (`config.py`, referencing issue #112 in
   its own docstring) was fixed; the docs were not.
4. **Two shipped-and-untested features and a small cluster of dead/half-wired code**: the `.env`
   `$VAR`-expansion loader and `defs.set_translations()`/`_translations` target-name mapping
   (both new since the last cycle) have zero test coverage; `set_translations()` itself is never
   called anywhere, making the whole mechanism permanently inert; a `Table.__init__` `prefix`
   parameter is accepted and silently discarded; an `is None`-vs-truthy bug in the index
   "unused columns" accumulator can corrupt a multi-volume run's warning output; the same bug
   pattern (truthy vs. `is not None`) in `IndexTable._get_null_value()` can turn a legitimate `0`
   null constant into a hard crash.

---

## Unified Priority List

Priorities are cross-cutting across code, tests, and docs. Items within the same severity tier are
listed in impact × effort order. Each item's originating sub-report and finding ID is given so the
full evidence and self-contained fix can be looked up directly.

### CRITICAL / Immediate — do these before anything else

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| C1 | Tests | Suite currently fails: `test_inventory_other_error_returns_empty` asserts the pre-`c680375` contract; `bodies_select.inventory()` now correctly re-raises. **Blocks CI on next push.** | `tests/test_geometry_constructors.py:47-55` | 15 min |
| C2 | Code | `create_cumulative_indexes()` ignores `args.exclude` from `--exclude` everywhere, and ignores the host's `exclude` default entirely on the worker/cloud path — real data-generation correctness bug | `src/metadata_tools/cumulative_support.py:137-183`, `cli/cumulative.py:27`, `cli/cumulative_worker.py:39-40` | 1-2 hours incl. regression test |

### HIGH / This sprint

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| H1 | Code | `key__on_chip_mosaic_flag()` returns `'Y'` for SL9 override; label documents `'YES'`/`'NO'` domain — produces incorrect published data | `src/metadata_tools/hosts/GO_0xxx/index_config.py:214-246` | 30 min |
| H2 | Code | `IndexTable._get_null_value()` uses a truthy check; a null constant of `0` (e.g. `PRODUCT_VERSION_ID`) is skipped, causing a hard `ValueError` crash downstream | `src/metadata_tools/index_support/table.py:288-313` | 30 min |
| H3 | Code | `_create_index()`'s unused-columns accumulator uses `not unused` instead of `unused is None`; corrupts the running intersection once it legitimately becomes empty on multi-volume runs | `src/metadata_tools/index_support/process.py:83-118` | 15 min |
| H4 | Code | `defs._translations`/`set_translations()` is completely unwired dead code — never called anywhere, so the lookup in `record.py` can never fire | `src/metadata_tools/defs.py:34-46`, `geometry_support/record.py:75-76` | 30 min – 1 day (needs intent investigation) |
| H5 | Code | `geometry_config.target_name()`'s docstring describes SKY/CIMS-ID fallback logic the one-line implementation does not have — lost functionality or stale docstring | `src/metadata_tools/hosts/GO_0xxx/geometry_config.py:196-209` | 15 min – 1 hour (needs investigation) |
| H6 | Docs | Four dev-guide pages describe the pre-issue-#112 architecture and give a literally broken example command | `docs/dev_guide/dev_guide_architecture.rst`, `dev_guide_environment.rst`, `dev_guide_extending.rst`, `dev_guide_layout.rst` | 1-2 hours |
| H7 | Docs | `CONTRIBUTING.md` stale: PEP 8 instead of ruff/mypy, wrong docs-build command, no Conventional Commits guidance, references a nonexistent `NDArrayFloatType` type | `CONTRIBUTING.md` | 30 min |
| H8 | Docs | `user_guide_cloud.rst`'s task-file JSON example shows the wrong `task_id` format, and the `--ssh-paste` CLI flag is undocumented | `docs/user_guide/user_guide_cloud.rst` | 30 min |
| H9 | Tests | Zero `@pytest.mark.parametrize` uses across 304 tests; `test_cli_host.py` alone has 20 near-identical `build_startup_script` tests (grew from 10 last cycle) | `tests/test_cli_host.py` | 2-4 hours |
| H10 | Tests | Two features shipped in commit `f344683` have zero test coverage: `.env` `$VAR`-expansion loader, and `defs.set_translations()`/the `Record.__init__` translation branch | `src/metadata_tools/__init__.py`, `defs.py`, `geometry_support/record.py` | 1-1.5 hours (coordinate with H4) |

### MEDIUM / Next two sprints

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| M1 | Code | `bodies_select.inventory()`'s first `except` block still swallows non-SPICE `RuntimeError`/`OSError` instead of re-raising (the second `except` block was already fixed) | `src/metadata_tools/geometry_support/bodies_select.py:37-61` | 15 min |
| M2 | Code | `Table.__init__`'s `prefix` parameter is accepted, assigned, then unconditionally overwritten before use — dead, misleading constructor argument | `src/metadata_tools/common.py:135-170` | 15 min |
| M3 | Code | `Suite.create()` raises a confusing `AttributeError` (not a clear validation error) when `--selection` matches no processing level | `src/metadata_tools/geometry_support/suite.py:63-69,224-225`, `cli/process.py` (`get_args`) | 30-45 min |
| M4 | Code | Three job-state `.db` files tracked in git despite a `.gitignore` pattern that should exclude them (added after they were already tracked) | `src/metadata_tools/metadata-{index,geometry,cumulative}-job.db`, `.gitignore` | 5 min — confirm with user before `git rm --cached` |
| M5 | Code | `--new_only`/`-n` accepts a list of volume names via `nargs='*'` but the values are never read — silently discarded | `src/metadata_tools/geometry_support/process.py:45-47,90,136` | 15-30 min |
| M6 | Code | `vulture` config excludes `tests/` in `pyproject.toml` but both `run-all-checks.sh` and CI pass `tests` explicitly as a positional path, so the exclude has no effect | `pyproject.toml`, `scripts/run-all-checks.sh`, `.github/workflows/run-tests.yml` | 5 min |
| M7 | Code | CI publishes to PyPI with a long-lived `PYPI_API_TOKEN` instead of OIDC Trusted Publishers | `.github/workflows/publish_to_pypi.yml` | 30 min |
| M8 | Code | `index_support/__init__.py` exports the private `_create_index` via `__all__`, contradicting the private-prefix convention | `src/metadata_tools/index_support/__init__.py:20-27` | 10 min |
| M9 | Code | `util.py` still mixes SCLK/IO/math concerns with nine unresolved `### move to utilities` markers (a prior split attempt was reverted — check `44e23e4` before retrying) | `src/metadata_tools/util.py` | 2-4 hours |
| M10 | Code | Functions exceeding 3 positional args unchanged: `Table.__init__` (8), `Suite.__init__` (9) | `src/metadata_tools/common.py:135`, `geometry_support/suite.py:27` | 2-4 hours (bundle with M2) |
| M11 | Code | `read-docs.sh` builds without `-n` (nitpicky) unlike CI and `run-all-checks.sh` — a locally-clean build can fail in CI | `scripts/read-docs.sh:39` | 5 min |
| M12 | Docs | `dev_guide_conventions.rst` falsely claims `ruff format` is not run as a gate, contradicting another page in the same guide, CLAUDE.md, and `run-all-checks.sh` | `docs/dev_guide/dev_guide_conventions.rst` | 10 min |
| M13 | Docs | `geometry_config.py::target_name` docstring/implementation mismatch — same root cause as code finding H5; fix once, in the code critique's chosen direction | `src/metadata_tools/hosts/GO_0xxx/geometry_config.py` | (tracked under H5) |
| M14 | Tests | `cli/_host.py`'s `load_host`, `host_dir_for`, `cloud_dir_for`, `dispatch_cloud_run_if_config`, `run_cloud_worker` remain completely untested | `tests/test_cli_host.py` | 1.5-2 hours |
| M15 | Tests | `pop_argv_flag`'s `SystemExit` assertion still has no `match=` | `tests/test_cli_host.py` | 5 min |
| M16 | Tests | Bare `print()` calls left in archive/integration test bodies | `tests/test_geometry.py`, `test_index.py`, `tests/hosts/GO_0xxx/test_*.py` | 15 min |
| M17 | Tests | `np.random.seed(0)` leaks global random state instead of an isolated RNG | `tests/test_util_math.py:127` | 15 min |
| M18 | Tests | `test_create_cumulative_indexes_fires_eight_cat_rows` and a `_cat_rows` `volumes=` filter test are still missing — directly relevant to fixing C2 above | `tests/test_cumulative_support.py` | 30 min |

### LOW / Backlog

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| L1 | Code | `events.log` runtime artifacts present under `src/metadata_tools/` (gitignored but should be relocated) | `src/metadata_tools/events.log`, `hosts/GO_0xxx/events.log` | varies |
| L2 | Code | Duplicated terminator-normalization logic between `write_txt_file`/`append_txt_file` | `src/metadata_tools/util.py:365-435` | 20 min |
| L3 | Code | Commented-out `SunTable` registration — decide keep-and-test or delete-and-track | `src/metadata_tools/geometry_support/suite.py:161,178` | 30 min – 1 hour |
| L4 | Code | `sclk_to_ticks` annotated `-> Any`; should be `-> float` with an explicit `cast` | `src/metadata_tools/util.py:520` | 15 min |
| L5 | Code | `SKY_TILES` still marked `###TODO: not tested` in library code | `src/metadata_tools/columns/sky.py:55-56` | 30 min |
| L6 | Code | `_mission_table_cache` / `_BODIES` / `_BODY_SUMMARY_DICT` global caches undocumented as non-thread-safe | `geometry_support/formats.py:124`, `bodies.py:32-47`, `columns/body.py:96-118` | 15 min |
| L7 | Code | `index_support/table.py`'s `.exists()` pre-check still violates `filecache.mdc` | `src/metadata_tools/index_support/table.py:82-84` | 20 min |
| L8 | Code | No `pip-audit` step in CI | `.github/workflows/run-tests.yml` | 15 min |
| L9 | Code | CI tests only `ubuntu-latest`; `pyproject.toml` classifiers still claim macOS/Windows | `.github/workflows/run-tests.yml`, `pyproject.toml` | 15 min – varies if enabled |
| L10 | Code | Two copy-pasted typos in shipped PDS3 label `DESCRIPTION` text (stray comma; missing word "identifier") | `hosts/GO_0xxx/templates/GO_0xxx_body_summary.lbl:83`, `GO_0xxx_ring_summary.lbl:78`, `GO_0xxx_supplemental_index.lbl:47-48` | 10 min |
| L11 | Code | Untracked Kate editor swap file in the working tree; no `.gitignore` pattern for editor swap files | `src/metadata_tools/cli/.index_cloud.py.kate-swp` | 2 min — confirm with user before deleting |
| L12 | Code | `CLAUDE.md`'s architecture description is stale relative to the (currently uncommitted) lazy `geometry_config` loading in `config.py`; also references a nonexistent `requirements-cloud.txt` | `CLAUDE.md` | 15 min |
| L13 | Code | `local_scheme = "no-local-version"` suppresses dev-build version suffixes (likely intentional for PyPI) | `pyproject.toml:87` | none — verify intent only |
| L14 | Docs | `CONTRIBUTING.md`/columns modules: undocumented module-level column constants; two `columns/body.py` functions with thin one-line docstrings | `src/metadata_tools/columns/{body,ring,sky,sun}.py` | 30-45 min |
| L15 | Docs | `docs/conf.py`'s `source_suffix` still list form instead of dict form | `docs/conf.py` | 5 min |
| L16 | Docs | `_host.py::resolve_task_file` still carries "kept for backwards compatibility" framing `doc_python.mdc` forbids | `src/metadata_tools/cli/_host.py` | 5 min |
| L17 | Docs | No `pipx install` note in the installation guide | `docs/user_guide/user_guide_installation.rst` | 10 min |
| L18 | Docs | `cli/__init__.py` is an empty file with no module docstring | `src/metadata_tools/cli/__init__.py` | 5 min |
| L19 | Docs | No dedicated how-to articles exist (`doc_how_to.mdc` checklist has nothing to critique against) | `docs/user_guide/` | 2-4 hours if pursued |
| L20 | Tests | Several existence-only assertions could be strengthened to exact-value checks (e.g. `test_record_add_named_column_dict`, `test_detailed_subregions_emit_rows`) | `tests/test_geometry_tables.py`, `test_geometry_prep.py` | 15 min |
| L21 | Tests | No direct unit tests for `tests/archive_support.py` helper functions themselves | `tests/archive_support.py` | 30 min |

---

## Recommended Work Sequence

### Wave 0 — Unblock CI (do first, 15 minutes)

1. **C1** — Fix `test_inventory_other_error_returns_empty` to assert the current, intended contract
   (exception propagates). See `critiques/tests_critique.md` Fix 1 for the exact replacement test.

### Wave 1 — Data-correctness bugs (2-3 hours total)

2. **C2** — Fix `create_cumulative_indexes()`'s dropped `exclude` argument; add the regression test
   from **M18** in the same change.
3. **H1** — Fix `key__on_chip_mosaic_flag()`'s `'Y'` → `'YES'`.
4. **H2** — Fix `_get_null_value()`'s truthy check.
5. **H3** — Fix the unused-columns accumulator's `not unused` → `unused is None`.

### Wave 2 — Investigate-then-fix (needs a decision before editing, 1-3 hours)

6. **H4** — Determine whether `defs._translations` is needed for GO_0xxx; wire it up via
   `host_init.py` or delete it.
7. **H5** — Determine whether `target_name()`'s SKY/CIMS-ID logic was lost or never real; fix the
   code or the docstring accordingly (resolves **M13** too).
8. **M3** — Add `--selection` argument validation and a `Suite.tables` default.

### Wave 3 — Documentation accuracy (2-3 hours)

9. **H6** — Rewrite the four dev-guide pages describing the pre-#112 architecture.
10. **H7** — Fix `CONTRIBUTING.md`.
11. **H8** — Fix the `user_guide_cloud.rst` task schema and add `--ssh-paste` docs.
12. **M12** — Fix `dev_guide_conventions.rst`'s `ruff format` claim.

### Wave 4 — Test suite hardening (4-6 hours)

13. **H9** — Parametrize `test_cli_host.py`'s 20 near-identical `build_startup_script` tests.
14. **H10** — Add tests for the `.env` loader and translation mapping (coordinate with H4's outcome).
15. **M14/M15/M16/M17/M18** — Untested `_host.py` functions, `match=` assertion, stray `print()`s,
    RNG isolation, cumulative call-set assertions.

### Wave 5 — Hygiene and polish (ongoing, low risk)

16. **M4/L11** — `git rm --cached` the tracked `.db` files and delete the stray `.kate-swp` file
    (confirm with the user first — both are destructive git/file operations).
17. **M2/M10** — Remove the dead `Table.prefix` parameter; consider the config-object refactor.
18. **M5/M6/M7/M8/M11** — CLI flag fix, vulture config, Trusted Publishers, `__all__` cleanup,
    `read-docs.sh` nitpicky flag.
19. **L1-L21** — Remaining low-effort/low-risk items, tackled opportunistically.

---

## Per-critique Index

- **Code analysis** → [`critiques/code_critique.md`](code_critique.md)
  — 1 Critical, 8 High, 11 Medium, 9 Low (29 findings) across 10 dimensions, plus a
  "Findings resolved since the last cycle" section (14 items independently re-verified fixed).
  Every `.py` file under `src/`, all 12 `.lbl` templates, and all packaging/CI/cloud config read
  in full.

- **Test suite critique** → [`critiques/tests_critique.md`](tests_critique.md)
  — 23 sections + an 18-fix "Prompt for an AI agent to fix tests." All 29 test files read in full;
  coverage freshly measured at 93.02%; one currently-failing test identified and given the
  first fix in the prompt.

- **Documentation critique** → [`critiques/documentation_critique.md`](documentation_critique.md)
  — 9 sections + a 7-fix "Prompt for an AI agent to fix the documentation." Every doc page and
  every docstring in `src/` read in full; Sphinx build actually run under `-W`, `-n`, and `-W -n`
  combined (zero warnings in all three).

The AI-agent prompt at the end of each sub-report is a stand-alone brief that a fresh AI agent
(with no prior context) can use to apply all fixes described in that critique without reading this
synthesis document. **Start with `critiques/tests_critique.md` Fix 1 — it is the only item in this
report that is actively breaking CI right now.**
