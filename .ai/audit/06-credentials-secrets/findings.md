---
phase: "06"
phase_name: "credentials-secrets"
id_prefix: "SEC"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/06-audit-credentials-secrets.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Credentials and Secrets

## Summary

Подтверждено замечаний: 3. Максимальная категория — HIGH. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** argv для двух внешних транспортов, редактирование вывода.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| SEC-001 | HIGH | `src/vkdownloader/services/ffmpeg_transport.py::FfmpegTransport.download` | При прямом FFmpeg-транспорте Cookie строится в headers_content, передаётся после -headers в ffmpeg_args и целиком попадает в аргументы дочернего процесса; там же присутствует подписанный media URL. |
| SEC-002 | HIGH | `src/vkdownloader/services/ytdlp_downloader.py::_download_with_ytdlp` | Подписанный адрес плейлиста m3u8_url добавляется последним позиционным аргументом к python -m yt_dlp, хотя другие параметры, связанные с cookie, уже передаются через stdin. |
| SEC-003 | MEDIUM | `src/vkdownloader/utils/url_sanitizer.py::sanitize_text_for_log` | Фильтр логов редактирует URL и временные cookie-пути, но оставляет без изменений целые строки вида Cookie: session=..., Set-Cookie: ... и голые пары session=.... |

#### SEC-001 — [HIGH] [BEST-PRACTICE] При прямом FFmpeg-транспорте `Cookie` строится в `headers_content`, передаётся после `-headers` в `ffmpeg_args` и целиком попадает в аргументы дочернего процесса; там же присутствует подписанный media URL.

**Anchor:** `src/vkdownloader/services/ffmpeg_transport.py::FfmpegTransport.download`
**Disambiguator:** `headers_content += f"Cookie: {cookie_header_value}`
**Checked:** static
**Classification:** mandatory
**Why this band:** HIGH — контролируемый приложением перенос токена в process argv; не CRITICAL, потому что живой токен и неавторизованный наблюдатель не использовались.
**Problem:** При прямом FFmpeg-транспорте `Cookie` строится в `headers_content`, передаётся после `-headers` в `ffmpeg_args` и целиком попадает в аргументы дочернего процесса; там же присутствует подписанный media URL.
**Impact:** Другие локальные процессы с правом читать командную строку дочернего процесса получают маршрут к сессионным данным во время передачи.
**Root cause:** Путь `-headers <string>` переносит чувствительные заголовки через границу argv вместо непрозрачного канала.
**Fix:** Рекомендуется убрать сессионные заголовки и подписанные адреса из `FfmpegTransport.download` argv там, где это технически возможно; при невозможности документировать ограничение и минимизировать время/доступ (effort: medium; priority: recommended). Это снижает локальное раскрытие.
**Verify:** new test needed: test_ffmpeg_argv_excludes_synthetic_cookie_token
**Best-practice reference:** https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url

**Evidence — `rg -nH 'Cookie: \{cookie_header_value|"-headers"|headers_content|ffmpeg_url|asyncio.create_subprocess_exec' src/vkdownloader/services/ffmpeg_transport.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/services/ffmpeg_transport.py:88:            ffmpeg_url = binding.media_playlist_url
src/vkdownloader/services/ffmpeg_transport.py:126:            headers_content = (
src/vkdownloader/services/ffmpeg_transport.py:130:                headers_content += f"Cookie: {cookie_header_value}\r\n"
src/vkdownloader/services/ffmpeg_transport.py:137:                "-headers",
src/vkdownloader/services/ffmpeg_transport.py:138:                headers_content,
src/vkdownloader/services/ffmpeg_transport.py:140:                ffmpeg_url,
src/vkdownloader/services/ffmpeg_transport.py:155:            process = await asyncio.create_subprocess_exec(
```

#### SEC-002 — [HIGH] [BEST-PRACTICE] Подписанный адрес плейлиста `m3u8_url` добавляется последним позиционным аргументом к `python -m yt_dlp`, хотя другие параметры, связанные с cookie, уже передаются через stdin.

**Anchor:** `src/vkdownloader/services/ytdlp_downloader.py::_download_with_ytdlp`
**Disambiguator:** `cmd.append(m3u8_url)`
**Checked:** ran
**Classification:** mandatory
**Why this band:** HIGH — маршрут раскрытия подписанного токена через argv; не CRITICAL, потому что доказано на синтетическом адресе без реального наблюдателя.
**Problem:** Подписанный адрес плейлиста `m3u8_url` добавляется последним позиционным аргументом к `python -m yt_dlp`, хотя другие параметры, связанные с cookie, уже передаются через stdin.
**Repro:** Исходная функция построения аргументов вызвана в изоляции, затем выполнена точно такая же операция `cmd.append(m3u8_url)` с синтетическим адресом; токен входит в argv.
**Impact:** Локальный просмотр аргументов запущенного интерпретатора способен раскрыть токен URL, даже если логирование адреса защищено.
**Root cause:** Секретный URL передаётся через argv в `_download_with_ytdlp`, а не через канал со скрытым содержимым.
**Fix:** Рекомендуется оценить безопасный транспорт URL в `_download_with_ytdlp` вместо аргумента командной строки (effort: medium; priority: recommended), сохранив совместимость с yt-dlp; выгода — единая модель защиты подписанного токена.
**Verify:** new test needed: test_ytdlp_argv_does_not_contain_signed_query_token

**Evidence — `rg -nH 'cmd.append\(m3u8_url\)|asyncio.create_subprocess_exec' src/vkdownloader/services/ytdlp_downloader.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/services/ytdlp_downloader.py:1701:    Uses ``asyncio.create_subprocess_exec`` instead of ``run_in_executor``
src/vkdownloader/services/ytdlp_downloader.py:1767:    cmd.append(m3u8_url)
src/vkdownloader/services/ytdlp_downloader.py:1786:        process = await asyncio.create_subprocess_exec(
```

