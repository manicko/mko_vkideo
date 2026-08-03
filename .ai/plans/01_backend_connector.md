# Plan 01 — Backend Connector & Config/Port Discovery (Part 1 of 5)

**Project:** Mko-AINotify — companion VS Code extension that forwards Kilo Code (opencode backend) permission approval requests to a mobile notification channel and relays decisions back.

**This part delivers:** Modules **KiloBackendConnector** and **ConfigManager** — the connection/config foundation layer of the 5-module architecture. All downstream modules (ApprovalStateManager, SecurityModule, TelegramProvider) depend on the contracts defined here.

**Source research:** `part1_requirements.md`, `part1_architecture.md`, `part1_risks.md`, `validation_priority.md`.

---

## 1. Scope & Goals

### 1.1 What this part delivers
- **ConfigManager**: robust discovery, cross-platform path resolution, schema validation, and live watching of `server.json`; typed read of extension settings; worktree→port mapping helpers.
- **KiloBackendConnector**: SDK client lifecycle (init, connect, SSE subscribe, disconnect, reconnect), normalization of `permission.asked` / `permission.v2.asked` SSE events into a stable `PendingApproval` type, and reply execution via `client.permission.reply()`.
- A clean, dependency-inverted boundary between the two modules (Connector depends on a `ConfigProvider` abstraction, never reads files directly).
- Connection state machine + observable state stream for status-bar integration.
- Recovery of missed events after reconnect via `/api/permission` list endpoint.

### 1.2 Explicit out-of-scope (handled by other parts)
| Responsibility | Owning part/module |
|---|---|
| Pending-approval TTL tracking, HMAC validation, callback dedupe | Part 2 — ApprovalStateManager |
| HMAC signing, bot-token/secret storage (SecretStorage) | Part 3 — SecurityModule |
| Telegram send/poll, inline keyboards, callback parsing | Part 4 — TelegramProvider |
| Decision → Telegram presentation, user-ID authorization | Part 4 + Part 2 |
| VS Code status bar UI rendering | Part 5 — extension activation/glue |
| Reply authorization (who is allowed to approve) | Part 2 + SecurityModule |

This part emits `PendingApproval` events and accepts `replyToPermission(...)` calls; it does **not** decide whether a reply is authorized, valid, or fresh.

---

## 2. Module Responsibilities & Boundaries

### 2.1 KiloBackendConnector — OWNS
- SDK client creation from port + auth supplied by config.
- SSE connection lifecycle to `http://127.0.0.1:{port}/global/event` (`client.global.event({ directory })`).
- Filtering + normalization of `permission.asked` and `permission.v2.asked` events into `PendingApproval`.
- Reconnection with exponential backoff + jitter and **connection timeout**.
- Missed-event recovery via `client.permission.list()` on (re)connect.
- Reply dispatch via `client.permission.reply({ path: { sessionID, requestID }, body: { reply } })`.
- Emitting connection-state changes and recovery status to subscribers.

### 2.2 KiloBackendConnector — MUST NOT
- Read or parse `server.json` or the filesystem (delegated to `ConfigProvider`).
- Validate extension settings schema (delegated to `ConfigManager`).
- Validate HMAC, store secrets, or touch `SecretStorage` (SecurityModule).
- Track pending-approval TTL, dedupe callbacks, or reject stale approvals (ApprovalStateManager).
- Send Telegram or any notification (TelegramProvider).
- Make authorization decisions about *who* may approve.

### 2.3 ConfigManager — OWNS
- Config file discovery + **correct cross-platform path resolution**.
- `server.json` parsing + strict schema validation (`port`, `password`, `version`, `pid`).
- Watching config file changes via VS Code `FileSystemWatcher` for rotation/password change.
- Reading + validating extension settings via `vscode.workspace.getConfiguration()`.
- Producing typed objects (`BackendAuth`, `KiloServerConfig`, `ExtensionSettings`, `WorktreeMapping`).

