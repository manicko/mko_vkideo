# План устранения замечаний аудита VKDownloader

**Тип:** dependency-aware execution DAG / semantic task specifications  
**Проект:** `mko_vkideo-main.zip`  
**Отчёт:** `vkdownloader_audit_findings_01-11(1).zip` — `AUDIT_INDEX.md` + 11 `findings.md`  
**Плановое размещение в репозитории:** `.ai/plans/02_vkdownloader_audit_remediation_plan.md` (после принятия плана).  
**Статус:** план; код не изменён, тесты исправлений не выполнены.

## 1. Входы, доверие к материалам и границы

В исходном zip содержатся код CLI/сервисов/инфраструктуры, `pyproject.toml`, `uv.lock`, workflow, тесты, документация и шаблон **`.ai/tasks/templates/task_template.yaml`**. SHA-256 исходного zip — `0c8e5799d6f473e1067815a46f71e336c8dab12207d28ee699a30f6fd2056b20`, он совпадает с `code_ref` отчёта по префиксу. **18 замечаний: HIGH — 5 (SEC-001, SEC-002, TST-001, DEP-001, DEP-002), MEDIUM — 11, LOW — 2.**

Отчёт аудитора — **`draft`, `problems-only`**, фаза 99 (`validator`) не запускалась. Выводы приняты как *входные задачи*, а не перепроверены или пересмотрены. Доказательство `static` отличается от локальной изолированной пробы `ran`, а потенциальное раскрытие cookie-строки в логах **не является доказанным фактом утечки настоящего секрета**. В baseline аудитора Python 3.14 отсутствовал, вызов pytest с Python 3.13 не прошёл из-за недостающего `structlog`; полной матрицы CI и реального VK/HLS не было. Архив не содержит Git revision. Поэтому V01–V05 и R00 обязательны, но в текущем ответе считаются **NOT RUN**.

Роль planner не предполагает исправление production code, создание реализации или расширение набора требований. Архитектурные альтернативы не объявляются готовыми решениями: для Playwright, FFmpeg и yt-dlp включены decision gates, которые обязаны получить проверяемый результат **до** изменения опасных контрактов. Это не дополнительный аудит исходных findings, а выбор осуществимого способа реализации.

## 2. Система исполнения

- **Единица работы:** одна находка → один изолированный implementation/documentation task (`I`/`D`). `R` — исследование и фиксация решения; `T` — отдельный тест только для нетривиальной границы; `V` — stage/release verification. Каждая запись ниже использует поля исходного YAML-шаблона `id`, `title`, `priority`, `depends_on`, `source_reference`, `source_section`, `description`, `goals`, `files.targets`, `files.semantic_anchors`, `changes`, `acceptance_criteria`. Дополнительные поля: `type`, `risk`, `tests_to_run`, `verifies` и критерии gates.
- **Семантическое таргетирование:** только имена классов/функций, конфиг-ключи, имена workflow steps и заголовки документации. Никаких номеров строк и предположений о смещении кода.
- **Done для I/D:** implementation-only diff, acceptance criteria, локальные целевые тесты/проверки документации и review. Test tasks отданы отдельно только там, где есть риск поведения или переход через границу процесса/API. `depends_on` определяет техническую готовность; порядок ZIP-фаз не определяет очередность разработки.
- **Merge/release:** для I01/I02/I04/I06/I07/I13, public contract и CI gates необходимо успешное `V` либо сознательное удержание релиза. Редакция логов не является компенсацией argv-утечки. При неопределённости приоритет **safety → существующая архитектура → убедительность evidence → инкрементальность**.

## 3. Критические противоречия, которые нельзя объединять молча

| Где | Существующий оракул/контракт | Новый необходимый контракт | Разрешение |
|---|---|---|---|
| `tests/test_ffmpeg_transport.py::test_ffmpeg_transport_no_secrets_in_argv` | Тест явно *допускает* cookie в `-headers` и `token=SECRET` в `-i` | Ни одного синтетического токена в `argv` | R01 → I01 → T01; не «озеленять» старый тест без исправления транспорта |
| `tests/test_downloader_throttle.py::test_retry_after_ceiling_applies_after_max` | Требует обрезать длинный server delay до 30 s | Нельзя повторить раньше Retry-After | I05 → T05; jitter ceiling и server floor разделяются |
| `tests/test_browser_infrastructure.py::test_select_suspends_host_filter_when_all_non_vk` | Требует unsafe fallback на внешний host | No-match не отдаёт untrusted URL | R03 → I04 → T04; не расширять trusted hosts без evidence |
| `tests/test_browser_infrastructure.py::test_network_monitor_skips_oversized_body_without_content_length` | Текущие пробы ограничивают body после материализации | Не читать неограниченный body до проверки размера | R04 → I06 → T06 |
| `tests/test_cli.py::test_batch_non_utf8_url_file_reports_designed_error` | Ожидает общий catch-all | Ожидает `Failed to read URL file` | I12, тест обновляется inline |
| `tests/test_hls_downloader.py::test_check_ffmpeg_available_write_once_when_false` | Считает вечный False-кэш нормой | Последующая операция видит новый бинарник | I08, старый тест заменяется inline |
| `tests/test_batch_downloader.py` (`_print_batch_summary`/`run_batch`) | Закреплён сервисный вывод и код возврата | Только сервисные данные; CLI форматирует и выбирает 0/1/130 | R05 → I13 → T08 одним атомарным контрактным переходом |
| `--cookies -` в `_build_ytdlp_cli_command` | stdin занят cookie-файлом | URL тоже требуется убрать из `argv` | R02 выбирает реально совместимый механизм, без двух потребителей stdin |
| Отсутствие `Content-Length` в Playwright | `Response.body()` загружает весь ответ | Peak memory ограничен *до* чтения | R04 выбирает streaming только если он доказан в используемом API; иначе безопасный skip |

**Условные решения:** если R01/R02 не находят технически совместимого способа устранить секреты из argv, это не «готово с документацией». Находка сохраняет статус **OPEN/HOLD**; владелец принимает отдельное решение об ограничении/отключении затронутого транспорта либо о документированном остаточном риске. Такой альтернативный путь не запускается одновременно с безопасной реализацией и не объявляется эквивалентом исправления. Изменение порога coverage допускается только после R06; конкретный процент здесь не выдуман.

## 4. Этапы, зависимости и параллельность

Результирующий граф — **DAG**, а не последовательность разделов отчёта. Параллельное выполнение разрешено для задач с непересекающимися write targets; tasks в одном модуле или одном YAML workflow должны проходить последовательный merge/rebase review.

| Волна готовности | Разрешённые работы | Контроль / блокирующая граница |
|---|---|---|
| A. Независимый старт | R00; параллельно I15, I16, D01, D02 | Быстрые CI/docs изменения не ждут сетевой/секретной миграции; объединение workflow diff I15/I16 вручную |
| B. Решения + локальные патчи | После R00: R01–R05 и I03, I05, I07–I12 | Разные ownership: sanitizer, retry, signals, FFmpeg cache, config, filesystem, CLI decoder; I09/I10 последовательный merge одного `config.py` |
| C. Контрактные изменения | R01→I01; R02→I02; R03→I04; R04→I06; R05→I13; I10→D03 | I01/I02 зависят также от I03; I04 и I06 оба правят `network_monitor.py`, последовательная интеграция без смешения concerns |
| D. Тесты и stage gates | I01→T01, I02→T02, I03→T03, I04→T04, I05→T05, I06→T06, I07→T07, I13→T08; затем V01/V02/V03 | V01/V02/V03 независимы после своих upstream; нельзя закрывать их по mock-only тестам, где нужна настоящая subprocess граница |
| E. CI quality и итог | V01+V02+V03 → R06 → I14 → V04; параллельно предварительно готовы I15/I16; все V → V05 | Зафиксировать реальный threshold, scanner rc matrix, LICENSE-only triggers; финальный release gate до объединения изменений |

**Матрица shared-write конфликтов:** `network_monitor.py`: I04 → I06 при одной ветке/одной рабочей копии (не причинная зависимость, а эксклюзивная запись; можно реализовать параллельно в разных ветках и слить последовательно). `config.py`: I09/I10 — отдельные PR. `packaging-check.yml`: I15/I16/I14 — независимые логически, но конфликтующие по одному YAML, интеграция последовательно. `tests/test_browser_infrastructure.py`: T04/T06 — независимые сценарии, merge последовательно. `cli.py`: I12/I13 — отдельные scopes функций, но merge review обязателен. `url_sanitizer.py` обязателен до завершения SEC transport test gates.

## 5. Полный реестр замечаний → задач и проверок

| Audit ID | Severity | Decision/исправление | Тест/проверка | Выпуск |
|---|---|---|---|---|
| ENT-001 | MEDIUM | R05 → I13 | T08 → V03 | V05 |
| CFG-001 | MEDIUM | I09 | inline → V03 | V05 |
| CFG-002 | MEDIUM | I10 → D03 | inline → V03 | V05 |
| NET-001 | MEDIUM | R03 → I04 | T04 → V02 | V05 |
| NET-002 | MEDIUM | I05 | T05 → V02 | V05 |
| NET-003 | MEDIUM | R04 → I06 | T06 → V02 | V05 |
| CON-001 | LOW | I07 | T07 → V03 | V05 |
| PRC-001 | LOW | I08 | inline → V03 | V05 |
| SEC-001 | HIGH | R01 → I01 | T01 → V01 | V05 |
| SEC-002 | HIGH | R02 → I02 | T02 → V01 | V05 |
| SEC-003 | MEDIUM | I03 | T03 → V01 | V05 |
| ART-001 | MEDIUM | I11 | inline → V03 | V05 |
| OUT-001 | MEDIUM | I12 | inline → V03 | V05 |
| QLT-001 | MEDIUM | D01 | inline → V03 | V05 |
| QLT-002 | LOW | D02 | links → V03 | V05 |
| TST-001 | HIGH | R06 → I14 | V04 | V05 |
| DEP-001 | HIGH | I15 | V04 | V05 |
| DEP-002 | HIGH | I16 | V04 | V05 |

## 6. Исполнимые задачи — спецификации по task_template.yaml

