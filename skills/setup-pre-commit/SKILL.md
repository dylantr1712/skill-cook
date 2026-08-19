---
name: setup-pre-commit
description: Set up pre-commit hooks for a Python/SQL repo using the pre-commit framework — ruff (lint + format), mypy (types), pytest (tests), and sqlfluff for SQL. Use when the user wants to add pre-commit hooks, configure ruff/black/mypy/sqlfluff, or add commit-time formatting/typechecking/testing.
---

# Setup Pre-Commit Hooks

## What This Sets Up

- **[pre-commit](https://pre-commit.com)** managing the git hook
- **ruff** for linting and formatting Python (replaces black + flake8 + isort)
- **mypy** for type checking (only if the repo is typed)
- **pytest** run on commit (only if the repo has tests)
- **sqlfluff** for linting/formatting SQL (only if the repo has `.sql` files)

## Steps

### 1. Detect the project shape

Read the repo before assuming; don't scaffold what isn't there:

- Package manager / project file: `pyproject.toml` (preferred), `setup.cfg`,
  `requirements*.txt`, `poetry.lock`, `uv.lock`, `Pipfile`. Use whatever the
  repo already uses; default to `pip` + `pyproject.toml` if unclear.
- Is it typed? (a `py.typed` marker, existing `mypy` config, or type hints
  in the source.) Skip mypy if not.
- Are there tests? (a `tests/` dir or `test_*.py` files.) Skip pytest if not.
- Are there `.sql` files? Skip sqlfluff if not, and ask which dialect
  (`postgres`, `snowflake`, `bigquery`, `duckdb`, …) if yes — sqlfluff needs it.

### 2. Install pre-commit

```bash
pip install pre-commit        # or: uv tool install pre-commit / pipx install pre-commit
```

### 3. Create `.pre-commit-config.yaml`

Include only the hooks the repo actually needs (from step 1):

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff          # lint
        args: [--fix]
      - id: ruff-format   # format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy          # omit this repo block if the project isn't typed

  - repo: https://github.com/sqlfluff/sqlfluff
    rev: 3.2.4
    hooks:
      - id: sqlfluff-lint     # omit both if there are no .sql files
      - id: sqlfluff-fix

  - repo: local
    hooks:
      - id: pytest          # omit if the project has no tests
        name: pytest
        entry: pytest -q
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

Pin `rev` to the current release of each hook (check the repo's latest tag);
the values above are a starting point, not gospel.

### 4. Configure the tools (only where missing)

Add to `pyproject.toml` only if the repo has no config for these yet:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]   # pycodestyle, pyflakes, isort, pyupgrade, bugbear

[tool.mypy]
python_version = "3.11"
warn_unused_ignores = true
```

For sqlfluff, create `.sqlfluff` (only if it's missing) with the dialect
from step 1:

```ini
[sqlfluff]
dialect = postgres
```

### 5. Install the git hook

```bash
pre-commit install
```

This writes `.git/hooks/pre-commit` so the hooks run on every `git commit`.

### 6. Verify

- [ ] `.pre-commit-config.yaml` exists with only the applicable hooks
- [ ] `pre-commit` is installed and `pre-commit install` has run
- [ ] Tool config (ruff / mypy / sqlfluff) exists in `pyproject.toml` / `.sqlfluff`
- [ ] Run `pre-commit run --all-files` to check every hook passes on the current tree

### 7. Commit

Stage all changed/created files and commit with message:
`Add pre-commit hooks (ruff + mypy + pytest + sqlfluff)`

The commit runs through the new hooks — a good smoke test that everything works.

## Notes

- `ruff` covers linting, import-sorting, and formatting in one fast tool; you
  don't need black, isort, or flake8 alongside it.
- `pre-commit run --all-files` is the way to apply the hooks to an existing
  codebase the first time (the git hook only sees staged files).
- Keep pytest lean at commit time (`pytest -q`, or a fast subset); push the
  full suite to CI so commits stay quick.
- `pre-commit autoupdate` bumps every hook's `rev` to its latest release.
