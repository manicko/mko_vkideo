---
phase: "03"
phase_name: "network-resilience"
id_prefix: "NET"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/03-audit-network-resilience.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Network Resilience

## Summary

Подтверждено замечаний: 3. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** browser response selection, HTTP Retry-After, limits тела ответа.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| NET-001 | MEDIUM | `src/vkdownloader/infrastructure/network_monitor.py::NetworkMonitor.select` | При отсутствии адресов с VK-доменами фильтр отключается, и единственный захваченный внешний URL, в том числе 127.0.0.1, возвращается как допустимый поток. |
| NET-002 | MEDIUM | `src/vkdownloader/services/retry_policies.py::_compute_backoff_delay` | Положительный Retry-After в 120 секунд сокращается до 30 секунд при расчёте задержки повтора запроса. |
| NET-003 | MEDIUM | `src/vkdownloader/infrastructure/network_monitor.py::NetworkMonitor._read_bounded_body` | Ограничение MAX_JSON_BODY_BYTES проверяется уже после того, как Response.body() целиком материализует ответ; при chunked-передаче неизвестной длины оно не ограничивает пиковую память. |

#### NET-001 — [MEDIUM] [BEST-PRACTICE] При отсутствии адресов с VK-доменами фильтр отключается, и единственный захваченный внешний URL, в том числе `127.0.0.1`, возвращается как допустимый поток.

**Anchor:** `src/vkdownloader/infrastructure/network_monitor.py::NetworkMonitor.select`
**Disambiguator:** `return sorted(captured, key=self._rank_playlist)`
**Checked:** ran
**Classification:** mandatory
**Why this band:** MEDIUM — некорректное допущение адреса, без сетевого обращения в пробе; не HIGH, поскольку внешнее скачивание не выполнялось.
**Problem:** При отсутствии адресов с VK-доменами фильтр отключается, и единственный захваченный внешний URL, в том числе `127.0.0.1`, возвращается как допустимый поток.
**Repro:** Выполнены только исходные методы фильтра/селектора над тремя синтетическими наборами; `foreign-only` и `loopback-only` возвращают адреса вне allowlist.
**Impact:** Загрузка может перейти к неутверждённому адресу; для локального адреса это также открывает направление нежелательного обращения к локальным сервисам, если downstream его скачает.
**Root cause:** `NetworkMonitor.select` использует ветку резервного выбора без host allowlist, если отфильтрованный список пуст.
**Fix:** Рекомендуется не отдавать неразрешённые адреса из `NetworkMonitor.select` без отдельного явного разрешения/диагноза (effort: small; priority: recommended). Это делает границу доверенных источников предсказуемой.
**Verify:** new test needed: test_select_rejects_only_foreign_manifest
**Best-practice reference:** https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

**Evidence — `rg -nH 'def select\(|if not host_allowed:|return sorted\(captured|ALLOWED_HOST_SUFFIXES' src/vkdownloader/infrastructure/network_monitor.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/infrastructure/network_monitor.py:53:    ALLOWED_HOST_SUFFIXES: tuple[str, ...] = (
src/vkdownloader/infrastructure/network_monitor.py:130:        is an entry in ``ALLOWED_HOST_SUFFIXES`` or a subdomain thereof.
src/vkdownloader/infrastructure/network_monitor.py:150:            host == suffix or host.endswith(f".{suffix}") for suffix in self.ALLOWED_HOST_SUFFIXES
src/vkdownloader/infrastructure/network_monitor.py:248:    def select(self) -> list[str]:
src/vkdownloader/infrastructure/network_monitor.py:287:            if not host_allowed:
src/vkdownloader/infrastructure/network_monitor.py:291:                return sorted(captured, key=self._rank_playlist)
```

**Evidence — `probes/03-host-filter-validated.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
foreign-only: hosts=['https://foreign.example/a.m3u8'] allowlist=('vkvideo.ru', 'vk.com') result=['https://foreign.example/a.m3u8']
loopback-only: hosts=['https://127.0.0.1/a.m3u8'] allowlist=('vkvideo.ru', 'vk.com') result=['https://127.0.0.1/a.m3u8']
mixed: hosts=['https://foreign.example/a.m3u8', 'https://vkvideo.ru/b.m3u8'] allowlist=('vkvideo.ru', 'vk.com') result=['https://vkvideo.ru/b.m3u8']
```

#### NET-002 — [MEDIUM] [BEST-PRACTICE] Положительный `Retry-After` в 120 секунд сокращается до 30 секунд при расчёте задержки повтора запроса.