Ниже `source_file` означает файл **в архиве аудитора**, а `files` — семантические мишени в **исходном проекте**. `mode: read-only` у research/verification означает только анализ. `tests_to_run` у простых задач означает inline validation, **не отдельную тестовую задачу**. `changes` описывает ожидаемый эффект, **не содержит реализационного кода**.

### 6.1. Decision/research gates

#### R00 — Восстановить воспроизводимый baseline Python 3.14

```yaml
id: R00
title: Восстановить воспроизводимый baseline Python 3.14
type: research_gate
status: pending
priority: high
risk: high
depends_on: []
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
- CFG-001
- CFG-002
- NET-001
- NET-002
- NET-003
- CON-001
- PRC-001
- SEC-001
- SEC-002
- SEC-003
- ART-001
- OUT-001
- QLT-001
- QLT-002
- TST-001
- DEP-001
- DEP-002
source_file:
- .ai/audit/01-entry-architecture/findings.md
- .ai/audit/02-config/findings.md
- .ai/audit/03-network-resilience/findings.md
- .ai/audit/04-concurrency-cancellation/findings.md
- .ai/audit/05-subprocess-browser/findings.md
- .ai/audit/06-credentials-secrets/findings.md
- .ai/audit/07-filesystem-artifacts/findings.md
- .ai/audit/08-cli-observability/findings.md
- .ai/audit/09-code-quality/findings.md
- .ai/audit/10-test-coverage/findings.md
- .ai/audit/11-supply-chain/findings.md
description: Создать исполняемую, не меняющую продукт конфигурацию контроля. Аудитор не смог запустить полный
  suite из-за Python 3.14 и structlog; наличие зелёной базы не предполагается.
goals:
- Получить версии Python 3.14/uv и установленные зависимости из uv.lock
- Запустить базовые проверки и зафиксировать результаты/падения до изменений
- Отделить исходные падения от будущих регрессий и отметить ограничения внешних интеграций
files:
- path: pyproject.toml
  mode: read-only
  targets:
  - type: config
    name: project.requires-python
  - type: config
    name: dependency-groups
  semantic_anchors:
  - requires-python; dev dependencies
- path: .python-version
  mode: read-only
  targets:
  - type: config
    name: python-version
  semantic_anchors:
  - Версия целевого интерпретатора
- path: uv.lock
  mode: read-only
  targets:
  - type: config
    name: locked-dependencies
  semantic_anchors:
  - Lockfile как единственный источник разрешённых пакетов
- path: tests/conftest.py
  mode: read-only
  targets:
  - type: module
    name: tests.conftest
  semantic_anchors:
  - Путь инициализации тестовой конфигурации
changes:
- action: capture_evidence
  description: Записать версии и исходы `uv sync --locked`, `uv run pytest tests/ tests/integration/ -rs`, Ruff,
    mypy и доступные бинарные зависимости; не править код для «озеленения».
acceptance_criteria:
- Baseline прикреплён к плану исполнения; нет заявлений о ранее не запускались тестах
- Рантайм Python 3.14 доступен для последующих verification gates либо все затронутые задачи помечаются blocked
- Изменение baseline не смешано с исправлениями аудита
tests_to_run:
- uv sync --locked
- uv run pytest tests/ tests/integration/ -rs
- uv run ruff check src tests
- uv run mypy src
deliverable: 'Протокол baseline: interpreter/dependency versions, status commands, pre-existing failures; no source
  changes.'
```

#### R01 — Выбрать технически подтверждённый безопасный FFmpeg input contract

```yaml
id: R01
title: Выбрать технически подтверждённый безопасный FFmpeg input contract
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-001
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: До изменения транспортного интерфейса определить, допускает ли установленный FFmpeg ввод подписанного
  URL и HTTP Cookie без раскрытия значений в argv. Не считать file/pipe/@file режимы поддерживаемыми без локальной
  пробы; документировать сохраняемые риски.
goals:
- Проверить поддерживаемые FFmpeg механизмы и контекст FfmpegTransport.download
- Согласовать один не раскрывающий argv вариант либо зафиксировать невозможность закрыть риск
- Проверить Windows/POSIX, HLS, отмену и закрытие временных артефактов
files:
- path: src/vkdownloader/services/ffmpeg_transport.py
  mode: read-only
  targets:
  - type: class
    name: FfmpegTransport
  - type: method
    name: FfmpegTransport.download
  semantic_anchors:
  - ffmpeg_args; headers_content; `asyncio.create_subprocess_exec`
- path: src/vkdownloader/services/ffmpeg_utils.py
  mode: read-only
  targets:
  - type: function
    name: cancel_subprocess
  - type: function
    name: read_progress
  semantic_anchors:
  - Процессный lifecycle и чтение прогресса
- path: tests/test_ffmpeg_transport.py
  mode: read-only
  targets:
  - type: function
    name: test_ffmpeg_transport_no_secrets_in_argv
  semantic_anchors:
  - Тест, допускающий секреты в аргументах
changes:
- action: record_decision
  description: Записать исполнимый безопасный протокол запуска, решение о cleanup, правах и поведении при ошибке.
    Если скрыть данные невозможно — блокировать утверждение «SEC-001 fixed», запросить явное решение владельца
    о дальнейшей эксплуатации/ограничении транспорта.
acceptance_criteria:
- Выбран ровно один проверенный подход, сохранена совместимость с FFmpeg/HLS
- Невозможность устранения argv-утечки не замаскирована лог-редакцией
- Нет произвольного перепроектирования транспорта
deliverable: 'Decision record SEC-001: chosen mechanism, evidence, supported platforms, reject/fallback outcome.'
```

#### R02 — Выбрать безопасный канал передачи URL в yt-dlp при наличии cookies

```yaml
id: R02
title: Выбрать безопасный канал передачи URL в yt-dlp при наличии cookies
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-002
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: 'Проверить реально поддерживаемый вход yt-dlp для signed playlist URL без его помещения в argv. Учесть,
  что `--cookies -` уже использует stdin: нельзя одновременно отдавать в тот же поток и URL, и cookie-файл.'
goals:
- Подтвердить рабочую форму передачи URL без argv
- Выбрать один совместимый с cookies способ, не снижая прав доступа к данным
- Установить контракт временных объектов, cancel/resume и сохранения output
files:
- path: src/vkdownloader/services/ytdlp_downloader.py
  mode: read-only
  targets:
  - type: function
    name: _build_ytdlp_cli_command
  - type: function
    name: _download_with_ytdlp
  semantic_anchors:
  - '`cmd.append(m3u8_url)`; stdin= cookie_stdin'
- path: src/vkdownloader/services/ytdlp_downloader.py
  mode: read-only
  targets:
  - type: function
    name: _create_temp_cookie_file
  - type: function
    name: _remove_cookie_artifact_dir
  semantic_anchors:
  - Приватные cookie-артефакты и cleanup
changes:
- action: record_decision
  description: Верифицировать выбранный контракт через локальный yt-dlp, включая `--cookies -` и скачивание без
    cookies; если совместимый канал отсутствует, оставить SEC-002 открытым и заблокировать выпуск соответствующего
    пути.
acceptance_criteria:
- Signed URL отсутствует в argv в выбранной экспериментальной схеме
- Cookie-данные не переводятся в менее защищённый канал
- Отмечены платформенные и operational ограничения
deliverable: 'Decision record SEC-002: validated invocation/input channels, cleanup policy and compatibility evidence.'
```

#### R03 — Определить допустимые origins для сетевого выбора HLS

```yaml
id: R03
title: Определить допустимые origins для сетевого выбора HLS
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-001
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Сопоставить действующий список ALLOWED_HOST_SUFFIXES и действующие доверенные VK/CDN маршруты. Запретить
  небезопасный fallback, не выдумывая список доменов и не подменяя результат аудита новой политикой доступа.
goals:
- Зафиксировать явные допустимые источники и процедуру корректировки политики
- Определить безопасное поведение при отсутствии одобренных кандидатов
- Учесть существующие тесты, которые ожидают небезопасную suspension-ветку
files:
- path: src/vkdownloader/infrastructure/network_monitor.py
  mode: read-only
  targets:
  - type: class
    name: NetworkMonitor
  - type: method
    name: NetworkMonitor._is_allowed_host
  - type: method
    name: NetworkMonitor.select
  semantic_anchors:
  - ALLOWED_HOST_SUFFIXES; `_is_allowed_host`; `select`
- path: tests/test_browser_infrastructure.py
  mode: read-only
  targets:
  - type: function
    name: test_select_suspends_host_filter_when_all_non_vk
  semantic_anchors:
  - Фиксация suspension fallback
changes:
- action: record_decision
  description: Сохранить только подтверждённые источники; определить, как downloader сообщает «нет допустимого
    потока», не обращаясь к localhost/private адресам.
acceptance_criteria:
- Определён fail-closed маршрут и поведение при легитимном CDN, где оно подтверждено
- Не разрешены произвольные внешние IP/host в качестве универсального fallback
deliverable: Origin-selection policy with explicit allowed cases and no-match behavior.
```

#### R04 — Выбрать ограниченный по памяти способ инспекции Playwright response

```yaml
id: R04
title: Выбрать ограниченный по памяти способ инспекции Playwright response
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-003
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Playwright Response.body() материализует содержимое полностью; выяснить, есть ли реальная потоковая
  граница для используемой версии API. Если нет, выбрать консервативный отказ от чтения неизвестного объёма и
  сохранить возможность захвата URL по адресу.
goals:
- Определить допустимые response types без полной materialization
- Зафиксировать поведение при отсутствующем/некорректном Content-Length
- Проверить совместимость с классификацией HLS и JSON-поиском URL
files:
- path: src/vkdownloader/infrastructure/network_monitor.py
  mode: read-only
  targets:
  - type: method
    name: NetworkMonitor._read_bounded_body
  - type: method
    name: NetworkMonitor._intercept_response
  semantic_anchors:
  - '`_read_bounded_body`; `_intercept_response`'
- path: tests/test_browser_infrastructure.py
  mode: read-only
  targets:
  - type: function
    name: test_network_monitor_skips_oversized_body_without_content_length
  semantic_anchors:
  - Тест oversized response с неизвестной длиной
changes:
- action: record_decision
  description: Описать выбранный способ, который гарантирует не читать неизвестный/заведомо большой body через
    all-at-once API, или подтвердить реальный bounded-stream API.
acceptance_criteria:
- Решение не полагается на `len(await response.body())` для контроля пикового потребления памяти
- Определены допустимые потери classification и fallback на URL capture
deliverable: Bounded-response decision with guaranteed memory-safety precondition.
```

