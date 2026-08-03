# Part 4 — Cross-Cutting Risks: Extension Lifecycle, Global Config, Observability, Error/Retry, Testing, Milestones

## 1. CROSS-CUTTING RISK REGISTER

| ID | Risk | Likelihood | Impact | Detection | Mitigation | Owner |
|----|------|------------|--------|-----------|------------|-------|
| **R-A1** | Activation race: Kilo backend not ready when extension activates | HIGH | HIGH - Missed initial approvals | SSE connection timeout on activate() | Poll config every 500ms until port discovered; defer subscription until Subscribed state; persist last known config path | Extension orchestrator |
| **R-A2** | Uncaught exception crashes extension host, killing all modules | MEDIUM | CRITICAL - No approvals delivered until manual restart | Unhandled rejection in VS Code logs; extension fails to respond | Wrap all async boundaries in try/catch; setUncaughtExceptionHandler; isolate module failures with circuit breaker pattern | Shared/errors.ts + all modules |
| **R-A3** | Status-bar flicker/spam during reconnect/recovery loops | MEDIUM | MEDIUM - UX degradation, confusion | Visual inspection; user complaint | Debounce status updates (max 1 per 2s); aggregate into single indicator; use distinct colors per state | Status bar wrapper |
| **R-A4** | Config hot-reload desync (settings change at runtime) | MEDIUM | HIGH - Inconsistent behavior, security gap | Test config change during active flow; monitor behavior | ExtensionSettings watch fires reload of dependent services; polling interval updates live; require restart for token changes | ConfigManager -> orchestrator |
| **R-A5** | Secret/credential leakage via logs/telemetry | LOW | CRITICAL - Bot token + HMAC secret exposed | Code review + log scanning for tokens | Structured logger NEVER logs secrets; redact() helper for all outputs; grep tests for token|secret|password in log assertions | Shared/logger.ts |
| **R-A6** | Provider switch mid-flight loses pending approvals | LOW | HIGH - Orphaned approvals, no way to respond | Test provider swap during active approvals | Drain old provider on switch; re-send pending approvals via new provider; maintain handle->messageRef map for edits | Provider factory + ApprovalStateManager |
| **R-A7** | Multiple VS Code windows sharing one bot token | MEDIUM | HIGH - Duplicate notifications, confused dedupe | Multiple approvals on same command; callback_query_id confusion | Single-window activation (activationEvents filter); SecretStorage scoped per window; dedupe by composite key (windowId+requestId) | SecurityModule + extension.ts |
| **R-A8** | Extension auto-update breaking SDK compatibility | MEDIUM | HIGH - Runtime crashes; missing API | Post-update extension fails to connect | Runtime version check in activate(); fail closed with clear error; optional SDK update bundled with extension | KiloBackendConnector |
| **R-A9** | Live Kilo backend unavailable in CI (integration tests) | HIGH | MEDIUM - Tests unreliable; skip required | CI failures on missing localhost:4097 | MockKiloClient with scripted SSE events; nock/msw for HTTP endpoints; optional live smoke test behind E2E_TELEGRAM flag | Test doubles |
| **R-A10** | High pending-approval volume exhausts memory or Telegram rate limits | LOW | HIGH - System unusable; crashes | Memory profiling; 429 rate limit errors | Bounded queue (max 1000); LRU eviction; batch notifications for burst; status bar warning on high volume | TelegramProvider + ApprovalStore |
| **R-A11** | Telegram API outage takes whole system down | LOW | HIGH - No approvals; no user feedback | HTTP 500/timeout errors; backoff exhaustion | Queue approvals in memory; after reconnect, flush queue; VS Code native notification as fallback if Telegram unavailable > 5min | TelegramProvider + orchestrator |

## 2. NON-FUNCTIONAL SLOs

