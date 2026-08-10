import pathlib
p = pathlib.Path('.ai/audit/04-audit-security/findings.md')
content = p.read_bytes().decode('utf-8')

# Fix corrupted arrow chars (replacement char -> arrow)
content = content.replace('\ufffd', '->')

# Fix Affected Modules line for SEC-006
content = content.replace(
    'src/vkdownloader/services/downloader.py:92, 605',
    'src/vkdownloader/services/downloader.py:605'
)

# Fix the utils/security.py reference in the Affected Modules
content = content.replace(
    'src/vkdownloader/utils/security.py:44-49',
    'src/vkdownloader/utils/security.py:44-52, 89-92'
)

# Fix evidence line: services/security.py -> utils/security.py
content = content.replace(
    'src/vkdownloader/services/security.py:89-92',
    'src/vkdownloader/utils/security.py:89-92'
)

p.write_text(content, encoding='utf-8')
print('Fixes applied. Verifying...')

# Verify
lines = content.splitlines()
for i, line in enumerate(lines, 1):
    if 'SEC-006' in line or (300 <= i <= 350 and ('security.py' in line or 'downloader.py:605' in line or 'Affected Modules' in line)):
        print(f'{i}: {line}')
