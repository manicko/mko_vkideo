---
phase: "02"
phase_name: "config"
id_prefix: "CFG"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/02-audit-config.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Configuration

## Summary

Подтверждено замечаний: 2. Максимальная категория — MEDIUM. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** Settings, поля, валидаторы, интерфейсы логирования.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| CFG-001 | MEDIUM | `src/vkdownloader/config.py::Settings.normalize_log_level` | Передающий неверный тип программный вызов Settings(log_level=123) получает необработанный AttributeError, а не стандартную ошибку валидации Pydantic. |
| CFG-002 | MEDIUM | `src/vkdownloader/config.py::Settings` | Параметры log_max_bytes и log_backup_count не имеют нижней границы |

#### CFG-001 — [MEDIUM] [BEST-PRACTICE] Передающий неверный тип программный вызов `Settings(log_level=123)` получает необработанный `AttributeError`, а не стандартную ошибку валидации Pydantic.

**Anchor:** `src/vkdownloader/config.py::Settings.normalize_log_level`
**Disambiguator:** `LogLevel(v.upper())`
**Checked:** ran
**Classification:** advisory
**Why this band:** MEDIUM — некорректная форма ошибки на программном пути; не HIGH, поскольку переменные окружения поставляют текст и пользовательский запуск не воспроизведён.
**Problem:** Передающий неверный тип программный вызов `Settings(log_level=123)` получает необработанный `AttributeError`, а не стандартную ошибку валидации Pydantic.
**Repro:** В изолированном выполнении исходного объявления `Settings` на Pydantic 2.13.5 передано `log_level=123`; результат `AttributeError`, тогда как `max_retries=0` даёт `ValidationError`.
**Impact:** Интеграционные вызовы Settings не могут единообразно обработать некорректное значение и классифицировать его как ошибку конфигурации.
**Root cause:** Валидатор без проверки типа вызывает строковый метод `.upper()`.
**Fix:** Рекомендуется сделать `Settings.normalize_log_level` полной функцией для всех входных типов и возвращать `ValueError` для неподдерживаемых (effort: trivial; priority: recommended). Это сохраняет контракт ValidationError для разработчика API.
**Verify:** new test needed: test_log_level_rejects_non_string_via_validation_error

**Evidence — `rg -nH 'def normalize_log_level|return LogLevel\(v\.upper\(\)\)' src/vkdownloader/config.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/config.py:302:    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
src/vkdownloader/config.py:310:        return LogLevel(v.upper())
```

**Evidence — `probes/02-settings-validated.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
Pydantic version=2.13.5
Fields=25
log_max_bytes=-1 -> ACCEPT -1
log_backup_count=-1 -> ACCEPT -1
max_retries=0 -> REJECT ValidationError
max_retries=1 -> ACCEPT 1
max_retries=11 -> REJECT ValidationError
log_level=123 -> REJECT AttributeError
log_level=None -> REJECT AttributeError
RotatingFileHandler(maxBytes=-1,backupCount=-1) shouldRollover=False
```

#### CFG-002 — [MEDIUM] [BEST-PRACTICE] Параметры `log_max_bytes` и `log_backup_count` не имеют нижней границы

**Anchor:** `src/vkdownloader/config.py::Settings`
**Disambiguator:** `log_max_bytes: int = Field(`
**Checked:** ran
**Classification:** advisory
**Why this band:** MEDIUM — операционный риск от принятого некорректного значения; не HIGH, поскольку реальное разрастание журнала не измерялось.
**Problem:** Параметры `log_max_bytes` и `log_backup_count` не имеют нижней границы. Отрицательные значения проходят конфигурацию, а стандартный ротатор при отрицательном лимите не выполняет ротацию.
**Repro:** Изолированно сконструировать `Settings(log_max_bytes=-1, log_backup_count=-1)` и `RotatingFileHandler(maxBytes=-1, backupCount=-1)`; модель принимает оба значения, `shouldRollover` возвращает False.
**Impact:** Оператор может неосознанно оставить постоянно растущий журнал и потерять ожидаемую политику хранения.
**Root cause:** В отличие от числовых лимитов загрузки, поля логирования объявлены без `ge`.
**Fix:** Рекомендуется ограничить допустимые значения `Settings.log_max_bytes` и `Settings.log_backup_count` на уровне модели и документировать значение отключения (effort: small; priority: recommended). Это не позволит молча отключить удержание логов.
**Verify:** new test needed: test_log_rotation_rejects_negative_limits

**Evidence — `rg -nH 'log_max_bytes: int|log_backup_count: int|default=10_485_760|default=5' src/vkdownloader/config.py | head -16`** *(исходный код из zip)*:
```text
src/vkdownloader/config.py:97:        default=5.0,
src/vkdownloader/config.py:135:        default=5,
src/vkdownloader/config.py:215:    log_max_bytes: int = Field(
src/vkdownloader/config.py:216:        default=10_485_760,
src/vkdownloader/config.py:219:    log_backup_count: int = Field(
src/vkdownloader/config.py:220:        default=5,
```

**Evidence — `probes/02-settings-validated.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
Pydantic version=2.13.5
Fields=25
log_max_bytes=-1 -> ACCEPT -1
log_backup_count=-1 -> ACCEPT -1
max_retries=0 -> REJECT ValidationError
max_retries=1 -> ACCEPT 1
max_retries=11 -> REJECT ValidationError
log_level=123 -> REJECT AttributeError
log_level=None -> REJECT AttributeError
RotatingFileHandler(maxBytes=-1,backupCount=-1) shouldRollover=False
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
