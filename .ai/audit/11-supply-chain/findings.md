---
phase: "11"
phase_name: "supply-chain"
id_prefix: "DEP"
mode: "problems-only"
report_status: "draft"
severity_taxonomy: ".kilo/commands/audit/phases/11-audit-supply-chain.md#severity-taxonomy"
code_ref: "archive-sha256:0c8e5799d6f4"
---

# Audit Findings — Supply Chain

## Summary

Подтверждено замечаний: 2. Максимальная категория — HIGH. Практический риск: изменения могут вызвать проблемы в эксплуатации, безопасности или сопровождении; выводы ограничены фактически проверенными сценариями.

## Scope

**Examined:** определения заданий supply-chain gates и фильтры их запуска.
**Tools:** `rg`, Python AST (с нормализацией только для чтения синтаксиса Python 3.14 / PEP 758), изолированные вызовы Python, `uv` offline, файловая проверка и чтение workflow.
**Not verified:** Полный `uv run pytest` не выполнен: архив требует Python 3.14, среда содержит только 3.13; `uv run --offline pytest -q -p no:cacheprovider` завершился с кодом 2: `No interpreter found for Python 3.14`. Вторая попытка `PYTHONPATH=src python -m pytest` завершилась на импорте `structlog` с кодом 4. Нет браузера/пользовательской сессии/стороннего origin; не выполнялись полные R1–Rn матрицы, Windows-ACL, реальные Windows-сигналы, CI jobs, wheel/sdist build. Изолированные пробы не эквивалентны запуску всей программы. В архиве нет `.git`, поэтому `git ls-files` и git SHA недоступны; пути проверены по zip-манифесту, `code_ref` — SHA-256 архива, не commit.

## Findings

| ID | Severity | Anchor | Title |
|---|---|---|---|
| DEP-001 | HIGH | `.github/workflows/packaging-check.yml::"Advisory scan"` | При любом коде выхода pip-audit, кроме 0 и 1, workflow выводит только warning и продолжает сборку |
| DEP-002 | HIGH | `.github/workflows/packaging-check.yml::"Packaging Check"` | Файл LICENSE объявлен как license-files для распространяемого пакета, но отсутствует в path-фильтре packaging workflow |

#### DEP-001 — [HIGH] [BEST-PRACTICE] При любом коде выхода `pip-audit`, кроме 0 и 1, workflow выводит только warning и продолжает сборку

**Anchor:** `.github/workflows/packaging-check.yml::"Advisory scan"`
**Disambiguator:** `::warning::Advisory database or scanner error`
**Checked:** static
**Classification:** mandatory
**Why this band:** HIGH — проверка безопасности способна перейти в предупредительный режим при отказе механизма, который должен её выполнять; не CRITICAL, поскольку реальная уязвимость не выявлялась.
**Problem:** При любом коде выхода `pip-audit`, кроме 0 и 1, workflow выводит только warning и продолжает сборку. Ошибка самого сканера не блокирует принятие изменений.
**Impact:** Временный сбой базы уязвимостей оставляет выпуск без результата dependency scan, но CI может завершиться успешно.
**Root cause:** В ветке `else` код не вызывает `exit 1`, а завершающий `rm -f` возвращает успешный статус.
**Fix:** Рекомендуется сделать неизвестные ошибки `pip-audit` блокирующими в `.github/workflows/packaging-check.yml`, либо явно ввести видимое ручное исключение с ответственным решением (effort: trivial; priority: recommended). Это исключит тихий обход контроля.
**Verify:** new test needed: test_dependency_scan_errors_fail_ci_job

**Evidence — `rg -nH 'Advisory scan|pip-audit|rc=\$\?|elif \[|::warning::|rm -f /tmp/vkr' .github/workflows/packaging-check.yml | head -16`** *(исходный код из zip)*:
```text
.github/workflows/packaging-check.yml:77:      - name: Advisory scan
.github/workflows/packaging-check.yml:81:          uv export --locked --group dev --no-emit-project -o /tmp/vkr.txt && uv run pip-audit -r /tmp/vkr.txt 2>&1
.github/workflows/packaging-check.yml:82:          rc=$?
.github/workflows/packaging-check.yml:85:          elif [ "$rc" -eq 1 ]; then
.github/workflows/packaging-check.yml:89:            echo "::warning::Advisory database or scanner error (exit $rc) — audit skipped"
.github/workflows/packaging-check.yml:91:          rm -f /tmp/vkr.txt
```

**Evidence — `probes/11-advisory-gate.txt`** *(локальный read-only probe; только синтетические значения)*:
```text
- name: Advisory scan
        if: runner.os == 'Linux'
        run: |
          set +e
          uv export --locked --group dev --no-emit-project -o /tmp/vkr.txt && uv run pip-audit -r /tmp/vkr.txt 2>&1
          rc=$?
          if [ "$rc" -eq 0 ]; then
            echo "No known vulnerabilities detected."
          elif [ "$rc" -eq 1 ]; then
            echo "::error::Known vulnerabilities found in dependencies"
            exit 1
          else
            echo "::warning::Advisory database or scanner error (exit $rc) — audit skipped"
          fi
          rm -f /tmp/vkr.txt
      - name: Build distribution artefacts
        run: uv build --out-dir dist/
      - name: Wheel entry-point smoke
        if: runner.os == 'Linux'
```

#### DEP-002 — [HIGH] [BEST-PRACTICE] Файл `LICENSE` объявлен как `license-files` для распространяемого пакета, но отсутствует в path-фильтре packaging workflow

**Anchor:** `.github/workflows/packaging-check.yml::"Packaging Check"`
**Anchor:** `pyproject.toml::"license-files"`
**Disambiguator:** `".python-version"`
**Checked:** static
**Classification:** advisory
**Why this band:** HIGH — содержимое, объявленное частью дистрибутива, меняется вне триггера проверки; не CRITICAL, так как материал реальной публикации не исследовался.
**Problem:** Файл `LICENSE` объявлен как `license-files` для распространяемого пакета, но отсутствует в path-фильтре packaging workflow. Изменение только LICENSE не запускает его проверки.
**Impact:** Потребитель может получить релиз с изменённым лицензионным содержимым без проверки сборки и состава артефакта на этом изменении.
**Root cause:** Источник состава пакета и набор путей, запускающих gate, рассинхронизированы.
**Fix:** Рекомендуется включить `LICENSE` в триггеры packaging workflow (effort: trivial; priority: recommended), чтобы изменения метаданных дистрибутива не миновали контроль.
**Verify:** new test needed: test_packaging_gate_paths_cover_license_file

**Evidence — `rg -nH '^name: Packaging Check|"pyproject.toml"|".python-version"|"README.md"|".env.example"|"src/\*\*"' .github/workflows/packaging-check.yml | head -16`** *(исходный код из zip)*:
```text
.github/workflows/packaging-check.yml:2:name: Packaging Check
.github/workflows/packaging-check.yml:13:      - "pyproject.toml"
.github/workflows/packaging-check.yml:15:      - ".python-version"
.github/workflows/packaging-check.yml:16:      - "README.md"
.github/workflows/packaging-check.yml:17:      - ".env.example"
.github/workflows/packaging-check.yml:18:      - "src/**"
.github/workflows/packaging-check.yml:23:      - "pyproject.toml"
.github/workflows/packaging-check.yml:25:      - ".python-version"
.github/workflows/packaging-check.yml:26:      - "README.md"
.github/workflows/packaging-check.yml:27:      - ".env.example"
.github/workflows/packaging-check.yml:28:      - "src/**"
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
