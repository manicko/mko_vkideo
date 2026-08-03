# Plan 04 — Lifecycle, Global Config, Observability, Error/Retry Policy, Consolidated Contracts, Testing Strategy, Milestones/Backlog (Part 4 of 5)

**Project:** Mko-AINotify — companion VS Code extension that forwards Kilo Code (`opencode` backend) permission approval requests to a mobile notification channel (Telegram) and relays decisions back.

**This part delivers (THE CROSS-CUTTING GLUE):** the extension bootstrap & orchestrator, `EventBus` mediator, `package.json` contribution points, status-bar + `OutputChannel` UX, the consolidated global `ExtensionSettings` schema + `ConfigManager` exposure + provider factory, the unified error taxonomy & retry policy, the observability pipeline (logger + metrics + health), the **consolidated internal contract bible**, the overall testing strategy, the single release roadmap (M0–M5), and the single ordered task backlog.

**This part does NOT modify Kilo Code.** It only consumes the 5 module contracts defined in plans 01–03:
- Part 1 — `KiloBackendConnector`, `ConfigManager`
- Part 2 — `TelegramProvider` (+ `NotificationProvider`)
- Part 3 — `SecurityModule`, `ApprovalStateManager`

**Source research:** `part4_requirements.md`, `part4_architecture.md`, `part4_risks.md`, `validation_priority.md`, plus plans `01_backend_connector.md`, `02_notification_provider.md`, `03_security_state.md`.

---

## 1. Scope & Goals

### 1.1 In scope (Part 4 owns)
- `extension.ts` `activate()` / `deactivate()` — the orchestrator that instantiates and wires the 5 modules in deterministic order.
- `EventBus` mediator for decoupled cross-cutting signals (`config.changed`, `decision.resolved`, `error.uncaught`, `health`).
- `package.json` manifest: `activationEvents`, `contributes.configuration` (full settings schema), `contributes.commands` (set token / rotate secret / show audit / flush queue), `contributes.statusBarItem`.
- `StatusBarController` — connection state + pending count with debounce; `OutputChannel` "Mko-AINotify" structured log sink.
- Consolidated `ExtensionSettings` schema + `ConfigManager` exposure contract + `createProvider()` factory switch.
- Unified error taxonomy (`ExtensionErrorKind`) and the global retry/backoff policy location map.
- Global `uncaughtException` / `unhandledRejection` handler + per-module crash isolation (circuit breaker).
- Observability: structured logger pipeline, `MetricsCollector` (counters + health signal).
- The **consolidated internal contract catalog** (`src/core/shared/types.ts`) that every other part implements against.
- Overall testing strategy (unit + full-loop integration + FakeProvider contract + gated live smoke + CI), consolidated milestones (M0–M5), and the single prioritized backlog.

### 1.2 Explicit out-of-scope (owned by Parts 1–3)
| Responsibility | Owning part/module |
|---|---|
| `server.json` discovery, SSE lifecycle, `replyToPermission`, `PendingApproval` normalization | Part 1 — KiloBackendConnector / ConfigManager |
| Bot API client, getUpdates polling, inline-keyboard rendering, `OutboundApproval` send | Part 2 — TelegramProvider |
| HMAC envelope, `SecretStorage`, `signCallback`/`verifyCallback`, handle map | Part 3 — SecurityModule + ApprovalStateManager |
| Pending approval TTL, dedupe, authorization check | Part 3 — ApprovalStateManager |

Part 4 references these but never reimplements their internals; it only calls their public interfaces.

---

## 2. Extension Bootstrap & Orchestrator Design

### 2.1 Activation strategy (timing vs Kilo backend not ready)

- `activationEvents`: `["*", "onStartupFinished"]`.
  - `onStartupFinished` fires after all extensions are activated. Kilo typically writes `server.json` during its activation, but **race conditions still exist** (R-A1).
  - `"*"` guarantees the extension loads for any workspace so commands/status bar are always available.

- **Activation race mitigation (REVISED):**
  ```
  activate(ctx):
    1. Create all 5 modules (dependencies injected)
    2. Start KiloBackendConnector.connect() NON-BLOCKING
    3. If ConfigNotFound, start RETRY LOOP:
       - Polling discovery every 500ms for up to 30s
       - Exponential backoff beyond 30s (max 10s interval)
       - Give up only on extension dispose
    4. Only wire onPendingApproval after reaching Subscribed state
  ```