#### R05 — Определить совместимый контракт результата batch-сервиса

```yaml
id: R05
title: Определить совместимый контракт результата batch-сервиса
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
source_file:
- .ai/audit/01-entry-architecture/findings.md
description: run_batch используется cli.batch_download и тестами; определить семантику структурированного результата
  и совместимость вызывающих сторон до изменения возвращаемого типа и печати.
goals:
- Сопоставить все вызовы run_batch и _print_batch_summary
- Зафиксировать структуру результата без CLI-specific types
- Зафиксировать код 0/1/130, skipped_count, порядок строк и UX без обратного импорта Typer в сервис
files:
- path: src/vkdownloader/services/batch_downloader.py
  mode: read-only
  targets:
  - type: function
    name: run_batch
  - type: function
    name: _run_batch_with_progress
  - type: function
    name: _print_batch_summary
  semantic_anchors:
  - '`run_batch` → `_run_batch_with_progress` → `_print_batch_summary`'
- path: src/vkdownloader/cli.py
  mode: read-only
  targets:
  - type: function
    name: batch_download
  semantic_anchors:
  - '`batch_download` → `_run_batch_with_signal_handlers`'
- path: tests/test_batch_downloader.py
  mode: read-only
  targets:
  - type: module
    name: tests.test_batch_downloader
  semantic_anchors:
  - Существующие сервисные оракулы returncode/печати
changes:
- action: record_decision
  description: Описать одновременное внедрение изменения обеих границ одним атомарным PR, миграционные последствия
    для неизвестных API-consumers и критерии совместимости интерфейса CLI.
acceptance_criteria:
- Нельзя выпускать сервис с изменённым контрактом до адаптации CLI
- Принята стратегия публичной совместимости или явно обозначено breaking change
- Предусмотрен сценарий cancel → exit 130
deliverable: Batch result contract decision and consumer inventory.
```

#### R06 — Согласовать coverage gate по измеренному baseline

```yaml
id: R06
title: Согласовать coverage gate по измеренному baseline
type: decision_gate
status: pending
priority: high
risk: high
depends_on:
- V01
- V02
- V03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- TST-001
source_file:
- .ai/audit/10-test-coverage/findings.md
description: После фиксации поведения и новых тестов измерить итоговое покрытие и выбрать обоснованный минимальный
  порог для CI; не угадывать процент и не использовать порог, который полностью обесценивает gate.
goals:
- Зафиксировать измерение на Python 3.14 и охват включаемых файлов
- Записать числовой порог и условия его изменения
- Подтвердить, что новые/изменённые тесты не скрывают ключевые ветви
files:
- path: .github/workflows/packaging-check.yml
  mode: read-only
  targets:
  - type: workflow_step
    name: Coverage report
  semantic_anchors:
  - Шаги `Coverage measurement` и `Coverage report`
- path: pyproject.toml
  mode: read-only
  targets:
  - type: config
    name: coverage
  semantic_anchors:
  - Конфигурация coverage, если присутствует
changes:
- action: record_decision
  description: Сохранить baseline report и утверждённое число с пояснением. Отдельно определить проверку, которая
    преднамеренно должна уронить gate при нарушении порога.
acceptance_criteria:
- Число порога выведено из воспроизводимого измерения, а не предположения
- Снижение порога допускается только отдельным мотивированным решением
deliverable: Signed coverage baseline and minimum threshold decision.
```

### 6.2. Isolated implementation tasks

#### I01 — Исключить Cookie и signed URL из FFmpeg argv

```yaml
id: I01
title: Исключить Cookie и signed URL из FFmpeg argv
type: implementation
status: pending
priority: high
risk: high
depends_on:
- R01
- I03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-001
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Применить единственный проверенный R01 контракт входа к FfmpegTransport.download. Убрать значения
  Cookie и signed media URL из argv; сохранить HLS-скачивание, сохранность staged-файлов, таймауты и cleanup.
goals:
- Не передавать синтетические cookie/token в argv
- Сохранить настройки user-agent/referer/ssl_verify без непреднамеренного ослабления
- Не сломать cancellation и cleanup
files:
- path: src/vkdownloader/services/ffmpeg_transport.py
  mode: change
  targets:
  - type: class
    name: FfmpegTransport
  - type: method
    name: FfmpegTransport.download
  semantic_anchors:
  - Формирование `headers_content`/`ffmpeg_args` перед `asyncio.create_subprocess_exec`
- path: src/vkdownloader/services/ffmpeg_utils.py
  mode: change
  targets:
  - type: function
    name: cancel_subprocess
  - type: function
    name: read_progress
  semantic_anchors:
  - Только если выбранная схема использует существующие lifecycle/helpers
changes:
- action: modify_code
  description: Перенести чувствительные данные в подтверждённый непубличный канал из R01, обработать ошибки и
    удалить временные ресурсы на success/failure/cancel.
acceptance_criteria:
- argv процесса не содержит URL query-token, Cookie и Set-Cookie
- Входной плейлист доступен FFmpeg без потери авторизации
- Не создан новый постоянно живущий plaintext артефакт
- Если R01 не нашёл безопасный вариант — задача blocked, не считается выполненной
tests_to_run:
- uv run pytest tests/test_ffmpeg_transport.py -q
```

#### I02 — Убрать signed playlist URL из argv yt-dlp

```yaml
id: I02
title: Убрать signed playlist URL из argv yt-dlp
type: implementation
status: pending
priority: high
risk: high
depends_on:
- R02
- I03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-002
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Использовать утверждённый в R02 ввод playlist URL, сохраняя cookie источник, поток прогресса, возобновление
  и директории артефактов. Не переносить plaintext токен в stdout/stderr или world-readable temp.
goals:
- URL с query-токеном не виден в argv
- yt-dlp работает с cookies и без cookies
- Временные ресурсы удаляются при normal/error/cancel
files:
- path: src/vkdownloader/services/ytdlp_downloader.py
  mode: change
  targets:
  - type: function
    name: _build_ytdlp_cli_command
  - type: function
    name: _download_with_ytdlp
  semantic_anchors:
  - '`_build_ytdlp_cli_command`; добавление `m3u8_url` перед spawn; `spawn_kwargs`'
- path: src/vkdownloader/services/ytdlp_downloader.py
  mode: change
  targets:
  - type: function
    name: _create_temp_cookie_file
  - type: function
    name: _remove_cookie_artifact_dir
  semantic_anchors:
  - При необходимости повторно использовать private cookie artifact lifecycle
changes:
- action: modify_code
  description: Заменить небезопасный позиционный URL на проверенный R02 канал и согласовать отдельный ввод cookies
    без конфликтов stdin.
acceptance_criteria:
- Signed URL отсутствует в списке аргументов
- Выходные медиа, resume, progress и прерывания работают в согласованных сценариях
- Не ухудшены права на cookie/token-bearing temp
- Нет неподтверждённых механизмов ввода
tests_to_run:
- uv run pytest tests/test_ytdlp_downloader.py -q
```

#### I03 — Редактировать cookie-header и token пары перед лог-синками

```yaml
id: I03
title: Редактировать cookie-header и token пары перед лог-синками
type: implementation
status: pending
priority: high
risk: medium
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-003
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Расширить центральную функцию sanitizer на формы `Cookie:`, `Set-Cookie:` и релевантные голые cookie-пары,
  не раскрывая значения и не искажая не-секретные диагностические маркеры.
goals:
- Скрыть header значения и известные cookie пары
- Сохранить редактирование URL и путей cookie artifacts
- Сохранить idempotence и безопасную обработку смешанного текста
files:
- path: src/vkdownloader/utils/url_sanitizer.py
  mode: change
  targets:
  - type: function
    name: sanitize_text_for_log
  - type: function
    name: sanitize_url_for_log
  - type: function
    name: redact_log_event
  semantic_anchors:
  - '`sanitize_text_for_log` → `redact_log_event`/`sanitize_for_log`'
changes:
- action: modify_code
  description: Обновить центральную нормализацию/редакцию текстовых полей без широкого «вырезать все key=value»,
    избежав ложного разрушения обычной диагностики.
acceptance_criteria:
- Синтетические маркеры в Cookie/Set-Cookie и самостоятельных cookie-парах отсутствуют в результате
- Повторная санитаризация не восстанавливает и не меняет редактирование
- URL hosts/нечувствительные слова сохраняются
tests_to_run:
- uv run pytest tests/test_url_sanitizer.py -q
```

#### I04 — Сделать выбор HLS URL fail-closed по trusted hosts

```yaml
id: I04
title: Сделать выбор HLS URL fail-closed по trusted hosts
type: implementation
status: pending
priority: high
risk: high
depends_on:
- R03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-001
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Устранить fallback, который в NetworkMonitor.select возвращает внешние адреса без разрешения. Учитывать
  не только no-match, но и exception fallback; не нарушить ранжирование master/media среди одобренных HLS URLs.
goals:
- Неразрешённый кандидат никогда не выходит из select
- Легитимный разрешённый URL остаётся доступным
- При отсутствии кандидата возвращается диагностируемый безопасный результат
files:
- path: src/vkdownloader/infrastructure/network_monitor.py
  mode: change
  targets:
  - type: class
    name: NetworkMonitor
  - type: method
    name: NetworkMonitor.select
  - type: method
    name: NetworkMonitor._is_allowed_host
  - type: method
    name: NetworkMonitor._log_host_suspension
  semantic_anchors:
  - '`select` → `_is_allowed_host`; `_log_host_suspension`; exception branch'
changes:
- action: modify_code
  description: Сохранить approved-host filtering на всех ветках select; убрать возврат unconstrained captured
    list при no-match и исключениях; оставить диагностику без чувствительных URL.
acceptance_criteria:
- Только foreign/loopback candidates → нет пригодных URL
- Mixed trusted/foreign → выдаются только trusted
- Сохранено ordering media before master и отсутствие исключений при плохом URL
tests_to_run:
- uv run pytest tests/test_browser_infrastructure.py -q
```

