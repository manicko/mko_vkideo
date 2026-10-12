"""Regenerate .ai/structure/back/py_map.yaml from the source tree.

Run:  uv run python .ai/structure/back/gen_py_map.py
Output: writes .ai/structure/back/py_map.yaml with repository-relative paths.
"""

import ast
import os

ROOT = "src/vkdownloader"
OUT = ".ai/structure/back/py_map.yaml"

modules = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames.sort()
    for fname in sorted(filenames):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(dirpath, fname)
        rel = os.path.relpath(fpath, ROOT)
        rel_posix = rel.replace(os.sep, "/")
        module_dotted = rel.replace(os.sep, ".")[:-3]
        with open(fpath, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=fpath)
        classes = []
        functions = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
        modules.append(
            {
                "path": f"src/vkdownloader/{rel_posix}",
                "module": f"vkdownloader.{module_dotted}",
                "classes": classes,
                "functions": functions,
            }
        )

lines = [
    "# Regeneration command: uv run python .ai/structure/back/gen_py_map.py",
    "# Lists only top-level classes and functions per module (no __init__ re-exports).",
    "# Paths are repository-relative (checkout-reproducible).",
    "",
]

for m in modules:
    lines.append(f"- path: {m['path']}")
    lines.append(f"  module: {m['module']}")
    lines.append("  layer: unknown")
    if m["classes"]:
        lines.append("  classes:")
        for c in m["classes"]:
            lines.append(f"  - {c}")
    else:
        lines.append("  classes: []")
    if m["functions"]:
        lines.append("  functions:")
        for fn in m["functions"]:
            lines.append(f"  - {fn}")
    else:
        lines.append("  functions: []")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Wrote {OUT} with {len(modules)} modules")
