import re, pathlib

patterns = [
    r'(api_key|apikey|api-key)\s*[:=]\s*["''][^"'']{8,}',
    r'(access_token|access-token)\s*[:=]\s*["''][^"'']{8,}',
    r'(refresh_token|refresh-token)\s*[:=]\s*["''][^"'']{8,}',
    r'(private_key|private-key)\s*[:=]\s*["''][^"'']{8,}',
    r'(client_secret|client-secret)\s*[:=]\s*["''][^"'']{8,}',
]

skip_dirs = ['.venv', '.kilo/node_modules', '.mypy_cache', '.pytest_cache', '.ruff_cache', '__pycache__', '.egg-info', '.git', 'dist']

for ext in ['*.py', '*.js', '*.json', '*.yaml', '*.yml', '*.toml', '*.env', '*.env.*']:
    for f in pathlib.Path('.').rglob(ext):
        parts = pathlib.Path(str(f)).parts
        if any(s in parts for s in skip_dirs):
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            for pat in patterns:
                if re.search(pat, line, re.IGNORECASE):
                    print(f'{f}:{i}: {line.strip()[:140]}')