#### I05 — Уважать Retry-After выше локального backoff ceiling

```yaml
id: I05
title: Уважать Retry-After выше локального backoff ceiling
type: implementation
status: pending
priority: high
risk: medium
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-002
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Развести предел клиентского jitter и минимальный серверный cooldown, либо использовать утверждённый
  отказ от повторного запроса при запрещённом длительном ожидании. Не инициировать ранний retry при 429.
goals:
- Локальный jitter остаётся ограничен
- Положительный Retry-After не обрезается до 30s с ранним повтором
- Ожидание прерываемо через shutdown_event
files:
- path: src/vkdownloader/services/retry_policies.py
  mode: change
  targets:
  - type: function
    name: _compute_backoff_delay
  - type: function
    name: _wait_with_shutdown
  - type: function
    name: _retry_429_with_backoff
  semantic_anchors:
  - '`_compute_backoff_delay` → `_wait_with_shutdown` → `_retry_429_with_backoff`'
changes:
- action: modify_code
  description: Разделить локальный jitter cap и серверное значение; для запретительного cooldown не повторять
    ранее deadline и сохранить bounded attempts.
acceptance_criteria:
- Retry-After 120s не приводит к повтору через 30s
- Нет бесконечного ожидания при cancel или exhaustion
- Форматы Retry-After из `_parse_retry_after` не изменились
tests_to_run:
- uv run pytest tests/test_downloader_throttle.py tests/integration/test_hls_fixture.py -q
```

#### I06 — Запретить all-at-once чтение неизвестно больших response bodies

```yaml
id: I06
title: Запретить all-at-once чтение неизвестно больших response bodies
type: implementation
status: pending
priority: high
risk: high
depends_on:
- R04
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-003
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Применить решение R04 к инспекции JSON и HLS playlist в NetworkMonitor. Контроль должен действовать
  до полной материализации ответа; отсутствие Content-Length не трактуется как «безопасный размер».
goals:
- Устранить неограниченное Response.body() на chunked/unknown-length ответах
- Сохранить capture URL по заголовку/адресу без полной загрузки body
- Не допустить OOM на заведомо большом Content-Length
files:
- path: src/vkdownloader/infrastructure/network_monitor.py
  mode: change
  targets:
  - type: method
    name: NetworkMonitor._read_bounded_body
  - type: method
    name: NetworkMonitor._intercept_response
  semantic_anchors:
  - '`_read_bounded_body`; обе ветки чтения тела в `_intercept_response`'
changes:
- action: modify_code
  description: Добавить согласованную R04 pre-read границу либо реализацию реально bounded-read; при невозможности
    безопасного body-read отказаться от анализа тела, не ломая URL-only capture.
acceptance_criteria:
- На безразмерном большом ответе не вызывается небезопасное полное чтение
- Известный малый ответ продолжает классифицироваться и извлекать HLS URL
- Классификация UNCLASSIFIED допустима, но downloader не рушится
tests_to_run:
- uv run pytest tests/test_browser_infrastructure.py -q
```

#### I07 — Восстановить исходный POSIX signal handler при cleanup

```yaml
id: I07
title: Восстановить исходный POSIX signal handler при cleanup
type: implementation
status: pending
priority: medium
risk: high
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- CON-001
source_file:
- .ai/audit/04-concurrency-cancellation/findings.md
description: Согласовать loop.add_signal_handler/remove_signal_handler с текущим сохранением process-level диспозиций.
  Не затереть сторонний обработчик; сохранить first/second/third interrupt и fallback для Windows.
goals:
- Предыдущий SIGINT/SIGTERM восстанавливается внутри действующего asyncio.Runner
- При повторной регистрации нет stale state
- Не ухудшается policy эскалации второго прерывания
files:
- path: src/vkdownloader/services/signal_handlers.py
  mode: change
  targets:
  - type: function
    name: setup_signal_handlers
  - type: function
    name: cleanup_signal_handlers
  - type: function
    name: _capture_previous_handler
  - type: function
    name: _restore_previous_handler
  semantic_anchors:
  - '`setup_signal_handlers`, `_capture_previous_handler`, `_restore_previous_handler`, `cleanup_signal_handlers`'
changes:
- action: modify_code
  description: На loop-registration зафиксировать предшествующую диспозицию и корректно её восстановить, не вмешиваясь
    в изменение третьей стороной.
acceptance_criteria:
- После cleanup в том же Runner SIGINT handler идентичен предшествующему
- Вне Runner и на Windows fallback поведение не регрессирует
- Повторный сигнал по-прежнему приводит к контролируемой эскалации
tests_to_run:
- uv run pytest tests/test_hls_downloader.py -q
```

#### I08 — Ограничить срок отрицательного кэша доступности FFmpeg

```yaml
id: I08
title: Ограничить срок отрицательного кэша доступности FFmpeg
type: implementation
status: pending
priority: low
risk: low
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- PRC-001
source_file:
- .ai/audit/05-subprocess-browser/findings.md
description: Устранить write-once False при изменении доступного бинарника в течение долгой сессии. Минимальный
  механизм — повторная проверка на границе нового запуска/необходимости бинарника, не perpetual polling.
goals:
- Отрицательный результат обновляется после изменения PATH
- Не добавлены необоснованные повторные probe на каждом сегменте
- Не меняется проверка ffprobe/version и fallback selector
files:
- path: src/vkdownloader/services/ffmpeg_utils.py
  mode: change
  targets:
  - type: function
    name: check_ffmpeg_available
  - type: variable
    name: _ffmpeg_available
  semantic_anchors:
  - '`_ffmpeg_available` и `check_ffmpeg_available`'
- path: src/vkdownloader/services/downloader.py
  mode: change
  targets:
  - type: module
    name: services.downloader
  semantic_anchors:
  - Места проверки FFmpeg при выборе backend
changes:
- action: modify_code
  description: Выбрать локальную operation-boundary переоценку доступности либо ограниченную инвалидацию кэша,
    не меняя остальные helpers.
acceptance_criteria:
- После no-binary следующая операция видит появившийся ffmpeg
- Старый тест write-once False заменён на требуемую политику; остальные проверки остаются
tests_to_run:
- uv run pytest tests/test_hls_downloader.py -q
```

#### I09 — Нормализовать типовую ошибку log_level через Pydantic

```yaml
id: I09
title: Нормализовать типовую ошибку log_level через Pydantic
type: implementation
status: pending
priority: medium
risk: low
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- CFG-001
source_file:
- .ai/audit/02-config/findings.md
description: 'Сделать Settings.normalize_log_level total validator: поддержать LogLevel и корректные строки; прочие
  входные типы направить через ValueError к ValidationError, сохраняя скрытие входных значений.'
goals:
- При неподдерживаемом типе не выбрасывать AttributeError
- Не изменять регистронезависимую нормализацию
- Не выводить чувствительное сырое значение в диагностике
files:
- path: src/vkdownloader/config.py
  mode: change
  targets:
  - type: class
    name: Settings
  - type: method
    name: Settings.normalize_log_level
  semantic_anchors:
  - '`Settings.normalize_log_level`'
changes:
- action: modify_code
  description: До `.upper()` проверить входной тип; для невалидного значения использовать Pydantic-compatible
    validation exception.
acceptance_criteria:
- Settings(log_level=123) → ValidationError
- INFO/info/LogLevel значения работают как ранее
- Критерии проверены existing tests/test_config.py + новый case
tests_to_run:
- uv run pytest tests/test_config.py -q
```

#### I10 — Ограничить числовые поля ротации логов

```yaml
id: I10
title: Ограничить числовые поля ротации логов
type: implementation
status: pending
priority: medium
risk: medium
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- CFG-002
source_file:
- .ai/audit/02-config/findings.md
description: Добавить нижние границы в Settings.log_max_bytes и Settings.log_backup_count, не меняя без основания
  значения по умолчанию и текущий lifecycle RotatingFileHandler.
goals:
- Отрицательные значения отвергаются до инициализации логирования
- Сохранены действующие defaults
- Семантика нулей определена и задокументирована отдельно
files:
- path: src/vkdownloader/config.py
  mode: change
  targets:
  - type: class
    name: Settings
  - type: field
    name: Settings.log_max_bytes
  - type: field
    name: Settings.log_backup_count
  semantic_anchors:
  - Fields `log_max_bytes`, `log_backup_count` в Settings
- path: src/vkdownloader/config.py
  mode: read-only
  targets:
  - type: function
    name: setup_logging
  semantic_anchors:
  - '`setup_logging` → RotatingFileHandler'
changes:
- action: modify_code
  description: Зафиксировать Pydantic ge для полей и сохранить точное типовое сообщение ошибки в Settings.
acceptance_criteria:
- Settings(log_max_bytes=-1) и Settings(log_backup_count=-1) → ValidationError
- 0 принимается/отвергается согласно фактическому контракту и согласованному D03 описанию
- Положительные значения и default rotation работают
tests_to_run:
- uv run pytest tests/test_config.py -q
```

#### I11 — Разделить ошибку длины пути и PATH_TRAVERSAL

```yaml
id: I11
title: Разделить ошибку длины пути и PATH_TRAVERSAL
type: implementation
status: pending
priority: medium
risk: medium
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ART-001
source_file:
- .ai/audit/07-filesystem-artifacts/findings.md
description: Не обозначать корректный длинный путь как атакующий traversal; согласовать предел с целевыми платформами,
  не отменяя проверки symlink/junction containment.
goals:
- Отдельная диагностика для path length
- Платформенная политика объяснима и тестируема
- Проверки traversal/symlink/junction остаются включены
files:
- path: src/vkdownloader/utils/security.py
  mode: change
  targets:
  - type: function
    name: validate_final_output_path
  - type: variable
    name: MAX_OUTPUT_PATH_LENGTH
  semantic_anchors:
  - '`MAX_OUTPUT_PATH_LENGTH`; проверки длины в `validate_final_output_path`'
- path: src/vkdownloader/models/enums.py
  mode: change
  targets:
  - type: class
    name: ErrorCode
  semantic_anchors:
  - '`ErrorCode.PATH_TRAVERSAL` и тип отдельной ошибки длины, если нужен'
- path: src/vkdownloader/exceptions.py
  mode: change
  targets:
  - type: class
    name: DownloadError
  semantic_anchors:
  - Классификация DownloadError без подмены traversal
changes:
- action: modify_code
  description: Выделить независимый семантический error code/message для ограничения длины; решение о пороге принять
    на основе Windows/Linux политики, а не подставлять произвольное значение.
acceptance_criteria:
- Легитимный длинный путь либо разрешён на поддерживающей платформе, либо отклонён именно как length limitation
- PATH_TRAVERSAL остаётся только для containment/symlink/path traversal
- Изменение не ослабляет Windows handling
tests_to_run:
- uv run pytest tests/test_security.py -q
```

