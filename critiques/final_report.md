# rms-metadata-tools — Final Analysis Report

**Generated:** 2026-07-13
**Branch:** jns-updates-claude
**Scope:** All source files, tests, docs, cloud config, and tooling.
**Sub-reports:** [`code_critique.md`](code_critique.md) · [`tests_critique.md`](tests_critique.md) · [`documentation_critique.md`](documentation_critique.md)

---

## Overall Assessment

`rms-metadata-tools` is a well-architected, production-quality planetary-science pipeline with clear
module boundaries, consistent use of project-specific conventions (`FCPath`, `PdsLogger`), a passing
Sphinx build (zero warnings), and a broadly hermetic test suite that runs without SPICE or archive
data. The `src/` layout, mypy-strict enforcement, `filterwarnings = ["error"]`, and `--strict-markers`
all represent best-practice adoption.

The remaining issues are concentrated in four clusters:

1. **Data-correctness risk** — a duplicate tile in `OUTER_RING_TILES` silently writes duplicate rows
   into every outer-ring detailed geometry file (no test catches it).
2. **Platform robustness** — six file-open calls lack `encoding='utf-8'`, which will break silently
   on non-UTF-8 platforms.
3. **Test suite gaps** — zero `@pytest.mark.parametrize` uses across 290 tests, several missing
   `match=` assertions, and stale coverage reporting (the `.coverage` file on disk shows 22 %, almost
   certainly pre-dating many recently added test modules; a fresh run is required).
4. **Stale documentation** — `CONTRIBUTING.md` references PEP 8 instead of ruff/mypy and the wrong
   docs-build command; `dev_guide_layout.rst` describes a cloud setup that was replaced by
   runtime startup-script generation.

---

## Unified Priority List

Priorities are cross-cutting across code, tests, and docs. Items within the same severity tier are
listed in impact × effort order.

### CRITICAL / Immediate

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| C1 | Code | Duplicate tile in `OUTER_RING_TILES` silently produces duplicate rows in every outer-ring geometry file | `src/metadata_tools/columns/ring.py:170` | 30 min |
| C2 | Code | Broad exception catch in `bodies_select.inventory()` swallows programming errors as SPICE failures | `src/metadata_tools/geometry_support/bodies_select.py` | 45 min |

### HIGH / This Sprint

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| H1 | Code | Six `open()`/`read_text()`/`write_text()` calls without `encoding='utf-8'` | `__init__.py:28`, `cli/_host.py:182,261`, `cli/geometry_cloud.py:83`, `cli/index_cloud.py:80`, `cli/cumulative_cloud.py:70` | 30 min |
| H2 | Code | `locals()['link_' + link]` dynamic lookup in `record.py:postprocess()` — refactoring-fragile, untype-checkable | `src/metadata_tools/geometry_support/record.py:210` | 30 min |
| H3 | Code | `from None` discards exception chain in `index_config.py:120` | `src/metadata_tools/hosts/GO_0xxx/index_config.py:120` | 5 min |
| H4 | Code | `except_test()` always returns `False` — dead stub or unimplemented filter | `src/metadata_tools/hosts/GO_0xxx/geometry_config.py:96` | 15 min |
| H5 | Code | CI lint runs only on Python 3.13 (`if: matrix.python-version == '3.13'` condition) | `.github/workflows/run-tests.yml` | 5 min |
| H6 | Tests | Run fresh coverage measurement — stale `.coverage` reports 22 % which almost certainly does not reflect recent test additions | `tests/` | 15 min (measurement) |
| H7 | Tests | Zero `@pytest.mark.parametrize` uses across 290 tests — ~12 groups of copy-pasted nearly-identical tests | `tests/test_config.py`, `test_util_*.py`, `test_geometry_masks.py`, `test_geometry_formatting.py`, `test_cli_host.py` | 2–4 hours |
| H8 | Docs | Fix `CONTRIBUTING.md` — replace PEP 8 ref with ruff/mypy, fix docs-build command, add Conventional Commits, replace non-existent `NDArrayFloatType` example | `CONTRIBUTING.md` | 30 min |
| H9 | Docs | Fix stale cloud layout in `dev_guide_layout.rst` — remove `generate_startup_scripts.py`, `gcp_*_startup.sh`, `gcp_*_startup.tail.sh`; document runtime generation | `docs/dev_guide/dev_guide_layout.rst` | 20 min |
| H10 | Docs | Rename `Args:` → `Parameters:` in two `_host.py` docstrings | `src/metadata_tools/cli/_host.py` | 5 min |