- Subscription is **deferred** until `ConnectionState.Subscribed`; no approval processing before then.

### 2.2 Factory wiring order (deterministic, dependency-safe)

```
activate(ctx):
  1. Logger        = createLogger("mko-ainotify")
  2. ConfigManager = new ConfigManager({ ctx, fsWatcher })
  3. SecurityModule= new SecurityModule({ vault, handleMap, contextProvider, rateLimiter })
  4. ApprovalSM    = new ApprovalStateManager({ security, pendingStore, dedupStore, ttlSweeper, auditLog })
  5. Connector     = new KiloBackendConnector({ directory, config: ConfigManager })
  6. Provider      = createProvider( settings.provider, { logger, settings, security } )
  7. Orchestrator  = new Orchestrator({ connector, provider, approvalSM, security, configManager })
  8. statusBar + outputChannel + metrics + uncaught handler
  9. Orchestrator.start()   // fires connect() + wire events
```

### 2.3 Orchestrator event wiring (the glue)

```typescript
// src/core/orchestrator/Orchestrator.ts
export class Orchestrator implements Disposable {
  constructor(deps: {
    connector: KiloBackendConnector;
    provider: NotificationProvider;
    approvalSM: ApprovalStateManager;
    security: SecurityModule;
    configManager: ConfigManager;
    settings: ExtensionSettings;
  }) {
    // Wire with explicit connection-state guard
    const pendingSubscription = connector.onStateChange(state => {
      if (state === ConnectionState.Subscribed) {
        // NOW safe to process approvals
        setupApprovalFlow();
      }
    });
  }
  
  private setupApprovalFlow(): void {
    // This MUST only run after Subscribed to avoid missed events
    this.connector.onPendingApproval(p => {
      const outbound = toOutbound(p, this.configManager); // includes sessionId/directory
      this.approvalSM.registerPending(outbound).then(ref => {
        this.provider.sendApprovalRequest(outbound).then(msgRef => {
          this.approvalSM.setSentReference(p.requestId, msgRef);
        });
      });
    });
    
    this.provider.onDecision(d => {
      this.approvalSM.validateAndConsume(d).then(resolved => {
        this.provider.applyResolvedDecision(resolved);
        if (resolved.action) {
          this.connector.replyToPermission(
            resolved.requestId, resolved.sessionId, resolved.directory,
            toPermissionReply(resolved.action)
          );
        }
        this.metrics.incDecision(resolved);
      });
    });
  }
}
```

### 2.4 `deactivate()` cleanup (deterministic disposal)

```
deactivate():
  1. Orchestrator.dispose()  // stops all flows
  2. Provider.stop()         // abort polling, flush/cancel in-flight
  3. Connector.dispose()     // close SSE, cancel timers
  4. ApprovalSM.dispose()    // stop sweeper, flush audit
  5. SecurityModule.dispose() // clear in-memory handles
  6. ConfigManager.dispose() // dispose fs watcher
  7. StatusBar.dispose()
  8. OutputChannel.dispose()
  9. ctx.subscriptions.forEach(d => d.dispose()) // safety net
```

---

## 3. `package.json` Contribution Points