#### I12 — Показывать контекст файла при UnicodeDecodeError URL-list

```yaml
id: I12
title: Показывать контекст файла при UnicodeDecodeError URL-list
type: implementation
status: pending
priority: medium
risk: low
depends_on:
- R00
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- OUT-001
source_file:
- .ai/audit/08-cli-observability/findings.md
description: Расширить узкий обработчик Path.read_text внутри cli.batch_download на UnicodeError, не расширяя
  исключения вокруг последующей загрузки.
goals:
- Ошибка декодирования URL-list получает специальный текст
- Код выхода остаётся 1
- Ошибки после этапа чтения не маскируются под проблему файла
files:
- path: src/vkdownloader/cli.py
  mode: change
  targets:
  - type: function
    name: batch_download
  semantic_anchors:
  - Вложенный try/except вокруг `urls_file.read_text()`
changes:
- action: modify_code
  description: Локально обработать UnicodeError вместе с OSError на этапе чтения списка.
acceptance_criteria:
- Битый UTF-8 URL-файл → `Failed to read URL file` + путь, exit 1
- Подменён старый test oracle, ожидавший общую ошибку
- Нет traceback/UnboundLocalError
tests_to_run:
- uv run pytest tests/test_cli.py -q
```

#### I13 — Перенести batch summary и exit mapping на CLI-границу

```yaml
id: I13
title: Перенести batch summary и exit mapping на CLI-границу
type: implementation
status: pending
priority: medium
risk: high
depends_on:
- R05
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
source_file:
- .ai/audit/01-entry-architecture/findings.md
description: 'Единая атомарная миграция сервис/CLI по решению R05: run_batch возвращает структурированную информацию
  без вызовов Typer и выбора процессного кода; cli.batch_download отображает существующий summary и определяет
  0/1/130.'
goals:
- Сервис не пишет в stdout/stderr самостоятельно
- CLI сохраняет наблюдаемое поведение и приоритет cancel над failed
- Нет разрыва между изменённым service contract и CLI потребителем
files:
- path: src/vkdownloader/services/batch_downloader.py
  mode: change
  targets:
  - type: function
    name: run_batch
  - type: function
    name: _run_batch_with_progress
  - type: function
    name: _print_batch_summary
  semantic_anchors:
  - '`run_batch` и `_print_batch_summary` как текущая сервисная граница'
- path: src/vkdownloader/cli.py
  mode: change
  targets:
  - type: function
    name: batch_download
  semantic_anchors:
  - '`batch_download` и `_run_batch_with_signal_handlers`'
- path: src/vkdownloader/models/dtos.py
  mode: change
  targets:
  - type: module
    name: models.dtos
  semantic_anchors:
  - Использовать существующие DTO, если R05 подтвердил подход; не вводить альтернативную параллельную модель
changes:
- action: modify_code
  description: Упаковать результаты/счётчики в сервисный тип; перенос вывода и exit policy в CLI в том же интегрируемом
    изменении. Прямое изменение публичного контракта следует за R05.
acceptance_criteria:
- run_batch не импортирует typer и не принимает решение exit code
- CLI status lines/summary/failed URLs/skipped/peak concurrency совпадают с текущими сценариями
- 0 success; 1 failed; 130 cancelled; reporter stop и cleanup на исключениях
- Изменение согласовано с внешними потребителями или помечено breaking по R05
tests_to_run:
- uv run pytest tests/test_batch_downloader.py tests/test_cli.py -q
```

#### I14 — Сделать минимальный coverage порог блокирующим

```yaml
id: I14
title: Сделать минимальный coverage порог блокирующим
type: implementation
status: pending
priority: high
risk: high
depends_on:
- R06
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- TST-001
source_file:
- .ai/audit/10-test-coverage/findings.md
description: Применить измеренный в R06 числовой порог в существующем job `Coverage report`, без создания второго
  измерителя или неявного снижения при падениях.
goals:
- Coverage regression вызывает non-zero CI status
- Порог не скрывает failure от команды pytest
- Policy изменения порога явна
files:
- path: .github/workflows/packaging-check.yml
  mode: change
  targets:
  - type: workflow_step
    name: Coverage report
  semantic_anchors:
  - Шаг `Coverage report`
changes:
- action: modify_ci
  description: Установить поддерживаемый coverage `fail-under`/эквивалент из R06 и сохранить существующую команду
    измерения.
acceptance_criteria:
- Ниже порога workflow падает; выше или равно — проходит
- Порог одинаково применим к используемой coverage конфигурации
- Значение можно сопоставить с артефактом измерения R06
tests_to_run:
- uv run coverage run -m pytest tests/
- uv run coverage report
```

#### I15 — Сделать сбой pip-audit непроходным для CI

```yaml
id: I15
title: Сделать сбой pip-audit непроходным для CI
type: implementation
status: pending
priority: high
risk: high
depends_on: []
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- DEP-001
source_file:
- .ai/audit/11-supply-chain/findings.md
description: 'Исправить шаг `Advisory scan`: неуспех `uv export` и все ненулевые коды scanner блокируют gate;
  отсутствие данных не должно трактоваться как «проверено и безопасно».'
goals:
- rc 0 разрешает продолжить
- rc 1 и rc > 1 блокируют job
- Не ломать cleanup временного requirements файла и GitHub Actions shell
files:
- path: .github/workflows/packaging-check.yml
  mode: change
  targets:
  - type: workflow_step
    name: Advisory scan
  semantic_anchors:
  - Шаг `Advisory scan` с `set +e`, `rc`, веткой else и `rm -f`
changes:
- action: modify_ci
  description: Развести exit codes и exit status финального shell step, обеспечив fail-closed на ошибках экспорта
    и сканера.
acceptance_criteria:
- Синтетическая имитация scanner rc=2/127 и export error даёт failure
- rc=1 корректно сигнализирует известную уязвимость; rc=0 остаётся green
- Последующая команда cleanup не перетирает ненулевой статус
```

#### I16 — Добавить LICENSE к packaging workflow path filters

```yaml
id: I16
title: Добавить LICENSE к packaging workflow path filters
type: implementation
status: pending
priority: high
risk: medium
depends_on: []
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- DEP-002
source_file:
- .ai/audit/11-supply-chain/findings.md
description: Согласовать фильтр триггеров push/pull_request с `pyproject.toml::license-files`, чтобы правка LICENSE
  не проходила мимо package gate.
goals:
- Изменение LICENSE запускает job на обоих событиях
- Текущие scoped paths не исключены
- Состав wheel/sdist по-прежнему проверяется
files:
- path: .github/workflows/packaging-check.yml
  mode: change
  targets:
  - type: workflow_trigger
    name: push.paths
  - type: workflow_trigger
    name: pull_request.paths
  semantic_anchors:
  - '`on.push.paths`, `on.pull_request.paths`'
- path: pyproject.toml
  mode: read-only
  targets:
  - type: config
    name: project.license-files
  - type: config
    name: tool.hatch.build.targets.sdist
  semantic_anchors:
  - '`project.license-files` и sdist manifest'
changes:
- action: modify_ci
  description: Дополнить оба path filters файлом LICENSE, не добавляя лишние нерелизные пути.
acceptance_criteria:
- PR/commit, содержащий только LICENSE, удовлетворяет фильтру запуска
- Проверки manifest в tests/test_packaging.py проходят
tests_to_run:
- uv run pytest tests/test_packaging.py -q
```

### 6.3. Documentation contracts

#### D01 — Исправить документацию tuple результата extractor

```yaml
id: D01
title: Исправить документацию tuple результата extractor
type: documentation
status: pending
priority: medium
risk: low
depends_on: []
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- QLT-001
source_file:
- .ai/audit/09-code-quality/findings.md
description: 'Синхронизировать публичную API reference с контрактом VKVideoExtractor.extract_streams_with_cookies:
  возвращаются streams, cookie string, raw cookie collection; сама реализация не меняется.'
goals:
- Точная сигнатура и пример распаковки трёх значений
- Описание cookies=None и raw cookies
- Нет ошибочной документации двухэлементного tuple
files:
- path: docs/01-tools/api-reference.md
  mode: change
  targets:
  - type: section
    name: VKVideoExtractor.extract_streams_with_cookies
  semantic_anchors:
  - Раздел `extract_streams_with_cookies` — подпись, Returns, Example
- path: src/vkdownloader/services/extractor.py
  mode: read-only
  targets:
  - type: method
    name: VKVideoExtractor.extract_streams_with_cookies
  semantic_anchors:
  - Публичная сигнатура — источник истины
changes:
- action: update_docs
  description: Исправить тип результата, распаковку и смысл третьего результата без печати реальных cookies.
acceptance_criteria:
- Документация и код согласованы
- Existing extractor tests подтверждают три возвращаемых элемента
tests_to_run:
- uv run pytest tests/test_extractor.py -q
```

#### D02 — Восстановить относительные ссылки на limitations guide

```yaml
id: D02
title: Восстановить относительные ссылки на limitations guide
type: documentation
status: pending
priority: low
risk: low
depends_on: []
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- QLT-002
source_file:
- .ai/audit/09-code-quality/findings.md
description: Исправить обе ссылки на руководство в overview, не меняя структуру каталога или саму страницу ограничений.
goals:
- Обе ссылки ведут из docs/01-tools в docs/11-guides
- Анкоры в пределах документа остаются действительными
files:
- path: docs/01-tools/vkdownloader-overview.md
  mode: change
  targets:
  - type: section
    name: Subprocess process boundary
  - type: section
    name: Secret-safe cookie passing
  semantic_anchors:
  - Ссылки на vkdownloader-limitations.md
- path: docs/11-guides/vkdownloader-limitations.md
  mode: read-only
  targets:
  - type: document
    name: vkdownloader-limitations
  semantic_anchors:
  - Целевой файл и anchors
changes:
- action: update_docs
  description: Исправить пути относительно каталога обзорного документа.
acceptance_criteria:
- Обе ссылки успешно разрешаются обычным link-check
- Текст и существующие навигационные анкоры не потеряны
```