### MEDIUM / Next Two Sprints

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| M1 | Code | `vulture` config/script inconsistency: `pyproject.toml` excludes `tests/` but `run-all-checks.sh` passes `tests` explicitly | `pyproject.toml`, `scripts/run-all-checks.sh` | 5 min |
| M2 | Code | `TRANSLATIONS: dict[str, str] = {}` mutable module-level "constant" without locking documentation | `src/metadata_tools/defs.py:34` | 15 min |
| M3 | Code | `exists()` pre-checks violate `filecache.mdc` (TOCTOU, cloud-path incompatible) | `src/metadata_tools/label_support.py:34`, `index_support/table.py:83` | 30 min |
| M4 | Code | Functions with ≥6 positional parameters (`Table.__init__`, `Suite.__init__`, `build_startup_script`, `dispatch_cloud_run_if_config`) | `common.py`, `geometry_support/suite.py`, `cli/_host.py` | 2–4 hours |
| M5 | Code | Module-level eager loops in `columns/body.py` and `columns/ring.py` run at import; `lru_cache` would defer and deduplicate | `src/metadata_tools/columns/body.py`, `columns/ring.py` | 1 hour |
| M6 | Code | `type(leaf) in (tuple, list)` should use `isinstance()` | `src/metadata_tools/util.py:209` | 5 min |
| M7 | Code | `list(outdir.glob(...)) != []` materializes full list just to check emptiness | `src/metadata_tools/geometry_support/process.py:136` | 5 min |
| M8 | Code | CI uses long-lived `PYPI_API_TOKEN`; migrate to OIDC Trusted Publishers | `.github/workflows/publish_to_pypi.yml` | 30 min |
| M9 | Tests | Add `match=` to bare `pytest.raises(SystemExit)` at `test_cli_host.py:48` | `tests/test_cli_host.py:48` | 5 min |
| M10 | Tests | Extract shared `startup_tpl` fixture from 10 near-identical `test_build_startup_*` tests | `tests/test_cli_host.py:141–304` | 30 min |
| M11 | Tests | Add `dispatch_cloud_run_if_config` and `run_cloud_worker` tests (subprocess mock) | `tests/test_cli_host.py` | 1 hour |
| M12 | Tests | Add `load_host` tests (strips sys.argv, exits on unknown host) | `tests/test_cli_host.py` | 20 min |
| M13 | Tests | Add `_cat_rows` volumes-filter test | `tests/test_cumulative_support.py` | 20 min |
| M14 | Tests | Add exact call-set assertion to `test_create_cumulative_indexes_fires_eight_cat_rows` | `tests/test_cumulative_support.py:111` | 10 min |
| M15 | Tests | `np.random.seed(0)` leaks global random state; use `np.random.default_rng(0)` | `tests/test_util_math.py:127` | 15 min |
| M16 | Tests | Remove bare `print()` from archive test bodies | `tests/test_geometry.py`, `test_index.py`, `tests/hosts/GO_0xxx/test_*.py` | 15 min |
| M17 | Docs | Add `Parameters:`/`Returns:` to `get_body_summary_dict` / `get_body_detailed_dict`; add constant docstrings to `columns/*.py` | `src/metadata_tools/columns/body.py`, `ring.py`, `sky.py`, `sun.py` | 30 min |

### LOW / Backlog

| # | Cluster | Finding | Files | Effort |
|---|---------|---------|-------|--------|
| L1 | Code | `py.typed` ships but comment says it is "intentionally NOT declared" — resolve contradiction | `pyproject.toml:82–85` | 5 min |
| L2 | Code | `_version.py` auto-generated by setuptools-scm; should be in `.gitignore` | `.gitignore` | 5 min |
| L3 | Code | `events.log` runtime artifacts in `src/` — configure cloud-tasks to write outside source tree | `src/metadata_tools/events.log` | varies |
| L4 | Code | `util.py` 830-line mixed-concern module; eight `### move to utilities` TODOs | `src/metadata_tools/util.py` | 2–4 hours |
| L5 | Code | Commented-out `SunTable` in `suite.py:178` | `src/metadata_tools/geometry_support/suite.py:178` | 5 min |
| L6 | Code | `sclk_to_ticks` annotated `-> Any`; replace with concrete return type | `src/metadata_tools/util.py` | 15 min |
| L7 | Code | Global `_BODIES` / `_BODY_SUMMARY_DICT` lazy-init without thread-safety doc | `src/metadata_tools/bodies.py`, `columns/body.py` | 10 min (comment) |
| L8 | Code | `_mission_table_cache` module-level cache undocumented | `src/metadata_tools/geometry_support/formats.py` | 5 min |
| L9 | Code | CI tests only `ubuntu-latest` but `pyproject.toml` classifiers claim macOS and Windows | `.github/workflows/run-tests.yml`, `pyproject.toml` | 15 min |
| L10 | Code | No `pip audit` step in CI | `.github/workflows/run-tests.yml` | 15 min |
| L11 | Tests | `test_columns_integration.py:test_body_summary_dict_is_populated` asserts `len > 0` instead of exact key set | `tests/columns/test_columns_integration.py` | 10 min |
| L12 | Tests | `test_record_add_named_column_dict` uses `endswith` instead of exact match | `tests/test_geometry_tables.py:130` | 5 min |
| L13 | Tests | `test_detailed_subregions_emit_rows` asserts `.isdigit()` instead of exact value `'0'` | `tests/test_geometry_prep.py:183` | 5 min |
| L14 | Tests | Add `pytest-timeout` to dev dependencies for archive/integration tests | `pyproject.toml` | 10 min |
| L15 | Tests | Log the `--randomly-seed` value in CI so failing runs can be reproduced | `.github/workflows/run-tests.yml` | 10 min |
| L16 | Docs | `user_guide_installation.rst` should mention `pipx install rms-metadata-tools` | `docs/user_guide/user_guide_installation.rst` | 10 min |
| L17 | Docs | `source_suffix = [...]` in `conf.py` should be dict form | `docs/conf.py` | 5 min |
| L18 | Docs | Remove "kept for backwards compatibility" from `resolve_task_file` docstring | `src/metadata_tools/cli/_host.py` | 5 min |
| L19 | Docs | Consider converting `user_guide_examples.rst` and `dev_guide_extending.rst` to structured how-to articles | `docs/` | 2–4 hours |

