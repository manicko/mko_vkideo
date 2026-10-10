"""Tests for the entry-point import graph.

See ``.ai/plans/05-entry-architecture-audit-fixes_fix.md`` Block 7 for the
rationale: eager re-exports in ``__init__.py`` files force a transitive import
chain that can form an import cycle (the ``exceptions -> utils/__init__ ->
security -> config`` inversion) and bloat the import surface so that touching
one helper recompiles half the package. The package roots are therefore
docstrings only, and a fresh-subprocess import of every module catches both a
regression that re-introduces a re-export and a cycle that only a cold start
exposes.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "vkdownloader"


def _package_modules() -> list[str]:
    """Return the dotted name of every importable module under the package.

    Discovered from the live source tree so the set tracks new modules
    automatically; ``__init__.py`` files are mapped to their package name,
    never to ``<pkg>.__init__``.
    """
    modules: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(SOURCE_ROOT).with_suffix("")
        if relative.name == "__init__":
            relative = relative.parent
        parts = tuple(part for part in relative.parts if part != ".")
        modules.append("vkdownloader" + ("." + ".".join(parts) if parts else ""))
    return modules


# Symbols the four eager roots used to re-export. Each is named after the
# package it represents so the invariant is local: importing a package must not
# pull in a subtree of modules it does not itself need to define.
PACKAGES_WITHOUT_REEXPORTS: list[tuple[str, str]] = [
    ("vkdownloader.services", "QualitySelector"),
    ("vkdownloader.utils", "sanitize_filename_component"),
    ("vkdownloader.models", "Video"),
    ("vkdownloader.infrastructure", "BrowserManager"),
]


@pytest.mark.parametrize("module_name", _package_modules())
def test_module_imports_in_a_fresh_interpreter(module_name: str) -> None:
    """Every source module imports with no error when loaded first.

    A subprocess is used so the import order matches a fresh interpreter,
    which is the only way to observe a cycle or a side effect that the running
    test session has already absorbed.
    """
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"importing {module_name} failed:\n{result.stderr}"


@pytest.mark.parametrize(("package", "symbol"), PACKAGES_WITHOUT_REEXPORTS)
def test_package_root_does_not_reexport_symbols(package: str, symbol: str) -> None:
    """No package root re-exports a symbol defined deeper in its subtree.

    Re-exports belong at the importing call site or a documented compatibility
    shim, so that importing a package does not silently execute its submodules.
    """
    module = importlib.import_module(package)

    assert not hasattr(module, symbol), (
        f"{package} should not re-export {symbol}; import it from its defining submodule instead"
    )