**Evidence — `probes/06-ytdlp-argv.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
cookie_file=None
synthetic_signed_url=https://cdn.example/stream.m3u8?token=SYNTHETIC_ONLY_TOKEN
argv_last=https://cdn.example/stream.m3u8?token=SYNTHETIC_ONLY_TOKEN
argv_contains_signed_token=True
argv_count=28
```

#### SEC-003 — [MEDIUM] [BEST-PRACTICE] Фильтр логов редактирует URL и временные cookie-пути, но оставляет без изменений целые строки вида `Cookie: session=...`, `Set-Cookie: ...` и голые пары `session=...`.

**Anchor:** `src/vkdownloader/utils/url_sanitizer.py::sanitize_text_for_log`
**Disambiguator:** `Shapes that are NOT matched:`
**Checked:** ran
**Classification:** advisory
**Why this band:** MEDIUM — измерен непокрытый формат, но не наблюдался его проход через sink; не HIGH, поскольку реальная утечка не подтверждена.
**Problem:** Фильтр логов редактирует URL и временные cookie-пути, но оставляет без изменений целые строки вида `Cookie: session=...`, `Set-Cookie: ...` и голые пары `session=...`.
**Repro:** Вызван настоящий `sanitize_text_for_log` на синтетическом наборе без реальных секретов; строки Cookie и Set-Cookie не меняются.
**Impact:** Если такой текст попадёт в путь echo, диагностический журнал или исключение, поле останется читаемым; реальный факт появления такого вывода не установлен (UNVERIFIED).
**Root cause:** Сопоставление `_URL_REGEX` и artefact-имён не покрывает протокольные формы cookie-заголовков.
**Fix:** Рекомендуется расширить контракт `sanitize_text_for_log` для секретных header-форм или запретить попадание этих форм в sinks до форматирования (effort: small; priority: recommended). Это создаст защиту от нестандартного вывода дочернего инструмента.
**Verify:** new test needed: test_cookie_header_redaction_synthetic_corpus

**Evidence — `rg -nH 'def sanitize_text_for_log|Shapes that are NOT matched|_URL_REGEX\.sub|_COOKIE_DIR_ARTEFACT_REGEX' src/vkdownloader/utils/url_sanitizer.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/utils/url_sanitizer.py:43:_COOKIE_DIR_ARTEFACT_REGEX = re.compile(_ARTEFACT_LEAD + r"vk_cookies__dir[a-z0-9_]+")
src/vkdownloader/utils/url_sanitizer.py:69:def sanitize_text_for_log(text: str) -> str:
src/vkdownloader/utils/url_sanitizer.py:89:    Shapes that are NOT matched:
src/vkdownloader/utils/url_sanitizer.py:123:    text = _URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)
src/vkdownloader/utils/url_sanitizer.py:125:    text = _COOKIE_DIR_ARTEFACT_REGEX.sub("***REDACTED***", text)
```

**Evidence — `probes/06-sanitizer-corpus.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
input='https://cdn.example/video.m3u8?token=FAKE_SECRET_123'; output='https://cdn.example/***REDACTED***'; unchanged=False
input='Cookie: session=FAKE_SECRET_123'; output='Cookie: session=FAKE_SECRET_123'; unchanged=True
input='session=FAKE_SECRET_123'; output='session=FAKE_SECRET_123'; unchanged=True
input='Set-Cookie: session=FAKE_SECRET_123; Path=/'; output='Set-Cookie: session=FAKE_SECRET_123; Path=/'; unchanged=True
input='headers=Cookie:session=FAKE_SECRET_123'; output='headers=Cookie:session=FAKE_SECRET_123'; unchanged=True
input='C:/Users/fake/AppData/Local/Temp/vk_cookies_abcd.cookies.txt'; output='***REDACTED***'; unchanged=False
```

## Fix Order

- **Dependencies:** None established.
- **Merge candidates:** None established.
- **Conflicting evidence:** None established.
- **Cross-phase conflicts:** Контроль границ: секреты argv описаны только в 06, HTTP-host selection — только в 03, CI coverage — в 10, supply-chain scanner — в 11.
- **Rollout risk:** Изменения проверять целевыми новыми тестами, указанными в `Verify`; переключение политики URL, Retry-After и cookie-передачи требует отдельно проверить совместимость с реальным downloader.

## Appendices

### Appendix A — Baseline prerequisites

**Command — `uv run --offline pytest -q -p no:cacheprovider`** (exit 2):
```text
error: No interpreter found for Python 3.14 in managed installations or search path

hint: A managed Python download is available for Python 3.14, but uv is set to offline mode
```

**Command — `PYTHONPATH=src python -m pytest -q -p no:cacheprovider`** (exit 4):
```text
ImportError while loading conftest '/mnt/data/audit_workspace/mko_vkideo-main/tests/conftest.py'.
tests/conftest.py:8: in <module>
    from vkdownloader.config import Settings
src/vkdownloader/config.py:12: in <module>
    import structlog
E   ModuleNotFoundError: No module named 'structlog'
```

### Appendix B — Evidence qualifications

Изолированные методы извлечены из исходного дерева; для AST-чтения только в памяти синтаксис `except A, B` Python 3.14 нормализован под анализатор Python 3.13. Исходный код и архив не изменялись. Проба не доказывает интеграционное поведение недоступных сторонних процессов. Никакие реальные credentials или URL подписанного сервиса не запрашивались.

Архив-источник: `mko_vkideo-main.zip` (SHA-256: `0c8e5799d6f4...`).
