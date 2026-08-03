# Part 4 — Cross-Cutting Architecture: Extension Bootstrap, Wiring, Observability

## 1. Extension Bootstrap Architecture

The extension uses a simple factory pattern (no DI container) for deterministic wiring. All modules are instantiated in `activate()` and disposed in `deactivate()`.

```
┌─────────────────────────────────────────────────────────────┐
│                     ExtensionContext                       │
│  (secrets, globalState, subscriptions, workspaceState)        │
└───────────────┬─────────────────────────┬───────────────────┘
                │                         │
                ▼                         ▼
┌─────────────────┐     ┌────────────────────────┐
│   Logger ┌──────┴─┐   │    ExtensionConfig   █  │
│ (shared) │Logger.ts│   │  pollingIntervalMs: 2000│
└──────────┴────────┘   │  approvalTtlMs: 1800000  │
                        │  allowedTelegramUserIds: [] │
                        │  backendDiscovery: serverJson│
                        └───────────┬──────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│  Dependency Graph (factory wiring)                                │
├───────────────────────────────────┼───────────────────────────────┤
│                                   │                              │
│  ┌─────────────────────────────────┼──────────────────────────────┐ │
│  │ConfigManager implements ConfigProvider                     │ │
│  │├── getActivePort() → number                              │ │
│  │├── getBackendAuth() → BackendAuth                          │ │
│  │├── watchConfigChanges(listener) → Disposable                │ │
│  │└── getSettings() → ExtensionSettings                       │ │
│  └─────────────────────────────────┼──────────────────────────────┘ │
                                    │                              │
│  ┌─────────────────────────────────┼──────────────────────────────┐ │
│  │SecurityModule (depends: SecretVault, HandleMap)             │ │
│  │├── getBotToken() → Promise<string>                        │ │
│  │├── getAuthorizedUserIds() → Promise<number[]>             │ │
│  │├── signCallback(requestId, action) → Promise<string>      │ │
│  │└── verifyCallback(token) → Promise<VerifyOutcome>           │ │
│  └─────────────────────────────────┼──────────────────────────────┘ │
                                    │                              │
│  ┌─────────────────────────────────┼──────────────────────────────┐ │
│  │ApprovalStateManager (depends: SecurityModule, PendingStore)│ │
│  │├── registerPending(pending)                                │ │
│  │├── validateAndConsume(response) → ResolvedDecision           │ │
│  │└── expireOld(timeoutMs) → number                           │ │
│  └─────────────────────────────────┼──────────────────────────────┘ │
                                    │                              │
│  ┌─────────────────────────────────┼──────────────────────────────┐ │
│  │TelegramProvider (depends: SecurityModule, ApprovalStore)   │ │
│  │├── initialize() → Promise<void>                             │ │
│  │├── sendApprovalRequest(approval) → Promise<MessageReference>  │ │
│  │├── start() → Promise<void>                                  │ │
│  │├── stop() → Promise<void>                                   │ │
│  │└── onDecision(cb) → Disposable                              │ │
│  └─────────────────────────────────┼──────────────────────────────┘ │
                                    │                              │
│  ┌─────────────────────────────────┼──────────────────────────────┐ │
│  │KiloBackendConnector (depends: ConfigManager)              │ │
│  │├── connect() → Promise<void>                                │ │
│  │├── onPendingApproval → Event<PendingApproval>                 │ │
│  │├── onStateChange → Event<ConnectionStateChange>               │ │
│  │└── replyToPermission(requestId, sessionId, directory, reply)  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

## 2. End-to-End Data Flow (One Approval)

```
Kilo Backend (SSE)                                Extension Host
permission.asked ──────────────────────────────────►
  { id, type, properties: { id, sessionID, permission, metadata } }

                              │ normalize() → PendingApproval
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    PendingApproval                             │
│  { eventId, requestId, sessionId, permission, patterns,         │
│    metadata: { command, args }, directory, receivedAt }        │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ onPendingApproval
                 ┌─────────────────────────┐
                 │ ApprovalStateManager    │
                 │ registerPending()       │
                 └───────────┬─────────────┘
                             │ OutboundApproval
                             ▼
                 ┌─────────────────────────┐
                 │ SecurityModule          │
                 │ signCallback(4 actions) │
                 └───────────┬─────────────┘
                             │ 4 signed tokens ≤64 bytes
                             ▼
                 ┌─────────────────────────┐
                 │ TelegramProvider        │
                 │ sendApprovalRequest()   │
                 │   → sendMessage()       │
                 │   → store MessageRef    │
                 └─────────────────────────┘
                              │
                              ▼ (Telegram API)
                    ┌───────────────────────┐
                    │  Mobile Notification │
                    │  [✅ Approve]       │
                    │  [❌ Reject]        │
                    └───────────────────────┘
                              │ user taps button
                              ▼ callback_query (raw)
                 ┌─────────────────────────┐
                 │ TelegramProvider        │
                 │ handleCallbackQuery()   │
                 │   → answerCallbackQuery │
                 │   → onDecision()        │
                 └───────────┬─────────────┘
                             │ InboundDecision (raw, unparsed)
                             ▼
                 ┌─────────────────────────┐
                 │ ApprovalStateManager    │
                 │ validateAndConsume()  │
                 │   → verify + authorize│
                 └───────────┬─────────────┘
                             │ ResolvedDecision
                             ▼
                 ┌─────────────────────────┐
                 │ TelegramProvider        │
                 │ editMessage()           │
                 │   removes inline keys   │
                 └───────────┬─────────────┘
                             │ PermissionReply
                             ▼
                 ┌─────────────────────────┐
                 │ KiloBackendConnector    │
                 │ replyToPermission()     │
                 └───────────┬─────────────┘
                             │
                             ▼
                    Kilo agent continues execution