### 2.4 ConfigManager — MUST NOT
- Make SDK API calls or manage connections (no SSE, no `permission.reply`).
- Handle or normalize permission events.
- Validate HMACs or manage secrets.
- Track pending approvals or their lifecycle.

### 2.5 Dependency direction
```
ApprovalStateManager ──► consumes PendingApproval (from Connector)
TelegramProvider      ──► consumes PendingApproval
SecurityModule        ──► supplies password path (ConfigManager reads file; SecurityModule guards secret)
KiloBackendConnector  ──► depends on ConfigProvider interface (provided by ConfigManager)
ConfigManager         ──► no dependency on Connector
```
The Connector must accept a `ConfigProvider` (interface) rather than a concrete `ConfigManager`, so it is unit-testable with `FakeConfigReader`.

---

## 3. Folder Structure

TypeScript VS Code extension layout. Only Part 1 modules shown; other module folders are placeholders.

```
mko-ainotify/
├── .vscode/
│   └── launch.json                      # Extension debug config
├── package.json                         # VS Code manifest + contributes.configuration
├── tsconfig.json                        # Strict TypeScript
├── vitest.config.ts                     # Unit test config (fake timers, mocking)
├── src/
│   ├── extension.ts                     # activate()/deactivate() (thin glue)
│   ├── core/
│   │   ├── connector/
│   │   │   ├── KiloBackendConnector.ts          # main class
│   │   │   ├── ConnectionStateMachine.ts        # state enum + transitions
│   │   │   ├── eventNormalizer.ts               # SSE → PendingApproval (pure fn)
│   │   │   ├── reconnectPolicy.ts               # backoff + jitter + Last-Event-ID
│   │   │   ├── recovery.ts                      # /api/permission list diff/replay
│   │   │   └── types.ts                         # PendingApproval, ConnectionState
│   │   ├── config/
│   │   │   ├── ConfigManager.ts                 # implements ConfigProvider
│   │   │   ├── ConfigProvider.ts                # interface (DI seam)
│   │   │   ├── serverJsonReader.ts              # cross-platform path + read (CORRECTED)
│   │   │   ├── serverJsonSchema.ts              # Zod schema
│   │   │   ├── settingsSchema.ts                # Zod schema
│   │   │   ├── worktreeMapping.ts               # worktree path → port
│   │   │   └── types.ts                         # BackendAuth, KiloServerConfig
│   │   └── shared/
│   │       ├── logger.ts                        # structured logger (no secrets)
│   │       └── errors.ts                        # typed error classes
│   └── test/
│       ├── fixtures/
│       │   ├── server.json.valid.json
│       │   ├── server.json.invalid.port.json
│       │   └── sse.permission.asked.sample.txt
│       ├── connector/
│       │   ├── KiloBackendConnector.test.ts
│       │   ├── eventNormalizer.test.ts
│       │   ├── reconnectPolicy.test.ts
│       │   └── recovery.test.ts
│       └── config/
│           ├── serverJsonReader.test.ts
│           ├── serverJsonSchema.test.ts
│           ├── settingsSchema.test.ts
│           └── ConfigManager.test.ts
└── README.md
```

---

## 4. Interfaces / API Contracts (TypeScript)

### 4.1 Connector types (`src/core/connector/types.ts`)