---

## Recommended Work Sequence

The table below groups issues by the order they should be addressed, independent of who works on
each. Items in the same wave can be tackled in parallel.

### Wave 1 — Safety and correctness (1–2 hours total)

1. **C1** — Fix duplicate tile in `OUTER_RING_TILES` (`columns/ring.py:170`). Add uniqueness test.
2. **H1** — Add `encoding='utf-8'` to six file-open calls.
3. **H3** — Remove `from None` in `index_config.py:120`.
4. **H5** — Remove `if: matrix.python-version == '3.13'` from CI lint gate.
5. **H6** — Run `pytest --cov=src --cov-report=term-missing -n auto` and record the true coverage.

### Wave 2 — Robustness and maintainability (2–4 hours total)

6. **H2** — Replace `locals()['link_' + link]` with explicit dispatch dict in `record.py`.
7. **C2** — Narrow broad exception catch in `bodies_select.inventory()`.
8. **H4** — Resolve `except_test()` stub (document, raise, or delete).
9. **H8** — Fix `CONTRIBUTING.md` (ruff/mypy, docs command, Conventional Commits).
10. **H9** — Fix `dev_guide_layout.rst` cloud section.
11. **H10** — Rename `Args:` → `Parameters:` in `_host.py`.

### Wave 3 — Test suite quality (3–5 hours)

12. **H7** — Add `@pytest.mark.parametrize` to the 12 copy-pasted test groups.
13. **M9** — Add `match=` to `pytest.raises(SystemExit)` in `test_cli_host.py:48`.
14. **M10** — Extract `startup_tpl` fixture.
15. **M11 / M12** — Add `dispatch_cloud_run_if_config`, `run_cloud_worker`, `load_host` tests.
16. **M13 / M14** — Add `_cat_rows` volumes filter test; strengthen cumulative-indexes call-set assertion.
17. **M16** — Remove `print()` from archive test bodies.
18. **L12 / L13** — Strengthen `endswith` and `.isdigit()` assertions.

### Wave 4 — Code hygiene (ongoing, low risk)

19. **M5 / M6 / M7** — `lru_cache` eager loops, `isinstance`, glob check.
20. **M3** — Replace `exists()` pre-checks with try/except.
21. **L1 / L2** — Resolve `py.typed` comment; add `_version.py` to `.gitignore`.
22. **L4** — Plan and execute `util.py` split (create tracking issue first).

### Wave 5 — Documentation polish (1–2 hours)

23. **M17** — Add column docstrings to `columns/` package.
24. **L16 / L17 / L18** — `pipx` note, `source_suffix` dict form, remove backwards-compat note.
25. **L19** — Consider converting key workflows to `doc_how_to.mdc` structured articles.

---

## Per-critique Index

For the complete findings, code snippets, and self-contained fix instructions, see:

- **Code analysis** → [`critiques/code_critique.md`](code_critique.md)
  — 32 findings across 10 dimensions; each High/Critical item includes before/after code snippets.

- **Test suite critique** → [`critiques/tests_critique.md`](tests_critique.md)
  — 23 sections + a fully self-contained "Prompt for an AI agent to fix tests" (§ at end of file).

- **Documentation critique** → [`critiques/documentation_critique.md`](documentation_critique.md)
  — 9 sections + a fully self-contained "Prompt for an AI agent to fix the documentation" (§ at end of file).

The AI-agent prompt at the end of each sub-report is a stand-alone brief that a fresh AI agent
(with no prior context) can use to apply all fixes described in that critique without reading this
synthesis document.