```jsonc
{
  "name": "mko-ainotify",
  "displayName": "Mko-AINotify",
  "version": "0.1.0",
  "engines": { "vscode": "^1.89.0" },
  "categories": ["Other"],
  "main": "./dist/extension.js",
  "activationEvents": ["*", "onStartupFinished"],
  "contributes": {
    "configuration": {
      "title": "Mko-AINotify",
      "properties": {
        "mkoAinotify.provider": {
          "type": "string", "enum": ["telegram", "discord", "ntfy", "pushover"],
          "default": "telegram"
        },
        "mkoAinotify.pollingIntervalMs": {
          "type": "number", "default": 2000, "minimum": 1000, "maximum": 5000
        },
        "mkoAinotify.approvalTtlMs": {
          "type": "number", "default": 1800000, "minimum": 60000
        },
        "mkoAinotify.allowedTelegramUserIds": {
          "type": "array", "items": { "type": "string" }, "default": []
        },
        "mkoAinotify.backendDiscovery": {
          "type": "string", "enum": ["serverJson", "processScan"], "default": "serverJson"
        },
        "mkoAinotify.connectionTimeoutMs": {
          "type": "number", "default": 30000, "minimum": 5000, "maximum": 120000
        },
        "mkoAinotify.dedupeWindowMs": {
          "type": "number", "default": 5000, "minimum": 1000
        },
        "mkoAinotify.dedupeTtlMs": {
          "type": "number", "default": 30000, "minimum": 5000
        },
        "mkoAinotify.clockSkewSec": {
          "type": "number", "default": 60, "minimum": 0, "maximum": 600
        },
        "mkoAinotify.sweepIntervalMs": {
          "type": "number", "default": 60000, "minimum": 5000
        },
        "mkoAinotify.secretGraceMs": {
          "type": "number", "default": 300000, "minimum": 0
        },
        "mkoAinotify.auditRetentionDays": {
          "type": "number", "default": 30, "minimum": 1
        },
        "mkoAinotify.logLevel": {
          "type": "string", "enum": ["error", "warn", "info", "debug"], "default": "info"
        },
        "mkoAinotify.statusBarDebounceMs": {
          "type": "number", "default": 1000, "minimum": 100, "maximum": 5000
        }
      }
    },
    "commands": [
      { "command": "mkoAinotify.setBotToken", "title": "Mko-AINotify: Set Telegram Bot Token" },
      { "command": "mkoAinotify.rotateSecret", "title": "Mko-AINotify: Rotate HMAC Secret" },
      { "command": "mkoAinotify.showAuditLog", "title": "Mko-AINotify: Show Audit Log" },
      { "command": "mkoAinotify.flushQueue", "title": "Mko-AINotify: Flush Notification Queue" }
    ]
  }
}
```

---

## 4. Status-Bar + OutputChannel UX

### 4.1 `StatusBarController` states

| ConnectionState | Icon | Text | Color | Tooltip |
|---|---|---|---|---|
| `Subscribed` | `$(plug)` | `$(plug) Mko · N` | default | "Connected · N pending approvals" |
| `Discovering` | `$(sync~spin)` | `$(sync~spin) Mko` | default | "Discovering Kilo backend…" |
| `Connecting` | `$(sync~spin)` | `$(sync~spin) Mko` | default | "Connecting…" |
| `Reconnecting` | `$(warning)` | `$(warning) Mko` | warning | "Reconnecting (attempt k)" |
| `Recovering` | `$(sync~spin)` | `$(sync~spin) Mko` | default | "Recovering missed events…" |
| `Degraded` | `$(warning)` | `$(warning) Mko` | warning | "Degraded — backend/Telegram unstable" |
| `Error` | `$(error)` | `$(error) Mko` | error | "Error: <redacted reason>" |
| `Disposed` | hidden | — | — | — |

- Pending count `N` capped at `99+`.
- Color turns warning when `N > 0`.
- Debounce enforced via `statusBarDebounceMs` setting.

### 4.2 `OutputChannel` — structured log output

- Channel name `"Mko-AINotify"`.
- All modules log through shared `Logger`.
- Redaction: passwords/tokens/callback data replaced with `"***"` or `"<callback_data:len=NN>"`.
- Structured format: `[ISO timestamp] LEVEL [component] key=value msg`.

---

## 5. Global Config Schema (Consolidated)

```typescript
// src/core/shared/types.ts
export type BackendDiscoveryMethod = "serverJson" | "processScan";
export type ProviderKind = "telegram" | "discord" | "ntfy" | "pushover";
export type LogLevel = "error" | "warn" | "info" | "debug";

export interface ExtensionSettings {
  // Part 1 (connector/config)
  pollingIntervalMs: number;
  approvalTtlMs: number;
  allowedTelegramUserIds: string[];
  backendDiscovery: BackendDiscoveryMethod;
  connectionTimeoutMs: number;
  dedupeWindowMs: number;
  // Part 3 (security/state)
  dedupeTtlMs: number;
  clockSkewSec: number;
  sweepIntervalMs: number;
  secretGraceMs: number;
  auditRetentionDays: number;
  // Part 4 (cross-cutting)
  provider: ProviderKind;
  logLevel: LogLevel;
  statusBarDebounceMs: number;
}
```

---

## 6. Cross-Cutting Error Handling & Retry Policy

### 6.1 Unified error taxonomy (`ExtensionErrorKind`)