```typescript
/** Finite connection states for the SSE/SDK lifecycle. */
export enum ConnectionState {
  Idle = "idle",
  Discovering = "discovering",
  Connecting = "connecting",
  Subscribed = "subscribed",
  Reconnecting = "reconnecting",
  Recovering = "recovering",    // Reconnected, recovering missed events
  Degraded = "degraded",      // SSE down but recovery polling active
  Error = "error",
  Disposed = "disposed",
}

/** Reply verdict forwarded verbatim to the backend. */
export type PermissionReply = "once" | "always" | "reject";

/** Normalized approval request emitted downstream. */
export interface PendingApproval {
  /** Stable event id (SSE event `id`, used for Last-Event-ID + dedupe). */
  eventId: string;
  /** Primary key for reply — SSE `properties.id`. */
  requestId: string;
  /** Originating session — SSE `properties.sessionID`. */
  sessionId: string;
  /** Tool/permission name: "bash" | "edit" | "read" | … (v1) or action (v2). */
  permission: string;
  /** File/resource patterns being accessed. */
  patterns: string[];
  /** Opaque backend metadata; for bash typically { command, args }. */
  metadata: Record<string, unknown>;
  /** Existing "always allow" patterns. */
  always: string[];
  /** Workspace/directory this approval is scoped to (for reply routing). */
  directory: string;
  /** Source event type, retained for diagnostics. */
  sourceType: "permission.asked" | "permission.v2.asked";
  /** ISO timestamp when normalized locally. */
  receivedAt: string;
  /** Monotonic sequence number for ordering (incremented per event). */
  sequence: number;
}

/** Emitted on every state transition. */
export interface ConnectionStateChange {
  from: ConnectionState;
  to: ConnectionState;
  reason?: string;
  at: string;
  reconnectAttempt?: number;
}

/** Abstraction the connector depends on (implemented by ConfigManager). */
export interface ConfigProvider {
  /** Returns active backend port or throws ConfigNotFoundError. */
  getActivePort(): Promise<number>;
  getBackendAuth(): Promise<BackendAuth>;
  getConfig(): Promise<KiloServerConfig>;
  watchConfigChanges(listener: (cfg: KiloServerConfig) => void): Disposable;
}

/** Interface for SecurityModule HMAC validation (used by Connector). */
export interface SecurityValidator {
  /** Verify HMAC signature on callback data; throws if invalid/expired. */
  verifyCallbackSignature(data: string, signature: string): Promise<boolean>;
  /** Get current time for expiry calculation (injected for testability). */
  now(): number;
}
```

### 4.2 Connector class (`src/core/connector/KiloBackendConnector.ts`)

```typescript
import { Disposable, Event, EventEmitter } from "vscode";

export interface KiloBackendConnectorOptions {
  /** Directory/workspace to scope the SSE subscription + replies. */
  directory: string;
  /** Config source (inject FakeConfigReader in tests). */
  config: ConfigProvider;
  /** Optional override of SDK client factory (inject mock in tests). */
  clientFactory?: KiloClientFactory;
  /** Reconnect policy override (inject deterministic policy in tests). */
  reconnect?: ReconnectPolicy;
  /** Connection timeout in ms (default 30000). */
  connectionTimeoutMs?: number;
  /** Event dedupe window in ms (default 5000). */
  dedupeWindowMs?: number;
}

export class KiloBackendConnector implements Disposable {
  private readonly _onPendingApproval = new EventEmitter<PendingApproval>();
  private readonly _onStateChange = new EventEmitter<ConnectionStateChange>();
  private readonly _onRecoveryNeeded = new EventEmitter<RecoveryEvent>();

  constructor(options: KiloBackendConnectorOptions);

  /** Establish SSE subscription. Idempotent; no-op if already Subscribed. */
  connect(): Promise<void>;

  /** Tear down SSE + SDK client; move to Disposed. */
  dispose(): void;

  /** Stream of normalized approvals for downstream consumers. */
  readonly onPendingApproval: Event<PendingApproval>;

  /** Stream of connection-state transitions (for status bar / diagnostics). */
  readonly onStateChange: Event<ConnectionStateChange>;

  /** Stream of recovery events (for observability). */
  readonly onRecoveryNeeded: Event<RecoveryEvent>;

  /** Current state snapshot. */
  getState(): ConnectionState;

  /**
   * Forward a decision to the backend.
   * @param requestId  SSE properties.id
   * @param sessionId  SSE properties.sessionID
   * @param directory  workspace scope (must match subscription)
   * @param reply      "once" | "always" | "reject"
   */
  replyToPermission(
    requestId: string,
    sessionId: string,
    directory: string,
    reply: PermissionReply
  ): Promise<ReplyResult>;

  /** Get the current reconnect attempt count (for diagnostics). */
  getReconnectAttempts(): number;

  /** Check if connector is in recovery mode. */
  isInRecoveryMode(): boolean;
}

export interface ReplyResult {
  ok: boolean;
  /** HTTP-ish status from backend (204 success, 404 expired, 401 auth, …). */
  status: number;
  error?: ReplyErrorKind;
}

export type ReplyErrorKind =
  | "not_found"      // requestID expired/invalid
  | "unauthorized"   // 401 – re-auth needed
  | "invalid"        // 400 – malformed reply
  | "transport"      // network/unknown
  | "duplicate";     // already replied (backend signal)

export interface RecoveryEvent {
  type: "started" | "completed" | "failed";
  recoveredCount?: number;
  error?: string;
  at: string;
}

export interface KiloClient {
  global: {
    event(opts: { directory: string; lastEventId?: string }): AsyncIterable<KiloSseEvent>;
  };
  permission: {
    /** List pending permissions for recovery. */
    list(opts: { directory: string }): Promise<PendingApproval[]>;
    reply(req: {
      path: { sessionId: string; requestId: string };
      body: { reply: PermissionReply; message?: string };
    }): Promise<ReplyResult>;
  };
}

export interface KiloClientFactory {
  create(port: number, auth: BackendAuth): KiloClient;
}

export interface KiloSseEvent {
  id: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface ReconnectPolicy {
  /** Get delay in ms for given attempt (0-indexed). */
  getDelay(attempt: number): number;
  /** Reset policy to initial state. */
  reset(): void;
  /** Get current attempt count. */
  getAttempt(): number;
}
```