**Anchor:** `src/vkdownloader/services/retry_policies.py::_compute_backoff_delay`
**Disambiguator:** `delay = min(delay, 30.0)`
**Checked:** ran
**Classification:** advisory
**Why this band:** MEDIUM — конфликт локального ограничения и серверной политики; не HIGH, поскольку сетевой отказ по причине раннего повтора не наблюдался.
**Problem:** Положительный `Retry-After` в 120 секунд сокращается до 30 секунд при расчёте задержки повтора запроса.
**Repro:** Исходная `_compute_backoff_delay(429, attempt, 120)` с фиксированной jitter=0 для трёх attempt вернула 30.0.
**Impact:** Клиент делает повтор раньше времени, запрошенного перегруженным origin; возможно продление ограничения частоты и повторная ошибка.
**Root cause:** Лимит 30 секунд применяется после выбора максимума с серверной задержкой.
**Fix:** Рекомендуется различать потолок собственной jitter-задержки и уважение к серверному `Retry-After` в `_compute_backoff_delay`; если долгие ожидания запрещены политикой, явно завершать попытку вместо раннего повтора (effort: small; priority: recommended). Это уменьшит давление на origin.
**Verify:** new test needed: test_retry_after_above_local_ceiling_is_not_retried_early
**Best-practice reference:** https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After

**Evidence — `rg -nH 'def _compute_backoff_delay|delay = max\(delay, retry_after_seconds\)|delay = min\(delay, 30\.0\)' src/vkdownloader/services/retry_policies.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/services/retry_policies.py:177:def _compute_backoff_delay(
src/vkdownloader/services/retry_policies.py:211:        delay = max(delay, retry_after_seconds)
src/vkdownloader/services/retry_policies.py:213:    delay = min(delay, 30.0)
```

**Evidence — `probes/03-retry-after.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
status=429 attempt=0 retry_after=None: waited=0.0
status=429 attempt=0 retry_after=2: waited=2
status=429 attempt=0 retry_after=120: waited=30.0
status=429 attempt=4 retry_after=None: waited=0.0
status=429 attempt=4 retry_after=2: waited=2
status=429 attempt=4 retry_after=120: waited=30.0
status=429 attempt=10 retry_after=None: waited=0.0
status=429 attempt=10 retry_after=2: waited=2
status=429 attempt=10 retry_after=120: waited=30.0
```

#### NET-003 — [MEDIUM] [BEST-PRACTICE] Ограничение `MAX_JSON_BODY_BYTES` проверяется уже после того, как `Response.body()` целиком материализует ответ; при chunked-передаче неизвестной длины оно не ограничивает пиковую память.

**Anchor:** `src/vkdownloader/infrastructure/network_monitor.py::NetworkMonitor._read_bounded_body`
**Disambiguator:** `body = await response.body()`
**Checked:** static
**Classification:** advisory
**Why this band:** MEDIUM — структурно доказанный неэффективный предел; не HIGH, так как реальный пик RSS не измерялся.
**Problem:** Ограничение `MAX_JSON_BODY_BYTES` проверяется уже после того, как `Response.body()` целиком материализует ответ; при chunked-передаче неизвестной длины оно не ограничивает пиковую память.
**Impact:** Крупный или враждебный ответ может кратковременно занять существенно больше заявленного лимита и ухудшить устойчивость процесса.
**Root cause:** Граница применяется к длине готовых bytes, а не к количеству реально принятых байтов.
**Fix:** Рекомендуется явно ограничивать/отбрасывать неограниченные ответы до полной буферизации там, где это позволяет выбранный интерфейс, либо отключить анализ таких тел (effort: medium; priority: recommended). Это делает бюджет памяти проверяемым.
**Verify:** new test needed: test_interceptor_rejects_unbounded_body_before_materialization

**Evidence — `rg -nH 'async def _read_bounded_body|body = await response\.body\(\)|len\(body\) > self\.MAX_JSON_BODY_BYTES' src/vkdownloader/infrastructure/network_monitor.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/infrastructure/network_monitor.py:192:    async def _read_bounded_body(self, response: Response) -> bytes | None:
src/vkdownloader/infrastructure/network_monitor.py:200:            body = await response.body()
src/vkdownloader/infrastructure/network_monitor.py:208:        if len(body) > self.MAX_JSON_BODY_BYTES:
src/vkdownloader/infrastructure/network_monitor.py:384:                body = await response.body()
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