#### D03 — Зафиксировать семантику нулевых значений ротации

```yaml
id: D03
title: Зафиксировать семантику нулевых значений ротации
type: documentation
status: pending
priority: medium
risk: low
depends_on:
- I10
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- CFG-002
source_file:
- .ai/audit/02-config/findings.md
description: Пояснить оператору действующие значения 0 и заданные нижние границы параметров rotation после I10,
  без переписывания unrelated конфигурации.
goals:
- Явный смысл нулевых значений и defaults
- Понятная ошибка при отрицательном лимите
files:
- path: docs/11-guides/configuration.md
  mode: change
  targets:
  - type: section
    name: Logging settings
  semantic_anchors:
  - Строки `log_max_bytes`, `log_backup_count` в таблице параметров
- path: .env.example
  mode: change
  targets:
  - type: config
    name: VKDOWNLOADER_LOG_MAX_BYTES
  - type: config
    name: VKDOWNLOADER_LOG_BACKUP_COUNT
  semantic_anchors:
  - Комментарии к VKDOWNLOADER_LOG_MAX_BYTES/VKDOWNLOADER_LOG_BACKUP_COUNT, если присутствуют
changes:
- action: update_docs
  description: Согласовать описание значений 0 и отрицательных ограничений с фактическим Settings и RotatingFileHandler
    контрактом.
acceptance_criteria:
- Операционная справка не обещает ротацию при нуле без доказательств
- Примеры соответствуют accepted model values
```

### 6.4. Dedicated regression/integration tests

#### T01 — Проверить FFmpeg transport argv и реальный HLS lifecycle

```yaml
id: T01
title: Проверить FFmpeg transport argv и реальный HLS lifecycle
type: test
status: pending
priority: high
risk: high
depends_on:
- I01
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-001
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Заменить test oracle, сейчас явно допускающий signed URL/cookies в ffmpeg argv. Протестировать выбор
  авторизованного плейлиста с синтетическими маркерами через реально выбранный stdin/file/proxy контракт R01.
goals:
- Зафиксировать отсутствие синтетических cookie/token в argv
- Проверить создание результата, остановку subprocess и отсутствие остаточных secret-bearing артефактов
- Сохранить staged-файлы при download failure
files:
- path: tests/test_ffmpeg_transport.py
  mode: change
  targets:
  - type: function
    name: test_ffmpeg_transport_no_secrets_in_argv
  - type: module
    name: tests.test_ffmpeg_transport
  semantic_anchors:
  - '`test_ffmpeg_transport_no_secrets_in_argv` и соседние subprocess tests'
changes:
- action: add_tests
  description: Обновить mock argv assertions на более сильный запрет любых маркеров; добавить контролируемый интеграционный
    HLS сценарий без реальных учётных данных.
acceptance_criteria:
- argv не содержит ни один синтетический секрет в любом элементе
- Тест ловит возврат старой `-headers Cookie` или `-i signed URL` схемы
- Success/failure/cancel освобождают ресурсы
tests_to_run:
- uv run pytest tests/test_ffmpeg_transport.py -q
```

#### T02 — Проверить yt-dlp URL channel при cookies и resume

```yaml
id: T02
title: Проверить yt-dlp URL channel при cookies и resume
type: test
status: pending
priority: high
risk: high
depends_on:
- I02
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-002
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Протестировать выбранный R02 input transport вместе с существующим stdin cookie контуром, выходными
  файлами и cancel/reap. Старые проверки только cookie path недостаточны.
goals:
- Синтетический query token отсутствует в argv
- Нет конкуренции cookie и URL за один stdin
- После ошибки и cancellation временные объекты удалены/сохранены по существующей политике
files:
- path: tests/test_ytdlp_downloader.py
  mode: change
  targets:
  - type: module
    name: tests.test_ytdlp_downloader
  semantic_anchors:
  - Тесты построения yt-dlp CLI и fake-subprocess boundary
- path: tests/test_ffmpeg_utils.py
  mode: read-only
  targets:
  - type: module
    name: tests.test_ffmpeg_utils
  semantic_anchors:
  - Имеющиеся helper-тесты child boundary, если задействована общая утилита
changes:
- action: add_tests
  description: Добавить fake child, фиксирующий argv/stdin и результат; проверить cookies/no-cookies и resume/failure
    по поддерживаемому yt-dlp интерфейсу.
acceptance_criteria:
- Возврат old positional m3u8_url делает тест красным
- Не появляется утечка из логов и temp
- Функциональное скачивание тестовой HLS-манифеста подтверждено на совместимой версии yt-dlp
tests_to_run:
- uv run pytest tests/test_ytdlp_downloader.py -q
```

#### T03 — Проверить redaction cookie headers во всех logging sinks

```yaml
id: T03
title: Проверить redaction cookie headers во всех logging sinks
type: test
status: pending
priority: high
risk: medium
depends_on:
- I03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-003
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Синтетический корпус cookie/raw pair/mixed URL/partial log messages, передаваемый через sanitize_text_for_log,
  sanitize_exception и центральный redaction processor.
goals:
- Редакция Header, Set-Cookie, независимых cookie-пар
- Idempotence и сохранение нейтрального контекста
- Проверка сообщения дочернего процесса/исключения, не только чистой функции
files:
- path: tests/test_url_sanitizer.py
  mode: change
  targets:
  - type: module
    name: tests.test_url_sanitizer
  semantic_anchors:
  - '`sanitize_text_for_log` и `redact_log_event` тестовые группы'
- path: tests/test_diagnostics.py
  mode: change
  targets:
  - type: module
    name: tests.test_diagnostics
  semantic_anchors:
  - Существующий диагностический sink, если необходимо прогнать сквозной сценарий
changes:
- action: add_tests
  description: Ввести таблицу синтетических маркеров и real-chain тест logging pipeline; ни один токен не должен
    появиться в выходе.
acceptance_criteria:
- Все синтетические токены скрыты в строке, записи события и исключении
- Обычные URL host и diagnostic flags сохранены
- Существующие тесты URL и cookie artifacts не регрессировали
tests_to_run:
- uv run pytest tests/test_url_sanitizer.py tests/test_diagnostics.py -q
```

#### T04 — Регрессии выбора HLS hosts и no-match behavior

```yaml
id: T04
title: Регрессии выбора HLS hosts и no-match behavior
type: test
status: pending
priority: high
risk: high
depends_on:
- I04
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-001
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Заменить ожидание старого unsafe fallback и прогнать hostname matrix против NetworkMonitor.select,
  включая localhost, IP, malformed, VK allowlisted и mixed entries.
goals:
- Foreign only не возвращает ни одного download URL
- При смешанном наборе сохраняются только trusted
- HLS ranking и diagnostics работают после отключения suspension
files:
- path: tests/test_browser_infrastructure.py
  mode: change
  targets:
  - type: function
    name: test_select_suspends_host_filter_when_all_non_vk
  - type: function
    name: test_select_filters_non_vk_hosts
  semantic_anchors:
  - '`test_select_suspends_host_filter_when_all_non_vk`, `test_select_filters_non_vk_hosts`, select ordering'
changes:
- action: add_tests
  description: Переписать оракул unsafe fallback; добавить security host cases и stable-rank cases без внешнего
    VK.
acceptance_criteria:
- Старый unconstrained fallback вызывает failure
- Нет обращения к 127.0.0.1/внутренним host из результата select
- Trusted manifests не теряются
tests_to_run:
- uv run pytest tests/test_browser_infrastructure.py -q
```

#### T05 — Регрессии Retry-After и cancel без ранних повторов

```yaml
id: T05
title: Регрессии Retry-After и cancel без ранних повторов
type: test
status: pending
priority: high
risk: medium
depends_on:
- I05
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-002
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Убрать тест, ожидающий обрезание серверного floor до 30 секунд; проверить задержку 120 секунд в не-блокирующем
  тестовом времени и интеграцию с retry count/cancellation.
goals:
- Retry-After 120 не сворачивается в 30
- Обычный jitter cap остаётся действующим
- cancel мгновенно прерывает ожидание; нет лишнего network attempt
files:
- path: tests/test_downloader_throttle.py
  mode: change
  targets:
  - type: function
    name: test_retry_after_ceiling_applies_after_max
  semantic_anchors:
  - '`test_retry_after_ceiling_applies_after_max` и ветки retry'
- path: tests/integration/test_hls_fixture.py
  mode: change
  targets:
  - type: function
    name: test_fault_429_retry_after
  semantic_anchors:
  - '`test_fault_429_retry_after`'
changes:
- action: add_tests
  description: Перестроить устаревший threshold oracle; использовать управляемые часы/патчи ожидания вместо настоящего
    sleep на 120s.
acceptance_criteria:
- 120s соблюдаются как floor или retry не выполняется по утверждённой политике
- Нет тестов с длительным реальным ожиданием
- Параллельное отмена/retry работает
tests_to_run:
- uv run pytest tests/test_downloader_throttle.py tests/integration/test_hls_fixture.py -q
```

#### T06 — Проверить отсутствие unbounded response materialization

```yaml
id: T06
title: Проверить отсутствие unbounded response materialization
type: test
status: pending
priority: high
risk: high
depends_on:
- I06
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-003
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Отследить обращения к Response.body на oversized/unknown-length chunked response и проверить нормальное
  извлечение из маленьких известных тел. Тест должен падать при возврате post-read cap.
goals:
- Unknown size без bounded API не приводит к full body read
- Known large response skip происходит до body()
- Known small HLS/JSON продолжает обрабатываться
files:
- path: tests/test_browser_infrastructure.py
  mode: change
  targets:
  - type: function
    name: test_network_monitor_skips_oversized_body_without_content_length
  semantic_anchors:
  - '`test_network_monitor_skips_oversized_body_without_content_length` и response interceptor tests'
changes:
- action: add_tests
  description: Отслеживать `Response.body` call count на неизвестной длине, корректной/невалидной metadata и малых
    известных ответах; сохранить runtime bounded.
acceptance_criteria:
- Неравномерный крупный response не приводит к materialization
- Существующая семантика URL-only capture сохраняется
- Тест отличает bound-before-read от truncate-after-read
tests_to_run:
- uv run pytest tests/test_browser_infrastructure.py -q
```

