import ast, os, re
def defined_names(path):
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name)
    return out
files = []
for root,_,fs in os.walk('src/vkdownloader'):
    for f in fs:
        if f.endswith('.py'):
            files.append(os.path.join(root,f))
all_defs = {}
for f in files:
    for n in defined_names(f):
        all_defs.setdefault(n, []).append(f)
src_all = ""
for f in files:
    src_all += open(f, encoding='utf-8').read()
results = []
for name, locs in all_defs.items():
    if name.startswith('_'):
        continue
    cnt = len(re.findall(r'\b'+re.escape(name)+r'\b', src_all)) - len(locs)
    if cnt == 0:
        results.append((name, locs))
for name, locs in sorted(results):
    print(name, locs)