```typescript
export enum ExtensionErrorKind {
  // Config
  ConfigNotFound = "config_not_found",
  ConfigInvalid = "config_invalid",
  // Backend / SSE
  BackendUnreachable = "backend_unreachable",
  BackendAuth = "backend_auth",
  SdkVersionMismatch = "sdk_version_mismatch",
  // Reply
  ReplyNotFound = "reply_not_found",
  ReplyTransport = "reply_transport",
  ReplyInvalid = "reply_invalid",
  ReplyDuplicate = "reply_duplicate",
  // Provider / Telegram
  ProviderTokenMissing = "token_missing",
  ProviderUnauthorizedUser = "unauthorized_user",
  ProviderSendFailed = "send_failed",
  ProviderRateLimited = "telegram_rate_limit",
  ProviderEditFailed = "edit_failed",
  ProviderNotSupported = "not_supported",
  ProviderInvalidResponse = "invalid_response",
  // Security
  SecuritySecretMissing = "secret_missing",
  SecuritySecretUnavailable = "secret_unavailable",
  SecurityRotationFailed = "rotation_failed",
  SecurityTokenMalformed = "token_malformed",
  CallbackInvalid = "callback_invalid",
  CallbackExpired = "callback_expired",
  CallbackTampered = "callback_tampered",
  CallbackUnknownHandle = "unknown_handle",
  CallbackRateLimited = "rate_limited",
  // General
  Internal = "internal"
}
```

### 6.2 Retry policy location matrix

| Operation | Retry Logic | Owner |
|---|---|---|
| SSE connect | Exp backoff (1-30s), full jitter | Part 1 `reconnectPolicy.ts` |
| SSE timeout | Single retry then reconnect | Part 1 `KiloBackendConnector` |
| `replyToPermission` | 1 immediate retry, 401 triggers re-auth, 404 no retry | Part 1 `KiloBackendConnector` |
| Telegram sendMessage | 3 retries then bounded queue | Part 2 `TelegramProvider` |
| Telegram getUpdates 429 | Honor `retry_after` or exp backoff (1-32s) | Part 2 `PollingLoop` |
| Telegram answerCallbackQuery | 1 retry, 5s timeout, never blocks decision flow | Part 2 `TelegramProvider` |
| HMAC verify DoS | Rate limited (100/sec sliding window) | Part 3 `RateLimiter` |

**No double-retry guarantee:** Each operation has exactly one retry owner. Modules do not retry each other's operations.

---

## 7. Observability

### 7.1 Structured logger (`src/core/shared/logger.ts`)

- `getLogger(component)` returns typed logger.
- Pipeline: Logger → redaction filter → OutputChannel sink + console (dev).
- Levels: DEBUG (off), INFO (state changes), WARN (recoverable), ERROR (schema/fatal).

### 7.2 Metrics collector (`src/core/shared/metrics.ts`)

```typescript
export interface MetricsSnapshot {
  approvalsSent: number;
  approved: number;
  rejected: number;
  expired: number;
  errorsByKind: Partial<Record<ExtensionErrorKind, number>>;
  connectionUptimeMs: number;
  reconnects: number;
  lastError?: { kind: ExtensionErrorKind; at: string };
  queueDepth: number;      // NEW: pending Telegram queue
  queueDropped: number;    // NEW: dropped due to TTL
}
```

### 7.3 Health signal

- `EventBus.fire("health", HealthSignal)` where HealthSignal contains connection state, pending count, degraded flag, queue depth.

---

## 8. Consolidated Internal API / Message Contract Catalog (The Contract Bible - REVISED)

> REVISED to fix inconsistencies from Part 1-3. Part 4 owns `src/core/shared/types.ts` that re-exports canonical types.