#### T07 — Проверить POSIX Runner handler restoration и Windows fallback

```yaml
id: T07
title: Проверить POSIX Runner handler restoration и Windows fallback
type: test
status: pending
priority: medium
risk: high
depends_on:
- I07
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- CON-001
source_file:
- .ai/audit/04-concurrency-cancellation/findings.md
description: Добавить проверку именно внутри активного asyncio.Runner после cleanup, с идентичностью прежнего
  обработчика, не только после выхода из asyncio.run. Оставить проверки второго прерывания и Windows fallback.
goals:
- Возвращён предшествующий Runner SIGINT callback
- Третье лицо/повторная установка не перетираются
- Windows fallback и 2nd interrupt не регрессируют
files:
- path: tests/test_hls_downloader.py
  mode: change
  targets:
  - type: module
    name: tests.test_hls_downloader
  semantic_anchors:
  - Signal handler тесты setup/cleanup и repeated asyncio.run
- path: tests/test_cli.py
  mode: read-only
  targets:
  - type: module
    name: tests.test_cli
  semantic_anchors:
  - Существующие SIGINT CLI интеграционные тесты
changes:
- action: add_tests
  description: Ввести POSIX-only test на восстановление identity до выхода из loop; на Windows исполнять соответствующие
    fallback проверки в CI matrix.
acceptance_criteria:
- Наблюдается pre-install handler после cleanup внутри живого Runner
- Нет зависшего shutdown_event и потери cancel semantics
- Синтетические сигналы не нарушают работающий тестовый процесс
tests_to_run:
- uv run pytest tests/test_hls_downloader.py tests/test_cli.py -q
```

#### T08 — Проверить batch service без console side effects и CLI exit contract

```yaml
id: T08
title: Проверить batch service без console side effects и CLI exit contract
type: test
status: pending
priority: medium
risk: high
depends_on:
- I13
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
source_file:
- .ai/audit/01-entry-architecture/findings.md
description: Проверить разделение ответственностей на реальном пути batch_download/run_batch со stub downloader
  и установленным reporter; заменить тесты, которые напрямую вызывают сервисный `_print_batch_summary` и ожидают
  exit int.
goals:
- Сервис выполняется с spy stdout/stderr без прямой печати
- CLI печатает прежний summary и status lines
- При успехе, ошибке, cancel коды остаются 0/1/130
files:
- path: tests/test_batch_downloader.py
  mode: change
  targets:
  - type: module
    name: tests.test_batch_downloader
  semantic_anchors:
  - '`test_print_batch_summary_*` и `run_batch` returncode tests'
- path: tests/test_cli.py
  mode: change
  targets:
  - type: function
    name: test_batch_all_success_exits_zero
  - type: function
    name: test_batch_cancelled_produces_cancelled_status
  semantic_anchors:
  - Batch summary/exit/cancel/reporting интеграция
changes:
- action: add_tests
  description: Перенастроить сервисные оракулы на структуру результатов и отсутствующий terminal I/O; расширить
    CLI test на cancel+failed priority и skipped counts.
acceptance_criteria:
- Сервис не импортирует Typer и не порождает пользовательские строки
- CLI поведение не теряет totals, duplicates, failed reasons
- Не нарушается путь отмены с сохранением частичных артефактов
tests_to_run:
- uv run pytest tests/test_batch_downloader.py tests/test_cli.py -q
```

### 6.5. Multi-stage verification and release gates

#### V01 — Security gate: argv, cookies и диагностические sinks

```yaml
id: V01
title: 'Security gate: argv, cookies и диагностические sinks'
type: verification
status: pending
priority: high
risk: high
depends_on:
- T01
- T02
- T03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- SEC-001
- SEC-002
- SEC-003
source_file:
- .ai/audit/06-credentials-secrets/findings.md
description: Проверить совместное поведение двух subprocess transports и центральной redaction. При невозможности
  исключить секрет из argv нельзя объявлять исправление закрытым только по результатам log sanitizer.
goals:
- Нет чувствительных значений в argv обоих процессов
- Обе авторизованные HLS траектории остаются рабочими
- Нет секретов в stderr/логах и потерянных ресурсах
files:
- path: src/vkdownloader/services/ffmpeg_transport.py
  mode: read-only
  targets:
  - type: method
    name: FfmpegTransport.download
  semantic_anchors:
  - FFmpeg процессная граница
- path: src/vkdownloader/services/ytdlp_downloader.py
  mode: read-only
  targets:
  - type: function
    name: _download_with_ytdlp
  semantic_anchors:
  - yt-dlp процессная граница
- path: src/vkdownloader/utils/url_sanitizer.py
  mode: read-only
  targets:
  - type: function
    name: sanitize_text_for_log
  semantic_anchors:
  - Центральный sanitizer
changes:
- action: verify
  description: На локальных synthetic HLS fixtures проверить argv ребёнка, cookie scope, resume/cancel, завершение
    и очистку, затем запустить узкие tests и валидацию без реальных credentials.
acceptance_criteria:
- Нет SECRET query/cookie в argv, stdout, stderr, диагностике
- HLS success/failure/cancel проходят без потери staged/partial bytes
- Операционная совместимость Windows/Linux задокументирована результатами, не предположениями
tests_to_run:
- uv run pytest tests/test_ffmpeg_transport.py tests/test_ytdlp_downloader.py tests/test_url_sanitizer.py tests/test_diagnostics.py
  -q
verifies:
- I01
- I02
- I03
- T01
- T02
- T03
verification_steps:
- Тестовые процессы с синтетическими cookie и signed URL; просмотр argv/process boundaries
- Smoke FFmpeg/yt-dlp на локальном HLS server, отмена и cleanup
- Проверка журналов и временных файлов на маркеры
pass_criteria:
- 0 утечек
- Функциональный локальный HLS сценарий зелёный
- Артефакты preserved/cleaned по контракту
failure_action: Вернуть I01/I02/I03 и соответствующий T на доработку; выпуск запрещён.
```

#### V02 — Network gate: allowed hosts, backoff, bounded responses

```yaml
id: V02
title: 'Network gate: allowed hosts, backoff, bounded responses'
type: verification
status: pending
priority: high
risk: high
depends_on:
- T04
- T05
- T06
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- NET-001
- NET-002
- NET-003
source_file:
- .ai/audit/03-network-resilience/findings.md
description: Единый контроль сетевой политики после трёх изолированных исправлений. Исключить unsafe fallback,
  ранний retry и загрузку больших неизвестных тел в память.
goals:
- Нельзя выбрать untrusted/loopback URL
- Соблюдаются Retry-After и shutdown
- Response.body не вызывается для потенциально unbounded replies
files:
- path: src/vkdownloader/infrastructure/network_monitor.py
  mode: read-only
  targets:
  - type: method
    name: NetworkMonitor.select
  - type: method
    name: NetworkMonitor._intercept_response
  semantic_anchors:
  - '`select`; `_intercept_response`'
- path: src/vkdownloader/services/retry_policies.py
  mode: read-only
  targets:
  - type: function
    name: _compute_backoff_delay
  - type: function
    name: _wait_with_shutdown
  semantic_anchors:
  - '`_compute_backoff_delay` и shutdown wait'
- path: tests/integration/fixtures/hls_server.py
  mode: read-only
  targets:
  - type: module
    name: integration.fixtures.hls_server
  semantic_anchors:
  - HLS HTTP test fixture
changes:
- action: verify
  description: Воспроизвести allowlist/no-match, 429/Retry-After=120 и oversized chunked варианты с локальным
    HLS fixture, включая smoke trusted flow.
acceptance_criteria:
- Нет SSRF-подобного направления на loopback через select
- Серверный Retry-After не проигнорирован
- Memory bound удовлетворяется ещё до body()
- При этом разрешённый HLS скачивается
tests_to_run:
- uv run pytest tests/test_browser_infrastructure.py tests/test_downloader_throttle.py tests/integration/test_hls_fixture.py
  -q
verifies:
- I04
- I05
- I06
- T04
- T05
- T06
verification_steps:
- Hostname matrix и URL selection boundary
- Фиктивные часы и HTTP 429/5xx fixture
- Mock Response.body and bounded parse cases
pass_criteria:
- No foreign URL emitted
- No early retry
- No unbounded read
failure_action: Вернуть соответствующую I04/I05/I06 + T04/T05/T06; не пропускать сетевой gate.
```

#### V03 — Application gate: CLI, signals, config, files и docs

