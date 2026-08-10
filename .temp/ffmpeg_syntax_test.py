import asyncio, tempfile, os

async def test():
    fd, hpath = tempfile.mkstemp(suffix='.headers')
    headers_content = 'User-Agent: TestAgent\r\nCookie: secret_cookie_value\r\n'
    os.write(fd, headers_content.encode())
    os.close(fd)

    async def run_ffmpeg(label, cmd):
        print(f'=== {label} ===')
        print(f'CMD: {cmd}')
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        lines = []
        for _ in range(6):
            line = await proc.stderr.readline()
            if not line:
                break
            lines.append(line.decode(errors='replace').rstrip())
        await proc.wait()
        for l in lines:
            print(f'  {l}')
        print()

    url = 'https://example.com/test.m3u8'
    await run_ffmpeg('1: -headers @file (CURRENT CODE)', ['ffmpeg', '-y', '-progress', 'pipe:2', '-nostats', '-headers', '@' + hpath, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    await run_ffmpeg('2: -headers inline', ['ffmpeg', '-y', '-progress', 'pipe:2', '-nostats', '-headers', headers_content, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    await run_ffmpeg('3: -/headers file (documented)', ['ffmpeg', '-y', '-progress', 'pipe:2', '-nostats', '-/headers', hpath, '-i', url, '-c', 'copy', '-f', 'null', '-'])
    os.unlink(hpath)

asyncio.run(test())