```

## 3. Event Bus / Orchestrator Design

Typed EventEmitter pattern for all cross-module communication:

```typescript
// src/core/shared/eventBus.ts
import { EventEmitter, Event } from "vscode";

export class EventBus {
  private emitters = new Map<string, EventEmitter<any>>();

  get<T>(eventName: string): Event<T> {
    if (!this.emitters.has(eventName)) {
      this.emitters.set(eventName, new EventEmitter<T>());
    }
    return this.emitters.get(eventName)!.event;
  }

  fire<T>(eventName: string, data: T): void {
    const emitter = this.emitters.get(eventName);
    emitter?.fire(data);
  }
}
```

Cross-module events:

| Event Name | Payload | Emitted By | Handled By |
|------------|---------|------------|------------|
| `permission.asked` | PendingApproval | KiloBackendConnector | Orchestrator |
| `connection.stateChange` | ConnectionStateChange | KiloBackendConnector | StatusBarController |
| `decision.inbound` | InboundDecision | TelegramProvider | ApprovalStateManager |
| `decision.resolved` | ResolvedDecision | ApprovalStateManager | Metrics, TelegramProvider |
| `config.changed` | KiloServerConfig | ConfigManager | KiloBackendConnector |

## 4. StatusBar + OutputChannel Integration

`StatusBarController` subscribes to `connection.stateChange` and maintains:
- Icon: `$(plug)` = connected, `$(error)` = error, `$(warning)` = reconnecting
- Text: `Approvals: N` with pending count from ApprovalStateManager
- Tooltip: Last error or connection details
- OutputChannel: "Mko-AINotify" logs all events at DEBUG level, errors at ERROR level

Triggers: `onStateChange` → render, `onPendingUpdate(count)` → render, `onError(msg)` → render + log.

## 5. Global Config Schema

```json
{
  "pollingIntervalMs": { "type": "number", "default": 2000, "min": 1000, "max": 5000 },
  "approvalTtlMs": { "type": "number", "default": 1800000, "min": 60000 },
  "allowedTelegramUserIds": { "type": "array", "items": { "type": "string" }, "default": [] },
  "backendDiscovery": { "type": "string", "enum": ["serverJson","processScan"], "default": "serverJson" },
  "connectionTimeoutMs": { "type": "number", "default": 30000, "min": 5000, "max": 120000 },
  "dedupeWindowMs": { "type": "number", "default": 5000, "min": 1000 },
  "provider": { "type": "string", "enum": ["telegram","discord","ntfy","pushover"], "default": "telegram" }
}
```

Provider selection via factory in `extension.ts`: `createProvider("telegram", context)` returns TelegramProvider; unknown kind throws ProviderError.

## 6. Cross-Cutting Error/Retry Policy

Error taxonomy: `config_not_found`, `config_invalid`, `backend_unreachable`, `backend_auth`, `reply_not_found`, `reply_transport`, `telegram_rate_limit`, `callback_invalid`, `callback_expired`, `unauthorized_user`, `token_malformed`, `rate_limited`, `internal`.

Retries: Connector exponential backoff (base 1s, cap 30s); Telegram 429 backoff with full jitter; send retry ×3 → then queue. Global `uncaughtException` handler logs + fires `error.uncaught` + graceful shutdown.

## 7. Observability

- Logger: `getLogger(component)` with structured JSON output; redacts `password`, `token`, `rawCallbackData`
- Metrics: `approvals_sent/approved/rejected/expired`, `errors_total{kind}`
- Health: StatusBar icon + `EventBus.health` signal

## 8. Consolidated Contracts

Types shared via `src/core/shared/types.ts`:
- `PendingApproval`, `ConnectionState`, `ReplyResult`
- `OutboundApproval`, `InboundDecision`, `ResolvedDecision`, `DecisionStatus`, `MessageReference`
- `BackendAuth`, `KiloServerConfig`, `ExtensionSettings`
- `ExtensionError`, `ExtensionErrorKind`

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Activation race | `onStartupFinished`; ConfigManager watches `server.json`; retries until ready |
| StatusBar spam | Debounce 100ms; only error tooltip |
| Uncaught crashes | Global handler + try/catch in all async ops |
| Config hot-reload | Reconnect on change; preserve pending state |

---

*Cited: VS Code Extension API, Telegram Bot API v10.2, Kilo Code 7.4.11.*