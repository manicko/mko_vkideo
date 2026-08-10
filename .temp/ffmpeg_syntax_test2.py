import asyncio, tempfile, os

async def test():
    fd, hpath = tempfile.mkstemp(suffix='.headers')
    headers_content = 'User-Agent: TestAgent\r\nCookie: secret_cookie_value\r\n'
    os.write(fd, headers_content.encode())
    os.close(fd)

    async def run_ffmpeg(label, cmd):
        print(f'=== {label} ===')
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        full = b''
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            full += line
        await proc.wait()
        # Show only relevant lines
        for line in full.decode(errors='replace').splitlines():
            low = line.lower()
            if any(k in low for k in ['trailing', 'crlf', 'http error', 'opening', 'error', 'cookie', 'header']):
                print(f'  {line.strip()[:140]}')
        print()

    url = 'https://example.com/test.m3u8'
    await run_ffmpeg('1: -headers @file (CURRENT CODE)', ['ffmpeg', '-y', '-v', 'warning', '-nostats', '-headers', '@' + hpath, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    await run_ffmpeg('2: -headers inline', ['ffmpeg', '-y', '-v', 'warning', '-nostats', '-headers', headers_content, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    await run_ffmpeg('3: -/headers file (documented)', ['ffmpeg', '-y', '-v', 'warning', '-nostats', '-/headers', hpath, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    os.unlink(hpath)

asyncio.run(test())