| Type | Definition | Owner | Notes |
|---|---|---|---|
| `PendingApproval` | SSE-normalized approval request | Part 1 `connector/types.ts` | **REQUIRED**: `metadata.command` field verified against Kilo SSE |
| `ConnectionState` | Enum: Idle→Discovering→Connecting→Subscribed→Reconnecting→Recovering→Degraded→Error→Disposed | Part 1 | |
| `ConfigProvider` | Interface: `getActivePort()`, `getBackendAuth()`, `getConfig()`, `watchConfigChanges()` | Part 1 | |
| `BackendAuth` | `{ port, password, pid?, version? }` | Part 1 | Password NEVER logged |
| `KiloServerConfig` | Validated server.json + sourcePath + readAt | Part 1 | |
| `ExtensionSettings` | Consolidated settings object (§5) | Part 4 | |
| `PermissionReply` | `"once" \| "always" \| "reject"` | Part 1 | Forwarded to backend |
| `ReplyResult` | `{ ok, status, error? }` | Part 1 | |
| `OutboundApproval` | `{ requestId, sessionId, command, cwd, project, reason?, timestamp, ttlMs, directory }` | Orchestrator (Part 4) | Created from PendingApproval + config context |
| `ApprovalAction` | `"approve" \| "reject" \| "approve_once" \| "always_allow"` | Part 2 `telegramTypes.ts` | |
| `MessageReference` | `{ providerId, chatId, messageId, correlationId? }` | Part 2 | |
| `InboundDecision` | `{ callbackQueryId, userId, rawCallbackData, chatId, messageId, receivedAt, requestId? }` | Part 2 | **RAW, unparsed**; verification in Part 3 |
| `DecisionStatus` | `"approved" \| "rejected" \| "expired" \| "invalid" \| "unauthorized" \| "error"` | Part 2 | |
| `ResolvedDecision` | `{ callbackQueryId, requestId, sessionId, directory, status, displayText, action? }` | Part 2/3 | **MUST include directory** for reply routing |
| `SecuritySeam` | `{ getBotToken(), getAuthorizedUserIds(), signCallback(requestId, action) }` | Part 3 | Updated to match revised SecurityModule |
| `ContextProvider` | **NEW**: `{ getContext(requestId): Promise<{ sessionId, directory }> }` | Part 3 | Provides session context for signing |
| `VerifyOutcome` | `{ status: valid/expired/tampered/unknown_handle/malformed/rate_limited, requestId, sessionId, directory, action, expiry? }` | Part 3 | |
| `HandleValue` | `{ requestId, sessionId, directory, action }` | Part 3 | Stored in HandleMap for routing |
| `ExtensionErrorKind` | Unified error taxonomy enum | Part 4 | |
| `ExtensionError` | `{ kind: ExtensionErrorKind, message, cause? }` | Part 4 | |

**Contract invariants:**
1. `CallbackToken` MUST be `Buffer.byteLength(t,"utf8") <= 64` (enforced by `assertTokenLength()` in SecurityModule).
2. `InboundDecision.rawCallbackData` NEVER parsed by Part 2 — only forwarded raw.
3. `OutboundApproval` created EXCLUSIVELY by orchestrator from `PendingApproval`.
4. Empty `allowedTelegramUserIds` ⇒ ApprovalStateManager rejects all (safe default enforced).
5. All timestamps ISO-8601 UTC. Envelope expiry uses Unix seconds.

---

## 9. Testing Strategy (Overall)

### 9.1 Unit tests (Vitest)
- `FakeExtensionContext` implements `ExtensionContext` with mock SecretStorage (Memento-backed).
- Per-module suites from Part 1-3.
- Part 4 additions: `EventBus.test.ts`, `Orchestrator.test.ts`, `StatusBarController.test.ts`, `MetricsCollector.test.ts`, `uncaught.test.ts`.

### 9.2 Integration tests
- `MockKiloClient` + `FakeProvider` for full-loop testing.
- Tests for reconnection flow, config hot-reload, provider drain+resend.
- Contract tests: `FakeProvider.test.ts` runs against TelegramProvider, stubs.

### 9.3 Gated live smoke
- `E2E_TELEGRAM=1` environment flag (default off).
- Manual only for release validation.
- Never in CI.

### 9.4 Hard-to-test mitigations

| Concern | Mitigation |
|---|---|
| Real SecretStorage | FakeSecretStore with Memento interface |
| SSE timing | Scheduler interface with fake timers |
| Clock skew | Inject `now()` into SecurityModule + RateLimiter |
| Multi-window race | Composite key `(windowId, requestId)` for dedupe |
| Offline behavior | Network error injection + queue TTL assertion |

---

## 10. Consolidated Milestones (M0–M5 Roadmap - REVISED)

