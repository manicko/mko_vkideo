---
phase: "01"
phase_name: "entry-architecture"
id_prefix: "ENT"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/01-audit-entry-architecture.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Entry Points & Module Architecture

## Summary

Подтверждено замечаний: 1. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** командный слой, сервис batch, границы импорта.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| ENT-001 | MEDIUM | `src/vkdownloader/services/batch_downloader.py::_print_batch_summary` | Сервисный слой напрямую печатает в консоль и определяет числовой код завершения через _print_batch_summary; run_batch возвращает его команде |

#### ENT-001 — [MEDIUM] [SPEC-DEVIATION] Сервисный слой напрямую печатает в консоль и определяет числовой код завершения через `_print_batch_summary`; `run_batch` возвращает его команде

**Anchor:** `src/vkdownloader/services/batch_downloader.py::_print_batch_summary`
**Disambiguator:** `typer.echo(`
**Checked:** static
**Classification:** advisory
**Why this band:** MEDIUM — нарушена граница ответственности, без доказанного неверного конечного результата; не HIGH, поскольку потери диагностики не наблюдалось.
**Problem:** Сервисный слой напрямую печатает в консоль и определяет числовой код завершения через `_print_batch_summary`; `run_batch` возвращает его команде. Правило разделения слоя CLI и сервисов не соблюдается.
**Impact:** При повторном использовании сервиса из API или иной оболочки возникают неожиданные терминальные сообщения; тестирование сервиса зависит от интерфейса Typer.
**Root cause:** Форматирование результата и отображение итога находятся внутри модуля оркестрации загрузок.
**Fix:** Рекомендуется перенести пользовательское отображение из `_print_batch_summary` и выбор exit status из `run_batch` в `cli.batch_download`, сохранив сервисный результат структурированным (effort: medium; priority: recommended). Это позволит переиспользовать загрузчик без CLI.
**Verify:** new test needed: test_batch_service_has_no_console_side_effects

**Evidence — `rg -nH '^def _print_batch_summary|^async def run_batch|import typer|typer\.echo|return 130|return 1 if failed' src/vkdownloader/services/batch_downloader.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/services/batch_downloader.py:603:def _print_batch_summary(
src/vkdownloader/services/batch_downloader.py:629:    import typer
src/vkdownloader/services/batch_downloader.py:633:        typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))
src/vkdownloader/services/batch_downloader.py:653:    typer.echo("\n\nDownload Summary:")
src/vkdownloader/services/batch_downloader.py:654:    typer.echo(f"  Total videos: {len(results)}")
src/vkdownloader/services/batch_downloader.py:656:        typer.echo(f"  Skipped (invalid URLs): {skipped_count}")
src/vkdownloader/services/batch_downloader.py:658:        typer.echo(f"  Skipped (duplicates): {skipped}")
src/vkdownloader/services/batch_downloader.py:659:    typer.echo(f"  Peak concurrent videos: {peak_concurrent_videos}")
src/vkdownloader/services/batch_downloader.py:660:    typer.echo(f"  Successful: {successful}")
src/vkdownloader/services/batch_downloader.py:661:    typer.echo(f"  Failed: {failed}")
src/vkdownloader/services/batch_downloader.py:663:        typer.echo(f"  Cancelled: {cancelled}")
src/vkdownloader/services/batch_downloader.py:678:        typer.echo("  Failed URLs:")
src/vkdownloader/services/batch_downloader.py:680:            typer.echo(f"    - {url}: {status}")
src/vkdownloader/services/batch_downloader.py:686:        typer.echo(
src/vkdownloader/services/batch_downloader.py:690:        return 130
src/vkdownloader/services/batch_downloader.py:693:    return 1 if failed > 0 else 0
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