| Category | SLO | Rationale |
|----------|-----|-----------|
| **Startup time** | <2s to reach Subscribed state | First approval must dispatch quickly for UX |
| **Memory cap** | <100MB total extension | VS Code extension memory budget |
| **CPU idle** | <1% average when no events | Persistent SSE + polling must not drain battery |
| **Crash resilience** | Module failure does not kill others | Circuit breaker isolation per module |
| **Observability coverage** | All state transitions logged | Diag issues in field deployments |
| **Status bar latency** | State visible within 1s | User feedback loop |

## 3. EDGE CASES

| Scenario | Handling |
|----------|----------|
| VS Code reload mid-approval | globalState restores handles, offset; recovery replays missed events |
| Laptop closed (offline) | Queue approvals; flush on reconnect; TTL expiration clears orphans |
| Kilo process restarts | ConfigManager detects port change; reconnect; recovery fetches pending |
| Telegram outage >5min | In-memory queue; VS Code native fallback; flush on recovery |
| Multiple VS Code windows | Single activation; SecretStorage scoped; dedupe by window key |
| Settings change at runtime | Settings watcher propagates to polling interval, TTL |
| Extension update | Runtime version check; fail closed; persistent state survives |

## 4. OVERALL TESTING STRATEGY

### 4.1 Unit Tests (Per Module)
- **Framework**: vitest + vscode-test for VS Code API mocking
- **Mocks**: FakeConfigReader (implements ConfigProvider), MockKiloClient (scripted SSE), FakeTelegramApiClient (records calls)
- **Coverage**: All functions, error paths, boundary conditions; target 80%+

### 4.2 Integration Tests
- FakeKiloClient: Full sign->send->callback->reply loop without real Kilo
- Reconnection flow: SSE disconnect->reconnect->recovery sequence
- Config hot-reload: Modify server.json during active subscription
- Provider lifecycle: start/stop/idempotency transitions verified

### 4.3 Contract Tests
- FakeProvider: In-memory NotificationProvider implementation
- Shared suite runs against TelegramProvider, FakeProvider, and stubs
- Guarantees any provider implementing NotificationProvider works

### 4.4 Live Smoke Tests (Gated)
- Flag: E2E_TELEGRAM=1 (default off)
- Scope: Real Kilo opencode backend + Telegram bot
- Never in CI: Manual execution only for release validation

### 4.5 Hard-to-Test Concerns & Mitigations

| Concern | Mitigation |
|---------|------------|
| Real Telegram API | FakeTelegramApiClient records method calls; nock/msw archives real responses |
| Real SecretStorage | FakeSecretStore with typed Memento interface; manual keyring integration test |
| SSE timing/reconnect race | Scheduler interface with fake timers; inject delayMs into MockKiloClient |
| Multi-window race | FakeExtensionContext with cloned state; verify dedupe by composite key |
| Clock skew on expiry | Inject now() function; RateLimiter clock also mockable |
| Provider switch atomicity | ProviderFactory + ApprovalStateManager drain + re-send sequence tested |

## 5. RELEASE PHASES (M0-M5)

| Phase | Objective | Delivers | Prerequisite |
|-------|-----------|----------|--------------|
| M0 | Scaffold extension, TS config, logger, errors | Extension manifest, vitest config, shared types | None |
| M1 | Connect + config foundation | ConfigManager, KiloBackendConnector, SSE connection | M0 |
| M2 | Notify capability | TelegramProvider, messageFormatter, polling loop | M1 |
| M3 | Secure approve | SecurityModule, ApprovalStateManager, handle map | M1, M2 |
| M4 | Polish + observability | Status bar, logging, graceful degradation | M3 |
| M5 | Provider abstraction + tests | FakeProvider contract tests, live smoke test | M4 |

## 6. BACKLOG ORDERING

1. Walking skeleton (config->SSE->fake approval)
2. Security contracts (SecretStorage+HMAC) before real Telegram
3. Failure handling before UI polish
4. Observability before scale optimization
5. Interfaces before implementations (DI seams)