### 4.3 ConfigManager types (`src/core/config/types.ts`)

```typescript
/** Auth tuple for Basic auth header `kilo:{password}` (never logged). */
export interface BackendAuth {
  port: number;
  password: string;   // 32-char hex; redacted in all logs
  pid?: number;
  version?: string;
}

/** Validated server.json. */
export interface KiloServerConfig {
  port: number;            // 1..65535
  password: string;        // 32-char hex
  version?: string;        // e.g. "7.4.11"
  pid?: number;            // positive int
  sourcePath: string;      // resolved absolute path
  readAt: string;          // ISO timestamp
}

/** Extension settings surfaced via package.json contributes.configuration. */
export interface ExtensionSettings {
  pollingIntervalMs: number;     // 1000..5000 (Telegram poll cadence)
  approvalTtlMs: number;           // default 30 * 60 * 1000
  allowedTelegramUserIds: string[];
  backendDiscovery: BackendDiscoveryMethod;
  connectionTimeoutMs: number;     // default 30000
  dedupeWindowMs: number;          // default 5000
}

export type BackendDiscoveryMethod =
  | "serverJson"          // preferred
  | "processScan";        // fallback

export interface WorktreeMapping {
  worktreePath: string;
  port: number;
  pid?: number;
}
```

### 4.4 ConfigManager class (`src/core/config/ConfigManager.ts`)

```typescript
import { Disposable } from "vscode";

export class ConfigManager implements ConfigProvider {
  /** Active backend port, throws if unavailable. */
  getActivePort(): Promise<number>;

  /** Auth credentials, throws if config missing/invalid. */
  getBackendAuth(): Promise<BackendAuth>;

  /** Full validated server config, throws if missing/invalid. */
  getConfig(): Promise<KiloServerConfig>;

  /** Typed extension settings (validated). */
  getSettings(): ExtensionSettings;

  /** Subscribe to server.json changes. */
  watchConfigChanges(listener: (cfg: KiloServerConfig) => void): Disposable;

  /** Resolve all known worktree→port mappings. */
  getWorktreeMappings(): Promise<WorktreeMapping[]>;

  /** Validate config NOW; throws on failure. */
  validateNow(): void;

  /** Get config file path for diagnostics. */
  getConfigPath(): string;
}

export interface ConfigValidationResult {
  ok: boolean;
  errors: string[];
}
```

---

## 5. Data Flow & Event Flow

### 5.1 Config discovery → auth → connect (startup)

