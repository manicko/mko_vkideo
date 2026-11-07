---
phase: "04"
phase_name: "concurrency-cancellation"
id_prefix: "CON"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/04-audit-concurrency-cancellation.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Concurrency and Cancellation

## Summary

Подтверждено замечаний: 1. Максимальная категория — LOW. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** установка и очистка обработчиков сигналов.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| CON-001 | LOW | `src/vkdownloader/services/signal_handlers.py::cleanup_signal_handlers` | В изолированном POSIX-проходе установка обработчиков заменила предшествующий SIGINT, а очистка не восстановила именно обработчик asyncio.Runner, который был установлен перед вызовом. |

#### CON-001 — [LOW] [BEST-PRACTICE] В изолированном POSIX-проходе установка обработчиков заменила предшествующий SIGINT, а очистка не восстановила именно обработчик `asyncio.Runner`, который был установлен перед вызовом.

**Anchor:** `src/vkdownloader/services/signal_handlers.py::cleanup_signal_handlers`
**Disambiguator:** `loop.remove_signal_handler(sig)`
**Checked:** ran
**Classification:** advisory
**Why this band:** LOW — портируемый структурный эффект без наблюдённой потери задач; не MEDIUM, потому что на заявленной Windows-платформе этот путь не исполнялся.
**Problem:** В изолированном POSIX-проходе установка обработчиков заменила предшествующий SIGINT, а очистка не восстановила именно обработчик `asyncio.Runner`, который был установлен перед вызовом.
**Repro:** На Linux Python 3.13 внутри `asyncio.run` проверена идентичность `signal.getsignal(SIGINT)` до установки и после очистки; Runner callback не восстановлен.
**Impact:** На переносимых сценариях, где после очистки внутри того же цикла остаётся работа, Ctrl+C может обрабатываться не тем механизмом, что до регистрации.
**Root cause:** На пути с `loop.add_signal_handler` запоминается только множество сигналов; `remove_signal_handler` не восстанавливает предыдущий callback Runner.
**Fix:** Рекомендуется сохранить и восстановить исходную диспозицию при возврате из `cleanup_signal_handlers` на POSIX так же аккуратно, как в fallback, без изменения политики второго прерывания (effort: medium; priority: recommended). Это устраняет скрытую смену обработчика.
**Verify:** new test needed: test_posix_loop_signal_handler_restored_after_cleanup
**Best-practice reference:** https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.remove_signal_handler

**Evidence — `rg -nH 'def cleanup_signal_handlers|loop.remove_signal_handler\(sig\)|_restore_previous_handler' src/vkdownloader/services/signal_handlers.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/services/signal_handlers.py:49:def _restore_previous_handler(sig: signal.Signals) -> None:
src/vkdownloader/services/signal_handlers.py:178:def cleanup_signal_handlers() -> None:
src/vkdownloader/services/signal_handlers.py:196:                loop.remove_signal_handler(sig)
src/vkdownloader/services/signal_handlers.py:206:        _restore_previous_handler(sig)
```

**Evidence — `probes/04-signal-lifecycle.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
platform=linux
within-asyncio-run before=functools.partial(<bound method Runner._on_sigint of <asyncio.runners.Runner object at 0x7f7aac136120>>, main_task=<Task pending name='Task-1' coro=<run() running at /mnt/data/audit_workspace/additional_probes.py:58> cb=[_run_until_complete_cb() at /usr/lib/python3.13/asyncio/base_events.py:181]>)
after-setup=<function _sighandler_noop at 0x7f7aac283560>
after-cleanup=<built-in function default_int_handler>
outside-run=<built-in function default_int_handler>
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
