---
name: setup-python-modules
description: Wire import-linter into a Python repo so each package is a deep module — a public API in __init__.py with implementation hidden in a private _internal subpackage, reachable from outside only through the public surface. User-invoked.
disable-model-invocation: true
---

# Setup Python Deep Modules

Make every top-level package in this repo a **deep module**: a lot of behaviour behind a small interface. A package's public surface is its **`__init__.py`** (what it re-exports); everything under a private `_internal/` subpackage is hidden. This skill installs [import-linter](https://github.com/seddonym/import-linter) and the contracts that make the public API the only way in, then proves the contracts bite.

For the vocabulary (deep module, interface, seam, depth), call the Skill tool with "codebase-design" and use its language throughout.

## The shape this enforces

```
src/myapp/
  pkg_a/
    __init__.py     ← the PUBLIC API. Re-exports what outsiders may use.
    _internal/      ← implementation: private, free to import within pkg_a.
        service.py
        parsing.py
  pkg_b/
    __init__.py
    _internal/
        ...
  tests/            ← import packages through their public API only.
```

The public surface is what `__init__.py` re-exports. By convention implementation lives under a `_internal/` subpackage (the leading underscore signals "private" to readers, and import-linter forbids reaching into it from outside). Everything a package needs internally imports freely within that package.

Three contracts, all enforced by `lint-imports`:

1. **Internals are private**: nothing *outside* a package may import that package's `_internal` subpackage. Outsiders go through `__init__.py`.
2. **Feature packages are independent**: top-level feature packages don't import each other directly — shared code moves into a `common`/`core` package they both depend on. (Skip or relax this if the repo is intentionally layered instead; see the layers stub.)
3. **No cycles**: import-linter reports import cycles; treat them as errors.

Layering (which packages may depend on which) is a *different* concern and is left as a commented `layers` stub in the config for this repo to fill in.

## Steps

### 1. Detect the environment

- **Project file**: `pyproject.toml` (preferred), else `setup.cfg`. import-linter can read config from either, or from a standalone `.importlinter`.
- **Package root**: the importable top-level package (e.g. `src/myapp/` with a `src` layout, or `myapp/` at the repo root). Confirm with the user if ambiguous.
- **Feature packages**: the immediate sub-packages under the root that hold real behaviour (exclude `_internal`, `tests`, `common`/`core`).
- **Existing config**: check for an `[importlinter]` section or `.importlinter` file. If one exists, do **not** overwrite it: merge the contracts in and tell the user what you added.

**Done when:** project file, root package, feature-package list, and existing-config status are all known.

### 2. Install import-linter

Install `import-linter` as a dev dependency with the repo's package manager (`pip install import-linter`, `uv add --dev import-linter`, or a `poetry add --group dev import-linter`).

**Done when:** `import-linter` is in the dev dependencies.

### 3. Write the config

Copy [`importlinter.ini`](./importlinter.ini) into the repo as `.importlinter` (or fold its `[importlinter]` / `[importlinter:contract:*]` sections into `pyproject.toml` under `[tool.importlinter]`). Set `root_package` to the root detected in step 1 and fill the `forbidden` and `independence` contracts with the actual package names.

**Done when:** the config exists with the correct `root_package` and one "internals private" forbidden contract per feature package.

### 4. Wire it into the checks

- Add a `lint-imports` invocation to the repo's check command — the one that already runs ruff/mypy (a `check` / `ci` / `lint` target in the `Makefile`, `tox.ini`, `noxfile.py`, or a pre-commit hook).
- If there is no umbrella target, add a `lint-imports` step and tell the user to include it in CI.

**Done when:** `lint-imports` runs as part of the same command as the type check.

### 5. Scaffold the example package

Create a committed `<root>/example/` as a copy-me template:

- `__init__.py` re-exports one public function that delegates to an internal module (so the package is visibly *deep*, not a pass-through).
- `_internal/impl.py`: an internal module in the private subpackage, imported by `__init__.py`, not reachable from outside.
- A test under `tests/` imports **only** `myapp.example` (the public API) and asserts against the public function.

Tell the user this is a starter template to copy or delete.

**Done when:** the example package exists, exposes its behaviour through `__init__.py`, and hides `impl` under `_internal/`.

### 6. Prove the contracts bite

This is the completion criterion for the whole skill: a config that doesn't fail on a violation is worthless.

1. Run `lint-imports`. It must **pass** on the clean example.
2. Temporarily add a deep import to the example test (e.g. `from myapp.example._internal.impl import thing`). Run `lint-imports` again; it must **fail** on the "internals are private" contract.
3. Revert the deep import. Run once more, and it must **pass**.

**Done when:** you have observed a pass, then a fail on the deep import, then a pass again. If step 2 does not fail, the contracts are not wired correctly — fix before finishing.

### 7. Document the convention

Write a `README.md` **in the root package folder** covering: the `<pkg>/__init__.py` + `_internal/` layout, "import a package only through its public API (`myapp.<pkg>`), never `myapp.<pkg>._internal.*`", and how to run `lint-imports`. Keep it to the copy-me snippet plus the three contracts in one paragraph each.

Then add a **context pointer** to it from the repo's agent-instructions file (`CLAUDE.md` if present, else `AGENTS.md`, creating `AGENTS.md` if neither exists). One line is enough, e.g. `Packages are deep modules: see [src/myapp/README.md](./src/myapp/README.md) before adding or importing one.` This is what makes an agent discover the boundary rule instead of tripping over it.

**Done when:** the package `README.md` exists and the repo's `CLAUDE.md`/`AGENTS.md` links to it.

## Notes

- **Public vs private is a naming convention import-linter enforces.** The public API is what `__init__.py` re-exports; the private `_internal/` subpackage is off-limits from outside. import-linter's `forbidden` contract lists each package's *siblings* (and the app's composition roots) as sources, so a package importing its own `_internal` stays free while outsiders are blocked.
- **One forbidden contract per feature package.** import-linter can't express "everything except this package", so each package gets its own contract naming the others as sources. The `importlinter.ini` template shows the two-package pattern; extend it as you add packages.
- **Feature packages are flat**: one tier of immediate children under the root. A package's internals may nest as deep as you like under `_internal/`; a package should not contain another feature package.
- Prefer a small `__init__.py` that re-exports a few names over one that pulls a whole subtree into the namespace — the equivalent of avoiding a barrel file. Keep the public surface small and hide implementation under `_internal/`.