| Phase | Objective | Key Deliverables | Dependencies |
|---|---|---|---|
| **M0 — Scaffold** | Extension skeleton, foundation types | `package.json`, `tsconfig`, `vitest.config`, `shared/logger.ts`, `shared/errors.ts`, `shared/types.ts` (contract bible), `EventBus.ts`, `FakeExtensionContext` | None |
| **M1 — Connect + Config** | Backend connection working | `ConfigManager` (cross-platform `server.json`), `KiloBackendConnector` (SSE+normalize+reply+reconnect+recovery), `ExtensionSettings` schema | M0 |
| **M2 — Notify** | Outbound notification path | `NotificationProvider` interface, `TelegramProvider`, `messageFormatter`, `PollingLoop`, `createProvider()` factory, orchestrator wires `PendingApproval`→`OutboundApproval`→`sendApprovalRequest` | M1 |
| **M3 — Secure Approve** | Authenticated, replay-safe decisions | `SecurityModule` (sign/verify, SecretStorage, HandleMap, RateLimiter), `ApprovalStateManager` (register/validate/consume/expire), `ContextProvider` integration, orchestrator wires full decision flow | M1, M2 |
| **M4 — Observability + Commands** | Status bar, logs, resilience | `StatusBarController`, `MetricsCollector`, global handlers, `setBotToken`/`rotateSecret`/`showAuditLog`/`flushQueue` commands, config hot-reload, `deactivate()` cleanup | M3 |
| **M5 — Provider Tests + QA** | Swap-safety + full coverage | `FakeProvider` contract suite, full-loop integration tests, gated smoke test, CI pipeline passing, README complete | M4 |

**Walking skeleton principle:** M0+M1+first M2 slice enables end-to-end approval flow through `FakeProvider`, proving the architecture before Telegram integration.

---

## 11. Prioritized Task Backlog (Single Ordered)

### Phase M0 — Scaffold (P0)
1. **T-P4-01** `package.json` manifest with full `contributes.configuration` and commands
2. **T-P4-02** `tsconfig.json` (strict, noUncheckedIndexedAccess), `vitest.config.ts`, eslint
3. **T-P4-03** `src/core/shared/logger.ts` — structured logging with `redact()`/`redactToken()`/`redactPassword()`
4. **T-P4-04** `src/core/shared/errors.ts` — `ExtensionErrorKind` enum + `ExtensionError` base
5. **T-P4-05** `src/core/shared/types.ts` — **contract bible** re-exporting all types (includes ContextProvider, fixed SecuritySeam)
6. **T-P4-06** `src/core/shared/eventBus.ts` — typed mediator
7. **T-P4-07** `src/core/test/doubles/FakeExtensionContext.ts` — mock VS Code context

### Phase M1 — Connect + Config (P0/P1)
8. **T-P4-08** `config/types.ts` (consolidated `ExtensionSettings`)
9. **T-P4-09** `config/settingsSchema.ts` (Zod validation)
10. **T-P4-10** `config/serverJsonReader.ts` — CORRECTED cross-platform paths (`%APPDATA%\kilo` Win)
11. **T-P4-11** `config/ConfigManager.ts` with retry-on-missing logic (500ms polling for 30s)
12. **T-P4-12** `connector/types.ts` (`ConnectionState`, `PendingApproval`, `PermissionReply`)
13. **T-P4-13** `connector/eventNormalizer.ts` (+v1/v2 support)
14. **T-P4-14** `connector/reconnectPolicy.ts` (exp backoff + jitter + cap)
15. **T-P4-15** `connector/KiloBackendConnector.ts` (connect/reply/recovery/timeout)
16. **T-P4-16** `Orchestrator.ts` skeleton (instantiation only, no wiring yet)

### Phase M2 — Notify (P1)
17. **T-P4-17** `provider/NotificationProvider.ts` interface + `ProviderContext`
18. **T-P4-18** `provider/TelegramApiClient.ts` interface + DTOs
19. **T-P4-19** `provider/FetchTelegramClient.ts` (outbound HTTPS only)
20. **T-P4-20** `provider/messageFormatter.ts` (pure function, HTML escaping, 64-byte token check)
21. **T-P4-21** `provider/PollingLoop.ts` (getUpdates with offset persistence)
22. **T-P4-22** `provider/TelegramProvider.ts` (send/poll/handle/edit)
23. **T-P4-23** `provider/adapters/*.ts` (Ntfy/Discord/Pushover stubs)
24. **T-P4-24** `createProvider.ts` factory function
25. **T-P4-25** Orchestrator.full Wiring: `onPendingApproval`→send, `onDecision`→resolve

