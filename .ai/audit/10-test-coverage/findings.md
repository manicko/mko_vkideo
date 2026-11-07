---
phase: "10"
phase_name: "test-coverage"
id_prefix: "TST"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/10-audit-test-coverage.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Test Coverage

## Summary

Подтверждено замечаний: 1. Максимальная категория — HIGH. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** конфигурация и воспроизводимость измерения test coverage в CI.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| TST-001 | HIGH | `.github/workflows/packaging-check.yml::"Coverage report"` | CI измеряет coverage, но не задаёт минимальный порог; успешный coverage report не отвергает падение процента покрытия. |

#### TST-001 — [HIGH] [BEST-PRACTICE] CI измеряет coverage, но не задаёт минимальный порог; успешный `coverage report` не отвергает падение процента покрытия.

**Anchor:** `.github/workflows/packaging-check.yml::"Coverage report"`
**Disambiguator:** `run: uv run coverage report`
**Checked:** ran
**Classification:** advisory
**Why this band:** HIGH — отсутствует контроль минимального измеряемого покрытия вне машины разработчика; не CRITICAL, потому что тестовое выполнение в CI присутствует.
**Problem:** CI измеряет coverage, но не задаёт минимальный порог; успешный `coverage report` не отвергает падение процента покрытия.
**Repro:** Считаны конфигурация pytest и workflow; вычислено 0 вхождений `fail-under` при двух существующих шагах coverage.
**Impact:** Изменение, оставляющее существенные ветви без проверок, может проходить существующий pipeline при зелёных тестах.
**Root cause:** Проверка содержит `coverage run` и `coverage report` без `--fail-under` либо конфигурационного эквивалента.
**Fix:** Рекомендуется добавить осмысленный минимальный порог к существующей команде coverage и определить правила его изменения (effort: trivial; priority: recommended). Это превращает уже оплачиваемую метрику в контроль регрессии, без новой инфраструктуры.
**Verify:** new test needed: test_ci_coverage_threshold_is_enforced
**Best-practice reference:** https://coverage.readthedocs.io/en/latest/commands/cmd_reporting.html

**Evidence — `rg -nH 'coverage run|coverage report|Behavioural tests' .github/workflows/packaging-check.yml | head -16`** *(исходный код из zip)*:
```text
.github/workflows/packaging-check.yml:71:      - name: Behavioural tests
.github/workflows/packaging-check.yml:74:        run: uv run coverage run -m pytest tests/
.github/workflows/packaging-check.yml:76:        run: uv run coverage report
```

**Evidence — `probes/10-coverage-gate.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
pytest.ini: absent
tox.ini: absent
setup.cfg: absent
.coveragerc: absent
pyproject.toml: present
tests/conftest.py: present
coverage command: run: uv run coverage run -m pytest tests/
coverage command: run: uv run coverage report
fail-under occurrences in workflow=0
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