```
[activate()]                         [ConfigManager]              [KiloBackendConnector]
     │                                     │                            │
     │ getActivePort()/getBackendAuth()    │                            │
     ├────────────────────────────────────▶│                            │
     │                                     │ read+validate server.json  │
     │                                     │ (cross-platform path)      │
     │◀──────────── BackendAuth ────────────┤                            │
     │                                     │                            │
     │ connect()                           │                            │
     ├─────────────────────────────────────────────────────────────────▶│
     │                                     │                            │ createKiloClient(port,auth)
     │                                     │                            │ global.event({directory})
     │                                     │                            │ → SSE GET /global/event
     │                                     │                            │ ◀── OPEN (with timeout)
     │◀──── onStateChange(Connecting → Subscribed) ──────────────────────┤
```

### 5.2 Permission event forward flow

```
 Kilo opencode backend                 KiloBackendConnector            ApprovalStateManager
 SSE: permission.asked ──▶            eventNormalizer()                register(pending)
 { id, type, properties }             → PendingApproval                  → HMAC + dedupe + TTL
                                            │ onPendingApproval                │
                                            ├────────────────────────────────▶│
                                            │                                 │
 (connector only normalizes + forwards; no business logic here)
```

### 5.3 Reply flow (decision in → backend)

```
TelegramProvider (Part 4) ─decision─▶ ApprovalStateManager (Part 2)
                                          validate + authorize
                                          └─▶ KiloBackendConnector.replyToPermission(
                                                  requestId, sessionId, directory, reply)
                                                    │ client.permission.reply({path, body})
                                                    ▼
                                              Kilo opencode backend
```

### 5.4 Recovery flow (reconnect / missed events)

```
 on disconnect ─▶ state=Reconnecting ─▶ backoff wait ─▶ getBackendAuth() (re-read server.json)
        │                                                              │
        │                                       re-create client + global.event({directory, lastEventId})
        │                                                              │
        └─ after SSE reconnect: client.permission.list({directory}) ──▶ recovery.ts
                  emit missing as PendingApproval (so Part 2 re-arms notifications)
```

---

## 6. Connection State Machine

**States:** `Idle → Discovering → Connecting → Subscribed ⇄ Recovering → Reconnecting → Degraded → Error → Disposed`

| From | Event / Trigger | To | Action |
|---|---|---|---|
| (none) | `connect()` called | Discovering | Begin auth/port resolution |
| Discovering | auth resolved, port present | Connecting | create client, open SSE with timeout |
| Discovering | config null / invalid | Error | emit error, await config watch |
| Connecting | SSE stream opened within timeout | Subscribed | emit `Subscribed`, reset backoff |
| Connecting | ECONNREFUSED / 401 / timeout | Reconnecting | schedule backoff retry |
| Subscribed | SSE closed / 4xx-5xx / heartbeat lost (10s no `server.connected`) | Recovering | emit event, prepare recovery |
| Recovering | list() returns, events replayed | Subscribed | complete recovery, reset state |
| Recovering | list() fails but SSE ok | Subscribed | log warning, skip recovery |
| Reconnecting | backoff elapsed, config valid | Connecting | retry connect |
| Reconnecting | repeated failures > 10 (or config permanently invalid) | Degraded | recovery polling only |
| Degraded | config recovers / SSE reopens | Recovering | attempt recovery |
| any | `dispose()` | Disposed | close SSE, cancel timers, dispose watchers |
| Error | valid config arrives via watch | Discovering | retry from scratch |

**Guards:** `connect()` idempotent; `dispose()` terminal; all transitions emit `onStateChange` and `onRecoveryNeeded`.

---

## 7. Message / Event Formats

### 7.1 `server.json` schema (cross-platform paths)

**CORRECTED paths per Kilo Code specification:**
- Linux/macOS: `~/.config/kilo/server.json` → `path.join(os.homedir(), ".config", "kilo", "server.json")`
- Windows: `%APPDATA%\kilo\server.json` → `path.join(process.env.APPDATA || process.env.USERPROFILE, "kilo", "server.json")`

