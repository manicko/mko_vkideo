---
phase: "09"
phase_name: "code-quality"
id_prefix: "QLT"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/09-audit-code-quality.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Code Quality

## Summary

Подтверждено замечаний: 2. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** сопоставление API-документации и локальных ссылок с репозиторием.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| QLT-001 | MEDIUM | `docs/01-tools/api-reference.md::"extract_streams_with_cookies(url: str, force_browser: bool = False) -> tuple[list[Stream], str | None]"` | API-справочник описывает extract_streams_with_cookies как возвращающий два значения, тогда как публичный метод фактически возвращает три, включая raw cookies. |
| QLT-002 | LOW | `docs/01-tools/vkdownloader-overview.md::"vkdownloader-limitations.md"` | Ссылки на руководство об ограничениях адресуют файл в каталоге 01-tools, хотя фактический файл находится в 11-guides. |

#### QLT-001 — [MEDIUM] [DOC-UPDATE] API-справочник описывает `extract_streams_with_cookies` как возвращающий два значения, тогда как публичный метод фактически возвращает три, включая raw cookies.

**Anchor:** `docs/01-tools/api-reference.md::"extract_streams_with_cookies(url: str, force_browser: bool = False) -> tuple[list[Stream], str | None]"`
**Anchor:** `src/vkdownloader/services/extractor.py::VKVideoExtractor.extract_streams_with_cookies`
**Disambiguator:** `tuple[list[Stream], str | None]`
**Checked:** static
**Classification:** advisory
**Why this band:** MEDIUM — внешний контракт документирован неверно; не HIGH, потому что не показан фактический пользовательский сбой.
**Problem:** API-справочник описывает `extract_streams_with_cookies` как возвращающий два значения, тогда как публичный метод фактически возвращает три, включая raw cookies.
**Impact:** Разработчик, распаковывающий ответ по документации, получит ошибку unpack при реальном вызове.
**Root cause:** Справочник не синхронизирован с изменённой сигнатурой сервиса.
**Fix:** Рекомендуется обновить строку сигнатуры, пример распаковки и описание третьего результата в `docs/01-tools/api-reference.md` (effort: trivial; priority: recommended). Это предотвращает ошибочный пример интеграции.
**Verify:** new test needed: test_api_reference_cookie_method_signature_matches_source

**Evidence — `rg -nH 'extract_streams_with_cookies\(|Returns:.*Tuple of \(streams|tuple\[list\[Stream\]' docs/01-tools/api-reference.md | head -16`** *(исходный код из zip)*:
```text
docs/01-tools/api-reference.md:85:#### `extract_streams_with_cookies(url: str, force_browser: bool = False) -> tuple[list[Stream], str | None]`
docs/01-tools/api-reference.md:95:**Returns:** Tuple of (streams list, cookies string) for CDN headers.
docs/01-tools/api-reference.md:814:- `VKVideoExtractor.extract_streams_with_cookies()` — When no streams found
```

#### QLT-002 — [LOW] [DOC-UPDATE] Ссылки на руководство об ограничениях адресуют файл в каталоге `01-tools`, хотя фактический файл находится в `11-guides`.

**Anchor:** `docs/01-tools/vkdownloader-overview.md::"vkdownloader-limitations.md"`
**Disambiguator:** `vkdownloader-limitations.md`
**Checked:** ran
**Classification:** advisory
**Why this band:** LOW — нарушение навигации без воздействия на исполняемый код; не MEDIUM, поскольку неверное действие по инструкции не установлено.
**Problem:** Ссылки на руководство об ограничениях адресуют файл в каталоге `01-tools`, хотя фактический файл находится в `11-guides`.
**Repro:** Разрешение локальных Markdown-ссылок относительно их собственного документа обнаружило два несуществующих пути к файлу, реально расположенному в `docs/11-guides`.
**Impact:** Читатель перехода из обзора получает несуществующую локальную страницу, что скрывает важные ограничения Windows-процессов.
**Root cause:** В Markdown выбран путь относительно неверного каталога.
**Fix:** Рекомендуется исправить относительный адрес обеих ссылок в `docs/01-tools/vkdownloader-overview.md` (effort: trivial; priority: recommended). Это восстановит навигацию по эксплуатационным ограничениям.
**Verify:** new test needed: test_documentation_local_links_resolve

**Evidence — `rg -nH 'vkdownloader-limitations\.md' docs/01-tools/vkdownloader-overview.md | head -16`** *(исходный код из zip)*:
```text
docs/01-tools/vkdownloader-overview.md:158:- **Secret-safe cookie passing**: VK session cookies are written to a temporary Netscape cookie file (requested at `0o600`, owner-only on POSIX only, with the same Windows caveat as above) inside a private per-run directory under the system temp directory, and passed to the yt-dlp subprocess as `--cookies <path>` in argv. Only the file **path** appears in process listings (`ps`, `/proc/<pid>/cmdline`, `htop`, `docker inspect`); the **contents** (signed CDN URLs and session tokens) do not. That exposure was tracked by phase 06's `SEC-006`, now closed: the artefact path is redacted out of child output before it reaches the console and out of every log record by the central redaction processor, so the process listing is the only place it is still readable — and it is moot for this single-user desktop deployment (D1). The cookie file and its directory are removed when the download ends, including on failure and cancellation; after a hard kill the residue is reclaimed by the next run's sweep, and that sweep's default-deny criterion and its deliberate retentions are in the [limitations guide](vkdownloader-limitations.md#cookie-artefact-lifecycle)
docs/01-tools/vkdownloader-overview.md:159:- **Subprocess process boundary**: every subprocess spawn (yt-dlp and ffmpeg merge stages) starts a new process session/group (`start_new_session=True` on POSIX, `CREATE_NEW_PROCESS_GROUP` on Windows). On POSIX this lets the termination ladder signal descendants via `os.killpg`; on Windows the group is console-signal routing only and descendants the child started for itself can survive — see the [limitations guide](vkdownloader-limitations.md#subprocess-process-boundary-trn-003) for the Windows residual and how to clean up manually.
```

**Evidence — `probes/09-doc-links.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
docs/00-overview/doc-maintenance-rules.md::../01-auth/auth-api.md unresolved
docs/01-tools/vkdownloader-overview.md::vkdownloader-limitations.md unresolved
docs/01-tools/vkdownloader-overview.md::vkdownloader-limitations.md unresolved
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
