---
phase: "07"
phase_name: "filesystem-artifacts"
id_prefix: "ART"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/07-audit-filesystem-artifacts.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Filesystem Artifacts

## Summary

Подтверждено замечаний: 1. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** обработка имён и валидация конечного пути.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| ART-001 | MEDIUM | `src/vkdownloader/utils/security.py::validate_final_output_path` | Валидный длинный путь (246 символов) отклоняется как PATH_TRAVERSAL, хотя не содержит переходов .. и не использует символические ссылки. |

#### ART-001 — [MEDIUM] [BEST-PRACTICE] Валидный длинный путь (246 символов) отклоняется как `PATH_TRAVERSAL`, хотя не содержит переходов `..` и не использует символические ссылки.

**Anchor:** `src/vkdownloader/utils/security.py::validate_final_output_path`
**Disambiguator:** `exc.error_code = ErrorCode.PATH_TRAVERSAL`
**Checked:** ran
**Classification:** advisory
**Why this band:** MEDIUM — законный путь ошибочно трактуется как нарушение безопасности; не HIGH, поскольку исходные файлы не были повреждены.
**Problem:** Валидный длинный путь (246 символов) отклоняется как `PATH_TRAVERSAL`, хотя не содержит переходов `..` и не использует символические ссылки.
**Repro:** В изоляции вызван исходный `validate_final_output_path` с путём 246 символов внутри временного каталога на Linux; получен `DownloadError` c error_code=path_traversal.
**Impact:** Пользователь получает диагностику категории безопасности вместо понятного ограничения длины имени; портативный запуск на Linux лишён допустимого пути.
**Root cause:** Ограничение `MAX_OUTPUT_PATH_LENGTH=240` переиспользует ошибку `PATH_TRAVERSAL` для независимой причины отказа.
**Fix:** Рекомендуется различать в `validate_final_output_path` нарушение containment и ограничение длины, а сам порог согласовать с фактической целевой платформой (effort: small; priority: recommended). Это повысит диагностируемость без снижения защиты.
**Verify:** new test needed: test_long_legitimate_output_path_reports_length_error

**Evidence — `rg -nH 'def validate_final_output_path|MAX_OUTPUT_PATH_LENGTH|Output path too long|ErrorCode\.PATH_TRAVERSAL' src/vkdownloader/utils/security.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/utils/security.py:22:MAX_OUTPUT_PATH_LENGTH: int = 240
src/vkdownloader/utils/security.py:23:MAX_FINAL_OUTPUT_PATH_LENGTH: int = MAX_OUTPUT_PATH_LENGTH
src/vkdownloader/utils/security.py:24:MAX_PATH_LENGTH: int = MAX_OUTPUT_PATH_LENGTH
src/vkdownloader/utils/security.py:70:        exc.error_code = ErrorCode.PATH_TRAVERSAL
src/vkdownloader/utils/security.py:82:        exc.error_code = ErrorCode.PATH_TRAVERSAL
src/vkdownloader/utils/security.py:145:def validate_final_output_path(path: Path, warning: bool = True) -> Path:
src/vkdownloader/utils/security.py:154:    if len(str(candidate)) > MAX_OUTPUT_PATH_LENGTH:
src/vkdownloader/utils/security.py:156:            f"Output path too long ({len(str(candidate))} > {MAX_OUTPUT_PATH_LENGTH}): {candidate}"
src/vkdownloader/utils/security.py:158:        exc.error_code = ErrorCode.PATH_TRAVERSAL
src/vkdownloader/utils/security.py:172:            exc.error_code = ErrorCode.PATH_TRAVERSAL
src/vkdownloader/utils/security.py:176:    if len(str(resolved)) > MAX_OUTPUT_PATH_LENGTH:
src/vkdownloader/utils/security.py:178:            f"Output path too long ({len(str(resolved))} > {MAX_OUTPUT_PATH_LENGTH}): {resolved}"
src/vkdownloader/utils/security.py:180:        exc.error_code = ErrorCode.PATH_TRAVERSAL
```

**Evidence — `probes/07-path-guard.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
input=/tmp/tmp_babyj7k/outside-repository; validated=/tmp/tmp_babyj7k/outside-repository; root_enforced=False
long_path rejected=Err message=Output path too long (246 > 240): /tmp/tmp_babyj7k/outside-repository/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx class=path_traversal
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
