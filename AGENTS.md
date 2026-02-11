# AGENTS Guide
This file is for coding agents working in this repository.
It consolidates build/lint/test commands and coding conventions.

## Project Snapshot
- Python `>=3.12`
- Workspace manager/runner: `uv`
- Multi-module layout: `packages/*` and `apps/*`
- Shared package: `packages/common/src/shared`
- Example app: `apps/example/src/example`
- Integration tests: top-level `tests/`

## Important Files
- `pyproject.toml` (workspace + pytest config)
- `ruff.toml` (lint + format)
- `mypy.ini` (strict typing)
- `packages/common/pyproject.toml`
- `apps/example/pyproject.toml`

## Setup
Run from repository root:
```bash
uv sync
```

## Build/Lint/Test Commands
Primary quality commands:
```bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
uv run pytest
```
There is no separate compile step for normal Python changes.

## Single Test Commands (Key)
Run one test file:
```bash
uv run pytest packages/common/tests/test_common.py
uv run pytest apps/example/tests/test_main.py
uv run pytest tests/test_integration.py
```
Run one specific test function by node ID:
```bash
uv run pytest packages/common/tests/test_common.py::test_greeting
uv run pytest apps/example/tests/test_main.py::test_main
uv run pytest tests/test_integration.py::test_integration
```
Run by keyword expression:
```bash
uv run pytest -k greeting
uv run pytest -k "greeting and not integration"
```
Verbose single-test debug run:
```bash
uv run pytest -v apps/example/tests/test_main.py::test_main
```

## Run the Example App
```bash
uv run python -m example.main
```
Expected output includes `Hello, World!`.

## Docker Commands
```bash
docker build -f apps/example/Dockerfile -t example:latest .
docker run --rm example:latest
docker-compose up
docker-compose down
```

## Pytest Configuration Notes
From root `pyproject.toml`:
- `testpaths = ["packages", "apps", "tests"]`
- `pythonpath = ["packages/common/src", "apps/example/src"]`
- `addopts = "--tb=short -q --no-header --import-mode=importlib"`
- `python_files = ["test_*.py", "*_test.py"]`
- `python_classes = ["Test*"]`
- `python_functions = ["test_*"]`

## Formatting and Linting Rules
From `ruff.toml`:
- Target Python: `py312`
- Max line length: `88`
- Quote style: double quotes
- Indentation: spaces
- Import sorting enabled (`I` rules)
- Naming checks enabled (`N` rules)
Enabled lint families:
- `E`, `F`, `W`
- `I`
- `UP`
- `B`
- `SIM`
- `N`
- `RUF`

## Import Conventions
- Prefer absolute imports from workspace packages.
- Example: `from shared.utils import greeting`
- Keep imports at module top unless lazy import is necessary.
- Let Ruff control ordering/grouping.
- Remove unused imports.

## Type System Rules
`mypy.ini` enables strict mode (`strict = True`).
- Type annotate new/changed function parameters and returns.
- Avoid implicit `Any`.
- Avoid unnecessary `# type: ignore`.
- Keep `warn_unused_ignores` and `warn_return_any` clean.
- Keep imports compatible with `mypy_path`.

## Naming Conventions
- Modules/packages: `snake_case`
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`

## Comments and Docstrings
- Use concise docstrings for non-trivial public behavior.
- Add comments only for non-obvious logic.
- Do not add comments that simply restate code.
- Keep text clear and direct.

## Error Handling
- Raise specific exception types.
- Exception messages must be in English.
- Do not swallow exceptions silently.
- Avoid bare `except:`.
- Catch precise exceptions and re-raise with context if needed.

## Testing Expectations
- Add or update tests for behavior changes.
- Prefer deterministic tests with explicit assertions.
- Keep module tests near each module (`packages/.../tests`, `apps/.../tests`).
- Use top-level `tests/` for cross-module integration coverage.

## Adding New Packages/Apps
- Create package in `packages/*` or app in `apps/*`.
- Add module-level `pyproject.toml`.
- Register workspace sources in root `pyproject.toml` when needed.
- Update `mypy.ini` `mypy_path` for new `src` directories.
- Run `uv sync` after dependency/workspace edits.

## Agent Pre-Submit Checklist
Run before handing off:
```bash
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
```
For quick loops, run at least impacted single-test node IDs.

## Cursor/Copilot Rules
Checked for:
- `.cursor/rules/`
- `.cursorrules`
- `.github/copilot-instructions.md`
Current repository state: none of these files exist.
If added later, incorporate their constraints into this guide.

## Active Technologies
- Python 3.12 + Typer (CLI), Pydantic v2, SQLAlchemy 2.x, psycopg, Alembic, OpenAIClient (OpenAI API) (001-whatsapp-split-reconciliation)
- PostgreSQL 16 (historico completo, append-only para runs e fechamentos versionados) (001-whatsapp-split-reconciliation)

## Recent Changes
- 001-whatsapp-split-reconciliation: Added Python 3.12 + Typer (CLI), Pydantic v2, SQLAlchemy 2.x, psycopg, Alembic, OpenAIClient (OpenAI API)
