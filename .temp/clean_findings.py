import pathlib, re
p = pathlib.Path('.ai/audit/04-audit-security/findings.md')
content = p.read_text(encoding='utf-8')

# Collapse 3+ consecutive newlines (blank lines) into 1 blank line (2 newlines)
content = re.sub(r'\n\n\n+', '\n\n', content)

# Also remove trailing whitespace on each line
lines = content.split('\n')
lines = [line.rstrip() for line in lines]
content = '\n'.join(lines)

p.write_text(content, encoding='utf-8')
print(f'Cleaned. New line count: {len(content.splitlines())}')
