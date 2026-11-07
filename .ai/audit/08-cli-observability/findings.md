---
phase: "08"
phase_name: "cli-observability"
id_prefix: "OUT"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/08-audit-cli-observability.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — CLI and Observability

## Summary

Подтверждено замечаний: 1. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** обработка ошибок чтения входного списка.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| OUT-001 | MEDIUM | `src/vkdownloader/cli.py::batch_download` | Ошибки декодирования URL-файла не проходят через специально предусмотренное сообщение Failed to read URL file: узкий обработчик ловит только OSError, а UnicodeDecodeError попадает в общий catch-all. |

#### OUT-001 — [MEDIUM] [BEST-PRACTICE] Ошибки декодирования URL-файла не проходят через специально предусмотренное сообщение `Failed to read URL file`: узкий обработчик ловит только `OSError`, а `UnicodeDecodeError` попадает в общий catch-all.

**Anchor:** `src/vkdownloader/cli.py::batch_download`
**Disambiguator:** `raw_urls = urls_file.read_text()`
**Checked:** static
**Classification:** advisory
**Why this band:** MEDIUM — диагностический контракт входного файла неполон; не HIGH, поскольку команда всё же сообщает о неуспехе общим сообщением.
**Problem:** Ошибки декодирования URL-файла не проходят через специально предусмотренное сообщение `Failed to read URL file`: узкий обработчик ловит только `OSError`, а `UnicodeDecodeError` попадает в общий catch-all.
**Impact:** При неверной кодировке входного списка оператор получает лишь общее сообщение и не понимает, какой файл вызвал отказ.
**Root cause:** Вызов `Path.read_text()` способен выбросить UnicodeError, не являющийся подклассом OSError.
**Fix:** Рекомендуется охватить сбои декодирования там же, где `batch_download` формирует ошибку чтения URL-файла (effort: trivial; priority: recommended). Это сохраняет контекст входного файла.
**Verify:** new test needed: test_batch_invalid_utf8_urls_file_reports_read_error

**Evidence — `rg -nH 'raw_urls = urls_file\.read_text\(\)|except OSError as e:|Failed to read URL file|An error occurred during batch download' src/vkdownloader/cli.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/cli.py:650:        # "Failed to read URL file" message while every other OSError
src/vkdownloader/cli.py:653:            raw_urls = urls_file.read_text()
src/vkdownloader/cli.py:654:        except OSError as e:
src/vkdownloader/cli.py:655:            typer.echo(f"Failed to read URL file: {urls_file} — {e}", err=True)
src/vkdownloader/cli.py:710:        typer.echo("An error occurred during batch download", err=True)
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