```jsonc
{
  "port": 4097,                 // int 1..65535
  "password": "a1b2c3d4...",    // 32-char hex string
  "version": "7.4.11",          // optional semver-ish string
  "pid": 12345                  // optional positive int
}
```

### 7.2 `PendingApproval` (emitted downstream)
See §4.1. Key additions:
- `sequence`: monotonic counter for ordering, used in recovery dedupe

### 7.3 SSE event fields (raw)
```
id: <event-id>
event: permission.asked | permission.v2.asked
data: { "id": "...", "sessionID": "...", "permission"|"action": "...",
        "patterns"|"resources": [...], "metadata": {...}, "always": [...] }
```

### 7.4 Reply request
```
client.permission.reply({
  path: { sessionId, requestId },
  body: { reply: "once" | "always" | "reject" }
})
```

---

## 8. Error Handling & Retry Strategy

### 8.1 Error classes (`src/core/shared/errors.ts`)
- `ConfigNotFoundError` — server.json missing
- `ConfigValidationError` — schema violation
- `BackendUnreachableError` — ECONNREFUSED / timeout
- `BackendAuthError` — 401 (password rotated)
- `ReplyNotFoundError` — 404 (expired)
- `ReplyTransportError` — network failure
- `SdkVersionMismatchError` — version mismatch

### 8.2 Per-error handling
| Error | Handling |
|---|---|
| ConfigNotFound / Validation | Log WARN, state=`Error`, keep `watchConfigChanges` armed; retry on change. |
| BackendUnreachable | State=`Reconnecting`, apply backoff; connection timeout triggers retry. |
| BackendAuth (401) | Clear cached auth, re-read server.json, reconnect immediately. |
| ReplyNotFound (404) | Log INFO "approval already resolved/expired"; return `ok:false, not_found`. |
| ReplyTransport | Log WARN, optional single immediate retry; if down, return `transport`. |
| SdkVersionMismatch | Log ERROR with both versions; surface in status bar; continue best-effort. |
| SSE timeout | Cancel connection, emit `Error`, trigger reconnect with backoff. |

### 8.3 Retry / reconnect strategy
- **Backoff:** exponential `base=1000ms`, factor 2, cap `30000ms`. Full jitter.
- **Connection timeout:** 30s default (configurable via `connectionTimeoutMs` setting).
- **Max reconnection attempts:** unbounded for transient, but after `maxAttempts=10` → `Degraded`.
- **Last-Event-ID:** persist in memory + VS Code `globalState`; pass on reconnect.
- **Event dedupe:** ignore events with `eventId` seen within `dedupeWindowMs` (default 5s).
- **No crash guarantee:** all SSE/SDK awaits wrapped in try/catch.

---

## 9. Configuration Format

### 9.1 Extension settings (`package.json` → `contributes.configuration`)

```jsonc
"mkoAinotify": {
  "pollingIntervalMs":    { "type": "number", "default": 2000, "minimum": 1000, "maximum": 5000 },
  "approvalTtlMs":        { "type": "number", "default": 1800000 },
  "allowedTelegramUserIds": { "type": "array", "items": { "type": "string" }, "default": [] },
  "backendDiscovery":     { "type": "string", "enum": ["serverJson","processScan"], "default": "serverJson" },
  "connectionTimeoutMs":  { "type": "number", "default": 30000, "minimum": 5000, "maximum": 120000 },
  "dedupeWindowMs":       { "type": "number", "default": 5000, "minimum": 1000, "maximum": 30000 }
}
```

### 9.2 Backend discovery method
- `serverJson` (default): read `server.json` from correct cross-platform path.
- `processScan` (fallback): scan processes for `kilo serve --port <num>` if server.json absent.

### 9.3 Worktree mapping
Single global SSE connection with `directory` filter. Connector routes events by `sessionID` matching workspace. Worktree mappings used only for fallback port discovery.

---

## 10. Logging Strategy