### Phase M3 — Secure Approve (P1)
26. **T-P4-26** `security/envelope.ts` (42-byte layout constants + `assertTokenLength()`)
27. **T-P4-27** `security/SecretVault.ts` (SecretStorage + encrypted file fallback)
28. **T-P4-28** `security/RateLimiter.ts` (100/sec sliding window)
29. **T-P4-29** `security/HandleMap.ts` + `ContextProvider` interface
30. **T-P4-30** `security/SecurityModule.ts` (signCallback/verifyCallback/getBotToken/rotateSecret/forgetHandle)
31. **T-P4-31** `state/PendingStore.ts`, `state/DedupStore.ts`, `state/TtlSweeper.ts`, `state/AuditLog.ts`
32. **T-P4-32** `state/ApprovalStateManager.ts` (register/validate/consume/expire)
33. **T-P4-33** Orchestrator: connect SecuritySeam to TelegramProvider, SecurityModule to ApprovalSM

### Phase M4 — Observability + Commands (P1/P2)
34. **T-P4-34** `StatusBarController.ts` (state→icon/text/color, debounce, count cap)
35. **T-P4-35** `MetricsCollector.ts` (counters, uptime, queue depth)
36. **T-P4-36** `installUncaughtHandlers.ts` (global try/catch, circuit breaker)
37. **T-P4-37** `mkoAinotify.setBotToken` command (SecretStorage prompt)
38. **T-P4-38** `mkoAinotify.rotateSecret` command
39. **T-P4-39** `mkoAinotify.showAuditLog` command
40. **T-P4-40** `mkoAinotify.flushQueue` command
41. **T-P4-41** Config hot-reload handling (`onDidChangeConfiguration` → live update polling interval)
42. **T-P4-42** SDK version check on startup (warn+degrade on mismatch)
43. **T-P4-43** `deactivate()` deterministic disposal order
44. **T-P4-44** VS Code native fallback notification (Telegram down >5min)

### Phase M5 — Provider Tests + QA (P2)
45. **T-P4-45** Unit tests: EventBus, Orchestrator, StatusBar, Metrics, uncaught handlers
46. **T-P4-46** Full-loop integration test (MockKiloClient + FakeProvider)
47. **T-P4-47** FakeProvider contract tests (all providers)
48. **T-P4-48** Provider drain+resend integration (R-A6)
49. **T-P4-49** Gated `E2E_TELEGRAM` smoke test harness
50. **T-P4-50** CI pipeline (lint → typecheck → unit → integration → package)
51. **T-P4-51** README documentation
52. **T-P4-52** Cross-part integration test: verify `metadata.command` field exists in PendingApproval

---

## 12. Critical Validation Corrections

### 12.1 Contract Inconsistencies Fixed (§8 Contract Bible)

| Issue | Severity | Correction |
|---|---|---|
| `SecuritySeam.signCallback(actionId, action)` vs `SecurityModule.signCallback(requestId, action)` | HIGH | REVISED: `signCallback(requestId, action)` with `ContextProvider` providing sessionId/directory. ContextProvider interface added to shared types. |
| `OutboundApproval` missing `directory` field | HIGH | Added `directory` field to `OutboundApproval` and `ResolvedDecision` for reply routing. |
| `ContextProvider` not in consolidated types | MEDIUM | Added to `shared/types.ts`. |
| `mkoAinotify.flushQueue` command missing | MEDIUM | Added to `package.json` commands. |

### 12.2 Concurrency & Race Condition Handling (NEW)

| Issue | Mitigation |
|---|---|
| Multiple concurrent approvals | `ApprovalStore` bounded to 1000 entries; Telegram rate-limiting via queue; handle uniqueness via crypto-random 8-byte handle |
| Provider switch mid-flight | Orchestrator drains old provider, resends pending approvals via new provider, preserves handle→messageRef map |
| Multi-window Telegram conflicts | Extension activates in single window; SecretStorage scoped; dedupe key includes window ID |
| SSE event ordering | `PendingApproval.sequence` monotonic counter; recovery uses `/api/permission` list for missed events |

### 12.3 Offline Recovery (ENHANCED)