```yaml
id: V03
title: 'Application gate: CLI, signals, config, files и docs'
type: verification
status: pending
priority: high
risk: high
depends_on:
- I07
- I08
- I09
- I10
- I11
- I12
- T07
- T08
- D01
- D02
- D03
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
- CFG-001
- CFG-002
- CON-001
- PRC-001
- ART-001
- OUT-001
- QLT-001
- QLT-002
source_file:
- .ai/audit/01-entry-architecture/findings.md
- .ai/audit/02-config/findings.md
- .ai/audit/04-concurrency-cancellation/findings.md
- .ai/audit/05-subprocess-browser/findings.md
- .ai/audit/07-filesystem-artifacts/findings.md
- .ai/audit/08-cli-observability/findings.md
- .ai/audit/09-code-quality/findings.md
description: Проверить пользовательскую семантику после небольших изменений и структурной границы service/CLI,
  не смешивая их в реализацию одного общего патча.
goals:
- Проверить статусы, вывод, cancel и ошибки конфигурации
- Сохранить paths и ffmpeg backend selector
- Проверить документы и навигацию
files:
- path: src/vkdownloader/cli.py
  mode: read-only
  targets:
  - type: function
    name: batch_download
  - type: function
    name: download
  semantic_anchors:
  - '`batch_download` и `download`'
- path: src/vkdownloader/services/batch_downloader.py
  mode: read-only
  targets:
  - type: function
    name: run_batch
  semantic_anchors:
  - '`run_batch` contract'
- path: src/vkdownloader/services/signal_handlers.py
  mode: read-only
  targets:
  - type: function
    name: cleanup_signal_handlers
  semantic_anchors:
  - '`cleanup_signal_handlers`'
- path: docs/01-tools/api-reference.md
  mode: read-only
  targets:
  - type: section
    name: VKVideoExtractor.extract_streams_with_cookies
  semantic_anchors:
  - Extractor public method reference
changes:
- action: verify
  description: Запустить targeted tests/CLI help and batch smoke под Linux и Windows, проверить нетривиальные
    сценарии ошибок и Markdown local links; убедиться, что symlink defense не ослаблена.
acceptance_criteria:
- CLI batch exit 0/1/130 и summary совпадают с контрактом
- POSIX Runner и Windows fallback сохраняют signal semantics
- Ошибка длины пути не классифицируется traversal
- Pydantic/UTF-8 errors корректны, док-ссылки рабочие
tests_to_run:
- uv run pytest tests/test_cli.py tests/test_batch_downloader.py tests/test_hls_downloader.py tests/test_config.py
  tests/test_security.py tests/test_extractor.py -q
verifies:
- I07
- I08
- I09
- I10
- I11
- I12
- I13
- D01
- D02
- D03
- T07
- T08
verification_steps:
- Targeted pytest + typed CLI help/batch smoke
- POSIX Runner identity и Windows CI fallback
- Documentation local-link integrity и schema error codes
pass_criteria:
- User-visible outcomes preserved
- Signal/path protections preserved
- No broken links/signature examples
failure_action: Исправить только провалившийся атомарный task, затем повторить V03.
```

#### V04 — CI gate: coverage, advisory scan, packaging triggers

```yaml
id: V04
title: 'CI gate: coverage, advisory scan, packaging triggers'
type: verification
status: pending
priority: high
risk: high
depends_on:
- I14
- I15
- I16
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- TST-001
- DEP-001
- DEP-002
source_file:
- .ai/audit/10-test-coverage/findings.md
- .ai/audit/11-supply-chain/findings.md
description: Проверить под реальным GitHub Actions shell/Linux+Windows выбранный coverage threshold, fail-closed
  поведение scanner и запуск workflow по LICENSE. Нельзя считать статическое чтение YAML эквивалентом CI.
goals:
- Coverage below threshold делает pipeline красным
- pip-audit/uv export errors блокируют package artifact publication
- LICENSE-only PR запускает packaging-check
files:
- path: .github/workflows/packaging-check.yml
  mode: read-only
  targets:
  - type: workflow_step
    name: Coverage report
  - type: workflow_step
    name: Advisory scan
  - type: workflow_trigger
    name: pull_request.paths
  semantic_anchors:
  - '`Coverage report`, `Advisory scan`, `on.push.paths`, `on.pull_request.paths`'
- path: pyproject.toml
  mode: read-only
  targets:
  - type: config
    name: project.license-files
  - type: config
    name: tool.hatch.build.targets.sdist
  semantic_anchors:
  - '`license-files` и `sdist include`'
changes:
- action: verify
  description: Выполнить CI-matrix, имитировать rc=0/1/2 scanner и failure uv export, induced below-threshold
    coverage, отдельный change LICENSE и проверить содержимое wheel/sdist.
acceptance_criteria:
- Все nonzero scanner и export → failed CI step
- Coverage regression → failed CI step
- LICENSE-only change запускает packaging-check и artifact build
- На Linux+Windows успех реального job зафиксирован
tests_to_run:
- uv run coverage run -m pytest tests/
- uv run coverage report
- uv build --out-dir dist/
- uv run pytest tests/test_packaging.py -q
verifies:
- I14
- I15
- I16
verification_steps:
- Linux/Windows GitHub Actions job
- Injected scanner failure / export failure and below-threshold coverage
- LICENSE-only trigger + wheel/sdist manifest inspection
pass_criteria:
- No silent bypass
- Only approved coverage threshold applies
- LICENSE change is gated
failure_action: Вернуть только упавшие I14/I15/I16, job gate остаётся красным.
```

#### V05 — Финальная интеграционная проверка и решение о релизе

```yaml
id: V05
title: Финальная интеграционная проверка и решение о релизе
type: verification
status: pending
priority: high
risk: high
depends_on:
- V01
- V02
- V03
- V04
source_reference: vkdownloader_audit_findings_01-11(1).zip
source_section:
- ENT-001
- CFG-001
- CFG-002
- NET-001
- NET-002
- NET-003
- CON-001
- PRC-001
- SEC-001
- SEC-002
- SEC-003
- ART-001
- OUT-001
- QLT-001
- QLT-002
- TST-001
- DEP-001
- DEP-002
source_file:
- .ai/audit/01-entry-architecture/findings.md
- .ai/audit/02-config/findings.md
- .ai/audit/03-network-resilience/findings.md
- .ai/audit/04-concurrency-cancellation/findings.md
- .ai/audit/05-subprocess-browser/findings.md
- .ai/audit/06-credentials-secrets/findings.md
- .ai/audit/07-filesystem-artifacts/findings.md
- .ai/audit/08-cli-observability/findings.md
- .ai/audit/09-code-quality/findings.md
- .ai/audit/10-test-coverage/findings.md
- .ai/audit/11-supply-chain/findings.md
description: Заключительный gate зависит от четырёх самостоятельных verification-потоков. Не превращать его в
  новую реализацию; любые найденные дефекты возвращать к конкретным I/T задачам. Внешнее авторизованное VK-тестирование
  — отдельная контролируемая процедура, без реальных секретов в отчёте.
goals:
- Зафиксировать полную матрицу тестов и типовую/линтер-проверку
- Проверить изоляцию процессов и сетевое поведение на конечном workflow
- Зафиксировать остаточные риски, инструкции отката и решение release/hold
files:
- path: pyproject.toml
  mode: read-only
  targets:
  - type: config
    name: project.requires-python
  - type: config
    name: build-system
  semantic_anchors:
  - Python 3.14 и build backend
- path: .github/workflows/packaging-check.yml
  mode: read-only
  targets:
  - type: workflow
    name: Packaging Check
  semantic_anchors:
  - Полная CI матрица
- path: src/vkdownloader/cli.py
  mode: read-only
  targets:
  - type: function
    name: cli
  - type: function
    name: batch_download
  semantic_anchors:
  - CLI smoke
- path: docs/11-guides/vkdownloader-limitations.md
  mode: read-only
  targets:
  - type: document
    name: vkdownloader-limitations
  semantic_anchors:
  - Документирование утверждённых остаточных рисков, если они существуют
changes:
- action: verify
  description: Выполнить весь suite и build с зафиксированными бинарными версиями; выполнить Windows/Linux E2E
    на синтетическом HLS, два backend paths, interrupt/resume, then sign off. Риски без разрешения блокируют выпуск.
acceptance_criteria:
- V01, V02, V03, V04 успешно закрыты
- Полные pytest/ruff/mypy/build/packaging gates зелёные на поддерживаемых платформах
- Не осталось незакрытой HIGH находки без согласованного решения и зафиксированного риска
- Rollback не удаляет существующие промежуточные файлы и не раскрывает токены
tests_to_run:
- uv run pytest tests/ tests/integration/ -rs
- uv run ruff check src tests
- uv run ruff format --check src tests
- uv run mypy src
- uv build --out-dir dist/
- uv run pytest tests/test_packaging.py -q
verifies:
- V01
- V02
- V03
- V04
verification_steps:
- Full reproducible CI and packaging
- Local HLS smoke incl 429/403/5xx, cancellation and resume
- Security artifacts review, documentation and rollback approval
pass_criteria:
- All gates accepted
- No unresolved release-blocking finding
- Evidence and backout instructions recorded
failure_action: Вернуть проваленный task к исполнителю; release = HOLD.
```

## 7. Проверки качества графа и правила изменения плана

1. **Точки остановки:** R00 без Python 3.14 не даёт права объявить ни одну тестовую задачу проверенной. R01/R02/R03/R04/R05 обязаны завершиться документированным решением; если канал безопасной передачи или поведение trusted host остаётся неизвестным, upstream `I` и downstream `V` — blocked. Невалидированные решения не реализуются по умолчанию.
2. **Проверки изменений:** I/D проходят review независимо. Для небольших CFG-001/CFG-002, PRC-001, ART-001, OUT-001, QLT-001/QLT-002, DEP-002 целевой тест или doc/link-check выполняется **внутри** задачи. Для сложных решений — выделены T01–T08. Для CI gates — обязательна V04 с реальными ветками исполнения сканера и coverage.
3. **Ответственность за regression fixtures:** обновлять ожидание только вместе с соответствующим исправлением. Недопустимо удалять тест, который доказывает защиту, чтобы получить green. Перед V01/V02/V03 установить границы заменённых оракулов из раздела 3.
4. **Безопасность:** никаких production credentials, cookies или signed media URLs в артефактах проверки, process argv, отчетах, скриншотах и диагностике. Для smoke использовать синтетические токены и локальный HLS fixture. Результаты реального VK-теста фиксировать только в обезличенной форме.
5. **Release/HOLD:** выпуск разрешён только при `V05=PASS`. При провале — возврат к конкретному `I`/`T` task, без массового rewrite; не откатывать пользовательские `.part`/fragments/workspaces. Изменения network policy/FFmpeg/yt-dlp допускают targeted rollback по одному backend или module после повторной проверки security gate. Не считать возврат к небезопасной argv-схеме безопасным rollback.
6. **Журнал решений:** зафиксировать в PR metadata или файле решения R01–R06 с outcome/owner/evidence. Пользовательская документация обновляется только для реальных контрактов (D01–D03) и утверждённых остатков риска, а не для каждого внутреннего переименования.

**Контроль исполнения:** `pending` в каждой задаче означает, что ни один фикс, тест или gate в настоящем плане не запущен. Имена `I01`–`I16`, `D01`–`D03`, `R00`–`R06`, `T01`–`T08`, `V01`–`V05` являются стабильными ID для задачи/PR/проверки.