- **Structured logger** via `src/core/shared/logger.ts`: `logger = logging.getLogger("mko-ainotify:connector")` / `:config`.
- **No secrets ever:** `password`, `BackendAuth.password` redacted as `"***"`.
- **Levels:** INFO for state transitions; WARN for recoverable errors; ERROR for schema/version failures; DEBUG for per-event (off by default).
- **Correlation:** attach `requestId`/`eventId` to approval-related logs.
- **Never use `print()`** — use the logger (project rule #12).

---

## 11. Testing Strategy

### 11.1 Unit tests (Vitest)
- `eventNormalizer.test.ts`: pure-function tests against fixtures; assert exact `PendingApproval` mapping.
- `serverJsonSchema.test.ts`: valid/invalid port, non-hex password, missing fields.
- `serverJsonReader.test.ts`: **correct cross-platform paths** (Win=%APPDATA%\kilo, Unix=~/.config/kilo).
- `settingsSchema.test.ts`: boundary values, defaults, invalid enum.
- `reconnectPolicy.test.ts`: deterministic policy with fake timers; assert backoff sequence + jitter bounds.
- `KiloBackendConnector.test.ts`: inject `FakeConfigReader` + `MockKiloClient`; test connect→Subscribed, disconnect→Reconnecting→Subscribed with Last-Event-ID replay, 401→re-auth, SSE timeout handling, event dedupe.
- `recovery.test.ts`: assert `/api/permission` list diff emits missing; stale entries skipped.

### 11.2 Test doubles
- `FakeConfigReader` — implements `ConfigProvider`, returns scripted configs.
- `MockKiloClient` — implements `KiloClient`; yields scripted events, records `reply()` calls.
- `InMemoryApprovalSink` — subscribes to `onPendingApproval` and collects.

---

## 12. Milestones (Part 1)

### M1 — Config discovery & validation foundation
- **Objective:** Correctly locate, read, validate, and watch `server.json` across platforms.
- **Deliverables:** All ConfigManager components, **correct cross-platform paths**.
- **Dependencies:** none.
- **Acceptance:** Unit tests pass; invalid config rejected; `watchConfigChanges` fires within 1s.

### M2 — Connector core + event normalization
- **Objective:** Connect via SDK, normalize events, expose `onPendingApproval`.
- **Deliverables:** `KiloBackendConnector`, `eventNormalizer`, `ConnectionStateMachine`, `KiloClientFactory` seam.
- **Dependencies:** M1.
- **Acceptance:** Both v1/v2 events normalized; malformed payloads handled gracefully.

### M3 — Reconnection, recovery & timeout handling
- **Objective:** Resilient SSE lifecycle: backoff+jitter, timeout, Last-Event-ID, recovery, dedupe.
- **Deliverables:** `reconnectPolicy`, `recovery`, error classes, heartbeat/liveness probe, dedupe logic.
- **Dependencies:** M2.
- **Acceptance:** Simulated disconnect→reconnect; missed events recovered; SSE timeout handled; no unhandled rejections.

### M4 — Reply path & status reporting
- **Objective:** `replyToPermission` maps to SDK, returns typed `ReplyResult`; state changes emitted.
- **Deliverables:** `replyToPermission` impl, `ReplyResult` mapping, `onStateChange`/`onRecoveryNeeded` wiring.
- **Dependencies:** M2, M3.
- **Acceptance:** Mock returns 204→`ok`; 404→`not_found`; timeout→`Reconnecting`; state transitions emitted.

### M5 — Integration smoke & worktree awareness
- **Objective:** End-to-end check against real/local backend; worktree port mapping.
- **Deliverables:** nock-based CI smoke test, `worktreeMapping.ts`, README setup notes.
- **Dependencies:** M3, M4.
- **Acceptance:** nock smoke passes; manual run confirms emit + reply.

---

## 13. Task Backlog (Granular)

1. **T1** Scaffold extension project: `package.json` (manifest + configuration), `tsconfig.json` (strict), `vitest.config.ts`.
2. **T2** Implement `src/core/shared/logger.ts` — structured logger + `redact()` helper.
3. **T3** Implement `src/core/shared/errors.ts` — 7 typed error classes.
4. **T4** Implement `src/core/config/types.ts` — interfaces and `BackendDiscoveryMethod` enum.
5. **T5** Implement `src/core/config/serverJsonSchema.ts` — Zod schema (port 1..65535, 32-char hex password).
6. **T6** Implement `src/core/config/settingsSchema.ts` — Zod schema with all settings including timeout/dedupe.
7. **T7** Implement `src/core/config/serverJsonReader.ts` — **CORRECTED cross-platform paths** using `process.env.APPDATA` for Windows.
8. **T8** Implement `src/core/config/ConfigProvider.ts` — interface with error semantics (throws on null).
9. **T9** Implement `src/core/config/ConfigManager.ts` — read/validate/watch; throws on invalid instead of returning null.
10. **T10** Implement `src/core/config/worktreeMapping.ts` — parse worktree configs → port mapping.
11. **T11** Write config unit tests: schema, **correct OS path variants**, `ConfigManager` watch/validate.
12. **T12** Implement `src/core/connector/types.ts` — enums, interfaces, `ReconnectPolicy`.
13. **T13** Implement `src/core/connector/eventNormalizer.ts` — pure function (v1 + v2).
14. **T14** Implement `src/core/connector/ConnectionStateMachine.ts` — state enum + transitions.
15. **T15** Implement `src/core/connector/reconnectPolicy.ts` — exponential backoff + full jitter + cap + maxAttempts.
16. **T16** Implement `src/core/connector/recovery.ts` — `/api/permission` list diff + dedupe logic.
17. **T17** Implement `src/core/connector/KiloBackendConnector.ts` — full implementation with **connection timeout**, **dedupe**, state machine.
18. **T18** Write connector unit tests: `eventNormalizer`, `reconnectPolicy`, **timeout handling**, `dedupe`, `KiloBackendConnector`.
19. **T19** Add test doubles: `FakeConfigReader`, `MockKiloClient`, `InMemoryApprovalSink`.
20. **T20** Add fixtures: valid/invalid configs, v1/v2 SSE samples.
21. **T21** Implement nock/msw-based CI integration smoke test.
22. **T22** Document manual validation steps in README.
23. **T23** Wire minimal `extension.ts` activate/deactivate to instantiate modules.

---

## Validation Scorecard

| Category | Score (/10) | Notes |
|----------|-------------|-------|
| **Architecture** | 8 | Clear separation, DI seams, state machine. Fixed cross-platform path error. Minor improvements to recovery flow needed. |
| **Implementation Risk** | 6 | SSE timeout missing (now fixed), dedupe logic incomplete (now fixed), config null handling clarified. |
| **Maintainability** | 9 | Well-structured modules, small files, clear interfaces. Tests planned. |
| **Production Readiness** | 7 | Good error handling, logging, retry strategy. Clock drift edge case remains for Part 3. |

### Top Issues Found & Resolved

- **[CRITICAL]** Cross-platform path error: Changed Windows path from `%USERPROFILE%\.config\kilo\server.json` to `%APPDATA%\kilo\server.json` - verified via Kilo Code documentation.
- **[HIGH]** Missing SSE connection timeout: Added `connectionTimeoutMs` setting and timeout handling in `KiloBackendConnector.connect()`.
- **[HIGH]** Missing event dedupe strategy: Added `dedupeWindowMs` setting and dedupe logic for events seen within window.
- **[HIGH]** ConfigProvider interface returned null: Changed to throw `ConfigNotFoundError` for cleaner error handling.
- **[MEDIUM]** Missing `onRecoveryNeeded` event: Added for observability during reconnect recovery phase.
- **[MEDIUM]** Contradictory worktree connection strategy: Clarified single global SSE with `sessionID` filtering.
- **[LOW]** Missing `ReplyErrorKind.duplicate`: Added to surface backend duplicate-reply signals.
- **[LOW]** Missing `sequence` field: Added monotonic counter for event ordering in recovery.

---

*Plan validated against: Kilo Code 7.4.11 / opencode backend API, VS Code Extension API (SecretStorage, FileSystemWatcher, EventEmitter), Context7 documentation.*