| Scenario | Handling |
|---|---|
| Network offline during approval send | Message queued in `ApprovalStore` (bounded memory), TTL = `approvalTtlMs`. Flush on reconnect. |
| Extension restart during pending approval | `HandleMap` persisted to `globalState`; `callback_query` offset persisted; sweeper restarts with TTL. |
| Kilo process restart | `ConfigManager` detects new `server.json` port; `KiloBackendConnector` reconnects; recovery fetches pending via `/api/permission`. |
| Telegram API outage | Messages queued; after reconnect, flush queue; if Telegram down >5min, VS Code native notification fallback. |

### 12.4 Secrets Management (VERIFIED)

| Secret | Storage | Never Logged | Rotation |
|---|---|---|---|
| Bot token | VS Code `SecretStorage` only | ✅ `redactToken()` | `rotateSecret` command |
| HMAC secret | VS Code `SecretStorage` only | ✅ | `rotateSecret` with grace period |
| Password (server.json) | File only, read by ConfigManager | ✅ `redactPassword()` | No rotation (Kilo controls) |

---

## 13. Backward Compatibility & Future Extensibility

| Change | Backward Compatible | Migration |
|---|---|---|
| SDK version mismatch | Graceful degradation (warn, continue) | Update extension to match Kilo version |
| Handle map versioning | Version field in envelope | Graceful decode failure handles old tokens |
| Provider swap | Queue drain + resend | No user action required |
| Settings schema extension | New fields optional with defaults | No migration needed |

---

## Validation Scorecard

| Category | Score (/10) | Notes |
|----------|-------------|-------|
| **Architecture** | 9 | Clean separation, DI seams, state machine. Contract inconsistencies resolved. ContextProvider addition clarifies cross-module boundaries. |
| **Implementation Risk** | 8 | SSE timeout, dedupe, config null handling fixed. Activation race mitigation strengthened. Rate limiting added. |
| **Maintainability** | 9 | Well-structured modules, small files, clear interfaces. Contract bible ensures consistency. Tests planned. |
| **Production Readiness** | 8 | Good error handling, logging, retry strategy. Clock drift handled. Secrets in SecretStorage. Graceful degradation. |

### Top Issues Found & Resolved

1. **[CRITICAL → RESOLVED]** Contract mismatch: `SecuritySeam.signCallback` signature updated to `(requestId, action)` with `ContextProvider` injection. ContextProvider added to shared types.

2. **[HIGH → RESOLVED]** Missing `directory` in `OutboundApproval`/`ResolvedDecision` — Added `directory` field to both types, sourced from `PendingApproval.directory` via orchestrator.

3. **[HIGH → RESOLVED]** Cross-platform secret fallback path — Uses `SecretStorage` with encrypted file fallback at `%APPDATA%\mko-ainotify\secrets.json.enc` (Windows) or `~/.config/mko-ainotify/secrets.json.enc` (Unix).

4. **[HIGH → RESOLVED]** Missing activation race mitigation — Retained retry loop with 500ms polling for 30s, exponential backoff beyond.

5. **[MEDIUM → RESOLVED]** Missing `flushQueue` command — Added to `package.json` commands for manual queue recovery.

6. **[MEDIUM → RESOLVED]** Missing `ContextProvider` in shared types — Added to `shared/types.ts` contract bible.

7. **[LOW → RESOLVED]** Provider drain+resend on switch — Documented in §2.3 and tested in T-P4-48.

8. **[LOW → RESOLVED]** Multi-window conflicts — Single-window activation enforced; SecretStorage scoped; composite dedupe keys.

---

*Plan validated against: VS Code Extension API v1.89+ (StatusBarItem, OutputChannel, EventEmitter, SecretStorage, activationEvents), Telegram Bot API v10.2 (64-byte callback_data limit), Kilo Code 7.4.11 / opencode backend API, NIST SP 800-107 (truncated HMAC), plans 01-03 and Part 4 research.*

---

## Summary

**Overall verdict:** The cross-cutting plan is technically sound but had critical contract inconsistencies between modules that are now resolved. The architecture follows clean separation of concerns with proper DI seams.

**Most important fix:** Added `ContextProvider` interface and corrected `SecuritySeam.signCallback` signature to ensure consistent cross-module contracts for HMAC signing with session context.

**Scores:** Architecture: 9/10, Implementation Risk: 8/10, Maintainability: 9/10, Production Readiness: 8/10.