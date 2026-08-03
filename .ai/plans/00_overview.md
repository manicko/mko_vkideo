# Mko-AINotify — High-Level Architecture Overview

> **Top-level entry point.** This document is the orientation map for the five-part implementation plan. Deep contracts, folder layouts, milestones, and backlogs live in the part plans:
> - `plans/01_backend_connector.md` — **Part 1**: `KiloBackendConnector` + `ConfigManager` (connection/config foundation).
> - `plans/02_notification_provider.md` — **Part 2**: `NotificationProvider` abstraction + `TelegramProvider` (transport/presentation).
> - `plans/03_security_state.md` — **Part 3**: `SecurityModule` + `ApprovalStateManager` (crypto/state authority).
> - `plans/04_lifecycle_config_testing.md` — **Part 4**: bootstrap/orchestrator, `EventBus`, consolidated `ExtensionSettings`, error taxonomy, contract bible, roadmap M0–M5.
> - `research/validation_priority.md` — validated 5-module decomposition and the no-relay polling decision.

> **Scope rule:** This file must never introduce a contract that contradicts the part plans. Where a field differs between plans, the **Part 4 consolidated contract bible (§8) is authoritative**, and this document follows it.

---

## 1. Problem Summary & Solution Statement

**Problem.** Kilo Code 7.4.11 (with its embedded `opencode` backend) autonomously edits code but pauses whenever it needs execution approval for a potentially sensitive command. When the developer is away from their computer, no notification is raised, so the agent blocks indefinitely and long autonomous sessions lose their value. The developer wants to keep execution approvals **enabled** (not globally disabled) but needs to be asked and to answer **from a mobile phone in real time**, securely, without publicly exposing the desktop machine.

**Solution.** Mko-AINotify is a *companion* VS Code extension that observes Kilo's `opencode` backend and forwards approval requests to Telegram over the normal Bot API, then relays Approve/Reject/Approve-Once/Always-Allow decisions back — **without modifying Kilo Code source**. The bot runs entirely inside the VS Code extension host and uses `getUpdates` long-polling, so the desktop makes **only outbound HTTPS** to `api.telegram.org` (no public port, no cloud relay). Each approval's inline-keyboard `callback_data` carries a 42-byte HMAC-SHA256-signed envelope (truncated to 128-bit, base64url → 56 chars ≤ Telegram's 64-byte limit), giving authenticated, replay-protected, TTL-bounded remote decisions. The architecture is deliberately split into five dependency-inverted modules behind a thin orchestrator so Telegram can later be swapped for ntfy/Discord/Pushover.

---

## 2. High-Level Architecture

### 2.1 The five modules + orchestrator/glue

| Module | Part | Role |
|---|---|---|
| **`KiloBackendConnector`** | 1 | Owns the SSE/SDK lifecycle to the `opencode` backend; normalizes `permission.asked` into `PendingApproval`; executes `replyToPermission()`. |
| **`ConfigManager`** | 1 | Discovers/validates `server.json` (cross-platform), exposes typed `ExtensionSettings`, watches config changes. |
| **`TelegramProvider`** | 2 | Bot API HTTP client, message+keyboard construction, `getUpdates` poll loop, raw callback forwarding, message editing. Implements `NotificationProvider`. |
| **`SecurityModule`** | 3 | HMAC-SHA256 sign/verify of the `callback_data` envelope, `SecretStorage` of bot token + HMAC secret, handle→context map, rate limiting. |
| **`ApprovalStateManager`** | 3 | Registers pending approvals with TTL, deduplicates by `callback_query_id`, authorizes by `allowedTelegramUserIds`, expires stale approvals, produces `ResolvedDecision`. |
| **`Orchestrator` + `EventBus` + `extension.ts`** | 4 | Thin glue: instantiates modules in dependency-safe order, wires events, owns status bar / output channel / unified errors / metrics. |

### 2.2 Component diagram

```
                         ┌──────────────────────────────────────────────────────┐
                         │                  VS Code Extension Host               │
                         │                                                        │
   ┌───────────────┐     │   ┌────────────────────┐      ┌────────────────────┐  │
   │  VS Code UI   │     │   │  StatusBarController│      │   OutputChannel     │  │
   │ (status bar,  │◀───▶│   │  MetricsCollector  │      │  (structured logs)  │  │
   │  commands)    │     │   └────────────────────┘      └────────────────────┘  │
   └───────────────┘     │            │ events                                    │
                         │            ▼                                            │
                         │   ┌────────────────────────────────────────────────┐  │
                         │   │                Orchestrator (glue)              │  │
                         │   │   wires: connector↔provider↔approvalSM↔security │  │
                         │   │   via EventBus (connection.stateChange,         │  │
                         │   │        decision.inbound, decision.resolved,     │  │
                         │   │        permission.asked, config.changed)        │  │
                         │   └───────┬───────────────┬───────────────┬─────────┘ │
                         │           │               │               │           │
                         │  ┌────────▼──────┐ ┌──────▼───────┐ ┌─────▼─────────┐ │
                         │  │ KiloBackend-  │ │ ApprovalState │ │  Security-    │ │
                         │  │ Connector     │ │ Manager      │ │  Module       │ │
                         │  │ (+Config-     │ │              │ │  (SecretStorage│ │
                         │  │  Manager)     │ │              │ │   for token +  │ │
                         │  │               │ │              │ │   HMAC secret)│ │
                         │  └───┬───────┬───┘ └──────┬───────┘ └───────┬───────┘ │
                         │      │       │           │                 │          │
                         │      │       │     sign/verify +           │          │
                         │      │       │     handle map             │          │
                         │      │       └───────────┬─────────────────┘          │
                         │      │                   │ (SecuritySeam)             │
                         │      │          ┌────────▼─────────┐                  │
                         │      │          │ TelegramProvider │                  │
                         │      │          │ (Notification-   │                  │
                         │      │          │  Provider impl)  │                  │
                         │      │          └───┬─────────┬────┘                  │
                         └──────┼──────────────┘         │                       │
                                │                        │                       │
            SSE GET /global/event│              HTTPS (outbound only)            │
            client.permission.*  │              sendMessage / getUpdates         │
                                │                        │                       │
                                ▼                        ▼                       │
                 ┌──────────────────────────┐   ┌──────────────────────────────┐ │
                 │  Kilo Code 7.4.11        │   │   Telegram Bot API           │ │
                 │  opencode backend        │   │   api.telegram.org           │ │
                 │  (localhost, port from   │   └──────────────┬───────────────┘ │
                 │   server.json)           │                  │                  │
                 └──────────────────────────┘                  │                  │
                                                                ▼                  │
                                                         ┌──────────────┐          │
                                                         │ Mobile phone │          │
                                                         │ (user taps   │          │
                                                         │  Approve/    │          │
                                                         │  Reject …)   │          │
                                                         └──────────────┘          │
                                                                                  │
                                          NO inbound ports opened on desktop ◀───┘
```

**Key invariants (arrows):**
- Desktop → Kilo backend: outbound SSE subscribe + `permission.reply` (localhost only).
- Desktop → Telegram: outbound HTTPS only (`sendMessage`, `getUpdates`, `answerCallbackQuery`, `editMessageText`).
- Telegram → phone: normal Bot API push; phone → Telegram: user taps inline button (callback).
- Nothing opens a listening socket on the developer's machine.

---

## 3. Component Responsibilities & Boundaries

### 3.1 One-line responsibilities
- **`KiloBackendConnector`** — Connects to the `opencode` backend over SSE, normalizes `permission.asked`/`permission.v2.asked` into `PendingApproval`, and dispatches `replyToPermission()`.
- **`ConfigManager`** — Locates/validates `server.json` cross-platform, exposes typed `ExtensionSettings`, and watches for config rotation.
- **`TelegramProvider`** — Sends approval messages with inline keyboards, polls `getUpdates`, forwards raw `InboundDecision`, and edits the message after resolution.
- **`SecurityModule`** — Signs/verifies the 42-byte HMAC envelope, stores bot token + HMAC secret in `SecretStorage`, and persists the handle→context map with rate limiting.
- **`ApprovalStateManager`** — Registers pending approvals (TTL), deduplicates by `callback_query_id`, authorizes by user id, expires stale entries, and emits `ResolvedDecision`.
- **`Orchestrator`/`EventBus`** — Instantiates modules in order, wires approval + decision flows, routes cross-cutting signals, owns status bar / output / metrics / unified errors.

### 3.2 Responsibility boundaries (what each MUST NOT do)

| Module | Must NOT |
|---|---|
| `KiloBackendConnector` | Read/parse `server.json` (delegated to `ConfigManager`); validate HMAC or touch `SecretStorage` (`SecurityModule`); track TTL/dedupe/expire approvals (`ApprovalStateManager`); send Telegram or any notification (`TelegramProvider`); decide *who* may approve. |
| `ConfigManager` | Make SDK/SSE calls or call `permission.reply`; normalize permission events; validate HMACs or manage secrets; track pending approvals. |
| `TelegramProvider` | Generate, parse, or verify HMAC (uses opaque tokens from `SecurityModule`); authorize users *authoritatively* (only a fast pre-check); track TTL/`callback_query_id` dedupe/consume (Part 3); call `replyToPermission` (orchestrator does). |
| `SecurityModule` | Send Telegram messages or poll `getUpdates`; talk to the Kilo backend; own `ExtensionSettings` schema; make authorization *policy* (it exposes `getAuthorizedUserIds` + verifies signatures; `ApprovalStateManager` enforces reject-all/empty-list policy). |
| `ApprovalStateManager` | Perform crypto/HMAC directly (delegates to `SecurityModule`); send Telegram; call `replyToPermission` (orchestrator does); discover/read `server.json`. |
| `Orchestrator` | Reimplement any module's internals; hold secrets; own business logic beyond wiring + glue. |

---

## 4. Data Flow (permission.asked → Kilo proceeds)

```
Kilo opencode backend                VS Code Extension Host
─────────────────────                ───────────────────────────────────────────────
                                      ┌─ ConfigManager.getBackendAuth() ───────────┐
                                      │   (resolve port + password via server.json) │
                                      └────────────────────────────────────────────┘
SSE: permission.asked ──────────────▶ KiloBackendConnector.eventNormalizer()
{ id, type, properties }              → PendingApproval {requestId, sessionId,
                                        permission, patterns, metadata, directory,…}
                                              │ onPendingApproval
                                              ▼
                                        Orchestrator.toOutbound(pending)
                                          → OutboundApproval {requestId, sessionId,
                                             command, cwd, project, reason?,
                                             timestamp, ttlMs, directory}
                                              │
                            ┌─────────────────┴───────────────────┐
                            ▼                                     ▼
                  ApprovalStateManager.                  SecurityModule.signCallback
                    registerPending(outbound)            (requestId, action) ×4
                      → stores TTL + handle map            → 4 opaque ≤64B tokens
                            │                                     │
                            └───────────────┬─────────────────────┘
                                            ▼
                                  TelegramProvider.sendApprovalRequest(outbound)
                                    formatApprovalMessage(outbound, tokens)
                                    → sendMessage() with inline keyboard
                                            │ HTTPS (outbound)
                                            ▼
                                    Telegram servers ──▶ phone: "[⚠️] Approve / Reject / …"
                                            │
                                  user taps a button
                                            │ callback_query (rawCallbackData = token)
                                            ▼
                                  TelegramProvider.getUpdates → handleCallbackQuery
                                    1) fast allow-list check (from.id ∈ authorized)
                                    2) answerCallbackQuery()  (clear spinner)
                                    3) emit InboundDecision {callbackQueryId, userId,
                                                       rawCallbackData, chatId, messageId}
                                            │ onDecision
                                            ▼
                                  Orchestrator → ApprovalStateManager.validateAndConsume(d)
                                    • SecurityModule.verifyCallback(token)  (HMAC+nonce+expiry)
                                    • dedupe by callback_query_id
                                    • authorize by allowedTelegramUserIds
                                    → ResolvedDecision {status, action?, directory,…}
                                            │
                                ┌───────────┴────────────┐
                                ▼                        ▼
                  TelegramProvider.              KiloBackendConnector.replyToPermission(
                    applyResolvedDecision           requestId, sessionId, directory,
                    (editMessageText,               toPermissionReply(action))
                     remove keyboard)                     │ client.permission.reply()
                                │                        ▼
                                │                  Kilo opencode backend → continues
                                ▼                  execution
                          phone shows "[approved]"
```

---

## 5. Event Flow (EventBus)

The `EventBus` is a typed mediator (Part 4) decoupling cross-cutting signals. The five primary events used by the orchestrator/glue:

```
                         ┌───────────────────────── EventBus ─────────────────────────┐
                         │                                                              │
  (1) permission.asked ──▶ fired by KiloBackendConnector.onPendingApproval             │
       payload: PendingApproval                                                        │
                         │                                                              │
  (2) connection.stateChange ─▶ fired by KiloBackendConnector.onStateChange            │
       payload: ConnectionStateChange {from,to,reason?,at,reconnectAttempt?}            │
       consumed by: StatusBarController, MetricsCollector, Orchestrator (gate wiring)  │
                         │                                                              │
  (3) decision.inbound ──▶ fired by TelegramProvider.onDecision                         │
       payload: InboundDecision {callbackQueryId, userId, rawCallbackData, …}           │
       consumed by: ApprovalStateManager.validateAndConsume                            │
                         │                                                              │
  (4) decision.resolved ─▶ fired after ApprovalStateManager produces result           │
       payload: ResolvedDecision {callbackQueryId, requestId, sessionId,               │
                                  directory, status, displayText, action?}             │
       consumed by: TelegramProvider.applyResolvedDecision (edit), MetricsCollector   │
                         │                                                              │
  (5) config.changed ──▶ fired by ConfigManager.watchConfigChanges / settings watcher  │
       payload: KiloServerConfig | ExtensionSettings                                    │
       consumed by: Connector (re-auth/reconnect), PollingLoop (interval), Metrics     │
                         │                                                              │
                         └──────────────────────────────────────────────────────────────┘

   (An additional internal `health` signal is emitted by MetricsCollector/Orchestrator
    for the status bar; it is not part of the five core events above.)
```

**Wiring rule (Part 4):** approval processing is deferred until `connection.stateChange → Subscribed`; no `onPendingApproval` is consumed before then.

---

## 6. State Machines

### 6.1 (a) Connection state machine — `KiloBackendConnector`
States: `Idle → Discovering → Connecting → Subscribed ⇄ Reconnecting → Recovering → Degraded → Error → Disposed`

```
        connect()                       auth ok, port present
 Idle ───────────▶ Discovering ─────────────────────────────▶ Connecting
   ▲                   │                                        │  │
   │                   │ config null/invalid                   │  │ SSE opened (timeout ok)
   │                   ▼                                        │  ▼
   │               Error ◀── (valid config arrives via watch) ─┘  Subscribed
   │                   │                                        │  ▲
   │                   │                                        │  │ SSE closed / heartbeat lost
   │            dispose()│                                      │  ▼
   │                   ▼                                        │  Recovering
   │               Disposed ◀──────────────────────────────────┘  │  │ list() replayed
   │                                                              │  ▼
   │   ECONNREFUSED/401/timeout ──▶ Reconnecting                 │  Subscribed
   │                                     │ backoff elapsed        │
   │                                     ▼                        │ list() fails but SSE ok
   │                                 Connecting ◀────────────────┘  (warn, skip recovery)
   │                                     │ repeated fail > 10
   │                                     ▼
   │                                 Degraded ──(config recovers / SSE reopens)──▶ Recovering
   └──────────────────────────────────────────────────────────────────────────────
```
- Guards: `connect()` idempotent; `dispose()` terminal; every transition emits `connection.stateChange`.

### 6.1 (b) Approval lifecycle — `ApprovalStateManager`
```
                                   registerPending(outbound)
   PENDING ──────────────────────────────────────────────────────┐
     │  (TTL timer armed, handle map written)                     │
     │                                                            │
     │  TelegramProvider.sendApprovalRequest() OK                 │
     │  ApprovalStateManager.setSentReference(requestId, msgRef)  │
     ▼                                                           │
   SENT ──(notification delivered; still PENDING for decision)───┘
     │
     │  validateAndConsume(decision):
     │    • verifyCallback OK + authorized + not dup + not expired
     │    • action ∈ {approve,approve_once,always_allow}
     ▼
   CONSUMED ──▶ Orchestrator.replyToPermission(...) → backend proceeds
     │
     │  action == reject  (or authz failed / invalid)
     ▼
   REJECTED ──▶ edit "[rejected]" / "[unauthorized]" / "[invalid]"; no backend reply
     │
     │  TTL sweep (TtlSweeper) fires before any decision
     ▼
   EXPIRED ──▶ edit "[expired]"; no backend reply; handle forgotten
```
Terminal states: **`CONSUMED`**, **`REJECTED`**, **`EXPIRED`** (all one-way; entry removes TTL timer + handle).

### 6.1 (c) `callback_data` envelope lifecycle — `SecurityModule` + `ApprovalStateManager`
```
   signCallback(requestId, action)
        │ build 42B envelope (version|action|handle|nonce|expiry|hmac16)
        │ store HandleMap[handle] = {requestId,sessionId,directory,action}
        ▼
   [CREATED] token = base64url(envelope)  (56 chars ≤ 64)
        │ embedded as button callback_data by TelegramProvider
        ▼
   [ISSUED]  (sits in inline keyboard until user taps / TTL)
        │ user taps → Telegram returns callback_query.data = token
        ▼
   [RETURNED] TelegramProvider forwards raw token in InboundDecision
        │ ApprovalStateManager → SecurityModule.verifyCallback(token)
        ▼
   [VERIFIED]  status: valid (handle resolved, HMAC ok, nonce ok, not expired)
        │ dedupe by callback_query_id (DedupStore, first-wins)
        ▼
   [CONSUMED]  handle forgotten; decision applied/rejected
        │ OR verifyCallback → expired / tampered / unknown_handle / malformed / rate_limited
        ▼
   [REJECTED/EXP]  token dropped; message edited accordingly; handle cleaned
```
Lifecycle guarantees: handle is unique per `(requestId, action)`; once `CONSUMED`/`EXPIRED` the handle is forgotten so a replayed token resolves to `unknown_handle`.

---

## 7. Message Formats

### 7.1 `PendingApproval` shape (normalized from SSE — Part 1)
```
PendingApproval {
  eventId, requestId, sessionId,
  permission, patterns[], metadata{}, always[],
  directory, sourceType, receivedAt, sequence
}
```
(`metadata` carries `command`/`args` for bash; see contract bible note that `metadata.command` must exist.)

### 7.2 Telegram approval message text layout (HTML, all user fields escaped)
```
<b>⚠️ Kilo needs approval</b>
<b>Project:</b> {project}
<b>Command:</b> <code>{command}</code>
<b>Directory:</b> {cwd}
<b>Reason:</b> {reason}            (omitted if absent)
<b>Requested:</b> {timestamp}
<b>Expires in:</b> {expiresInSec}s
```
- `parse_mode = "HTML"`; total ≤ 4096 chars (long `command`/`cwd` truncated with ellipsis).

### 7.3 Inline-keyboard actions (one button per row)
```
[ ✅ Approve ]        callback_data = token.approve
[ ❌ Reject ]         callback_data = token.reject
[ ⏯️ Approve Once ]   callback_data = token.approve_once
[ 🔁 Always Allow ]   callback_data = token.always_allow
```
- `inline_keyboard: InlineKeyboardButton[][]` (4 rows). Only `callback_data` carries machine data; button `text` is human-readable. After resolution the keyboard is removed via `editMessageText`.

### 7.4 The 42-byte `callback_data` envelope (≤ 64-byte Telegram limit)
| Field | Bytes | Meaning |
|---|---|---|
| `version` | 1 | protocol version (`0x01`) for future envelope evolution |
| `action` | 1 | 0=approve, 1=reject, 2=approve_once, 3=always_allow |
| `handle` | 8 | opaque short handle → `requestId`/`sessionId`/`directory` (random) |
| `nonce` | 8 | random, bound into HMAC (replay protection) |
| `expiry` | 8 | Unix seconds UTC (TTL bound) |
| `hmac` | 16 | **truncated HMAC-SHA256** (128-bit, NIST SP 800-107) |
| **Total raw** | **42** | |

**Length proof (Telegram `callback_data` ≤ 64 bytes UTF-8):**
- Raw envelope = 42 bytes (fixed).
- base64url encoding ratio = 4 chars per 3 bytes, rounding **up** per group: `ceil(42 / 3) * 4 = 14 * 4 = 56` chars.
- 56 ≤ 64 ✅ (8 chars headroom preserved; no padding chars are emitted by base64url).
- Runtime guard `assertTokenLength(token)` throws if `Buffer.byteLength(token,"utf8") > 64`.
- Note: a full 32-byte HMAC would make the envelope 58 bytes → 78 base64 chars, which **exceeds** the 64-byte limit; hence the 16-byte truncation is mandatory.

---

## 8. Consolidated API Contracts (TypeScript signatures only)

> Canonical home: `src/core/shared/types.ts` (Part 4 contract bible). Shared types are re-exported from there; module-local type files import from it.

### 8.1 Shared types (canonical)
```typescript
// ---- enums / unions ----
export enum ConnectionState {
  Idle = "idle", Discovering = "discovering", Connecting = "connecting",
  Subscribed = "subscribed", Reconnecting = "reconnecting", Recovering = "recovering",
  Degraded = "degraded", Error = "error", Disposed = "disposed",
}
export type PermissionReply   = "once" | "always" | "reject";
export type ApprovalAction    = "approve" | "reject" | "approve_once" | "always_allow";
export type Decision          = ApprovalAction;                       // resolved user choice
export type DecisionStatus    = "approved" | "rejected" | "expired" | "invalid" | "unauthorized" | "error";
export type BackendDiscoveryMethod = "serverJson" | "processScan";
export type ProviderKind      = "telegram" | "discord" | "ntfy" | "pushover";
export type LogLevel          = "error" | "warn" | "info" | "debug";

// ---- backend-facing ----
export interface PendingApproval {
  eventId: string; requestId: string; sessionId: string;
  permission: string; patterns: string[]; metadata: Record<string, unknown>;
  always: string[]; directory: string;
  sourceType: "permission.asked" | "permission.v2.asked";
  receivedAt: string; sequence: number;
}
export interface ConnectionStateChange {
  from: ConnectionState; to: ConnectionState; reason?: string;
  at: string; reconnectAttempt?: number;
}
export interface BackendAuth {
  port: number; password: string; pid?: number; version?: string;
}
export interface KiloServerConfig {
  port: number; password: string; version?: string; pid?: number;
  sourcePath: string; readAt: string;
}
export interface ReplyResult { ok: boolean; status: number; error?: ReplyErrorKind; }
export type ReplyErrorKind = "not_found" | "unauthorized" | "invalid" | "transport" | "duplicate";

// ---- notification-facing ----
export interface OutboundApproval {
  requestId: string; sessionId: string; command: string; cwd: string;
  project: string; reason?: string; timestamp: string; ttlMs: number;
  directory: string;                                                   // added in contract bible
}
export interface MessageReference {
  providerId: string; chatId: number | string; messageId: number; correlationId?: string;
}
export interface InboundDecision {
  callbackQueryId: string; userId: number; rawCallbackData: string;
  chatId: number | string; messageId: number; receivedAt: string; requestId?: string;
}
export interface ResolvedDecision {
  callbackQueryId: string; requestId: string; sessionId: string; directory: string;
  status: DecisionStatus; displayText: string;
  action?: "approve" | "approve_once" | "always_allow" | "reject";
}
export interface EditOptions { removeKeyboard?: boolean; parseMode?: "HTML" | "MarkdownV2" | "Markdown"; }

// ---- security-facing ----
export interface HandleValue { requestId: string; sessionId: string; directory: string; action: ApprovalAction; }
export interface HandleMapEntry { handle: Uint8Array; value: HandleValue; createdAt: number; requestId: string; }
export type VerifyOutcome =
  | { status: "valid"; handle: Uint8Array; requestId: string; sessionId: string; directory: string; action: ApprovalAction; expiry: number; }
  | { status: "expired"; handle: Uint8Array; requestId: string; sessionId: string; directory: string; action: ApprovalAction; }
  | { status: "tampered" }
  | { status: "unknown_handle" }
  | { status: "malformed" }
  | { status: "rate_limited" };
export type CallbackToken = string;                                   // base64url envelope, ≤64B
export interface Envelope { version: number; action: number; handle: Uint8Array; nonce: Uint8Array; expiry: number; hmac: Uint8Array; }

// ---- config / DI seams ----
export interface ExtensionSettings {
  provider: ProviderKind; pollingIntervalMs: number; approvalTtlMs: number;
  allowedTelegramUserIds: string[]; backendDiscovery: BackendDiscoveryMethod;
  connectionTimeoutMs: number; dedupeWindowMs: number;
  dedupeTtlMs: number; clockSkewSec: number; sweepIntervalMs: number;
  secretGraceMs: number; auditRetentionDays: number;
  logLevel: LogLevel; statusBarDebounceMs: number;
}
export interface ConfigProvider {
  getActivePort(): Promise<number>;
  getBackendAuth(): Promise<BackendAuth>;
  getConfig(): Promise<KiloServerConfig>;
  watchConfigChanges(listener: (cfg: KiloServerConfig) => void): Disposable;
}
export interface SecuritySeam {
  getBotToken(): Promise<string>;
  getAuthorizedUserIds(): Promise<number[]>;
  signCallback(actionId: string, action: ApprovalAction): Promise<string>;   // actionId == requestId
}
export interface ContextProvider { getContext(requestId: string): Promise<{ sessionId: string; directory: string }>; }

// ---- unified error ----
export enum ExtensionErrorKind {
  ConfigNotFound = "config_not_found", ConfigInvalid = "config_invalid",
  BackendUnreachable = "backend_unreachable", BackendAuth = "backend_auth", SdkVersionMismatch = "sdk_version_mismatch",
  ReplyNotFound = "reply_not_found", ReplyTransport = "reply_transport", ReplyInvalid = "reply_invalid", ReplyDuplicate = "reply_duplicate",
  ProviderTokenMissing = "token_missing", ProviderUnauthorizedUser = "unauthorized_user", ProviderSendFailed = "send_failed",
  ProviderRateLimited = "telegram_rate_limit", ProviderEditFailed = "edit_failed", ProviderNotSupported = "not_supported", ProviderInvalidResponse = "invalid_response",
  SecuritySecretMissing = "secret_missing", SecuritySecretUnavailable = "secret_unavailable", SecurityRotationFailed = "rotation_failed",
  SecurityTokenMalformed = "token_malformed", CallbackInvalid = "callback_invalid", CallbackExpired = "callback_expired",
  CallbackTampered = "callback_tampered", CallbackUnknownHandle = "unknown_handle", CallbackRateLimited = "rate_limited",
  Internal = "internal",
}
export interface ExtensionError { kind: ExtensionErrorKind; message: string; cause?: unknown; }
```

### 8.2 `KiloBackendConnector` (Part 1) — public surface
```typescript
export class KiloBackendConnector implements Disposable {
  constructor(options: KiloBackendConnectorOptions);
  connect(): Promise<void>;
  dispose(): void;
  readonly onPendingApproval: Event<PendingApproval>;
  readonly onStateChange: Event<ConnectionStateChange>;
  readonly onRecoveryNeeded: Event<RecoveryEvent>;
  getState(): ConnectionState;
  replyToPermission(requestId: string, sessionId: string, directory: string, reply: PermissionReply): Promise<ReplyResult>;
  getReconnectAttempts(): number;
  isInRecoveryMode(): boolean;
}
export interface KiloBackendConnectorOptions {
  directory: string; config: ConfigProvider;
  clientFactory?: KiloClientFactory; reconnect?: ReconnectPolicy;
  connectionTimeoutMs?: number; dedupeWindowMs?: number;
}
```

### 8.3 `ConfigManager` (Part 1) — public surface
```typescript
export class ConfigManager implements ConfigProvider {
  getActivePort(): Promise<number>;
  getBackendAuth(): Promise<BackendAuth>;
  getConfig(): Promise<KiloServerConfig>;
  getSettings(): ExtensionSettings;
  watchConfigChanges(listener: (cfg: KiloServerConfig) => void): Disposable;
  getWorktreeMappings(): Promise<WorktreeMapping[]>;
  validateNow(): void;
  getConfigPath(): string;
}
```

### 8.4 `NotificationProvider` + `TelegramProvider` (Part 2) — public surface
```typescript
export interface NotificationProvider {
  readonly id: string;
  readonly isRunning: boolean;
  sendApprovalRequest(approval: OutboundApproval): Promise<MessageReference>;
  start(): Promise<void>;
  stop(): Promise<void>;
  onDecision(cb: (decision: InboundDecision) => void): Disposable;
  editMessage(reference: MessageReference, text: string, options?: EditOptions): Promise<void>;
}
export class TelegramProvider implements NotificationProvider {
  readonly id = "telegram";
  constructor(options: TelegramProviderOptions);
  initialize(): Promise<void>;
  sendApprovalRequest(approval: OutboundApproval): Promise<MessageReference>;
  start(): Promise<void>;
  stop(): Promise<void>;
  onDecision(cb: (decision: InboundDecision) => void): Disposable;
  editMessage(reference: MessageReference, text: string, options?: EditOptions): Promise<void>;
  get isRunning(): boolean;
  handleCallbackQuery(raw: RawCallbackQuery): Promise<void>;
  applyResolvedDecision(result: ResolvedDecision): Promise<void>;
}
export function createProvider(kind: ProviderKind, context: ProviderContext): NotificationProvider;
```

### 8.5 `SecurityModule` (Part 3) — public surface
```typescript
export class SecurityModule {
  constructor(options: { vault: SecretVault; handleMap: HandleMap; contextProvider: ContextProvider; rateLimiter: RateLimiter; });
  signCallback(requestId: string, action: ApprovalAction): Promise<string>;     // returns CallbackToken
  verifyCallback(token: string): Promise<VerifyOutcome>;
  getBotToken(): Promise<string>;
  setBotToken(token: string): Promise<void>;
  deleteBotToken(): Promise<void>;
  rotateSecret(): Promise<void>;
  forgetHandle(requestId: string): Promise<void>;
}
```

### 8.6 `ApprovalStateManager` (Part 3) — public surface
```typescript
export class ApprovalStateManager {
  constructor(options: { security: SecurityModule; pendingStore: PendingStore; dedupStore: DedupStore; ttlSweeper: TtlSweeper; auditLog: AuditLog; settings: ExtensionSettings; });
  registerPending(approval: OutboundApproval): Promise<void>;
  setSentReference(requestId: string, ref: MessageReference): Promise<void>;
  validateAndConsume(decision: InboundDecision): Promise<ResolvedDecision>;
  expireOld(): Promise<number>;
  getStatus(): ApprovalStatus;
  dispose(): void;
}
```

### 8.7 `Orchestrator` + `EventBus` (Part 4) — public surface
```typescript
export class Orchestrator implements Disposable {
  constructor(deps: { connector: KiloBackendConnector; provider: NotificationProvider; approvalSM: ApprovalStateManager; security: SecurityModule; configManager: ConfigManager; settings: ExtensionSettings; });
  start(): Promise<void>;
  dispose(): void;
}
export interface EventBus {
  fire<K extends keyof AppEvents>(type: K, payload: AppEvents[K]): void;
  on<K extends keyof AppEvents>(type: K, cb: (p: AppEvents[K]) => void): Disposable;
}
export interface AppEvents {
  "permission.asked": PendingApproval;
  "connection.stateChange": ConnectionStateChange;
  "decision.inbound": InboundDecision;
  "decision.resolved": ResolvedDecision;
  "config.changed": KiloServerConfig | ExtensionSettings;
  "health": HealthSignal;
}
```

---

## 9. Folder Structure (full VS Code extension TypeScript tree)

```
mko-ainotify/
├── .vscode/launch.json
├── package.json                      # manifest + contributes.configuration + commands + statusBarItem
├── tsconfig.json                     # strict, noUncheckedIndexedAccess
├── vitest.config.ts
├── eslint.config.js
├── README.md
├── src/
│   ├── extension.ts                  # activate()/deactivate() — thin glue
│   └── core/
│       ├── connector/
│       │   ├── KiloBackendConnector.ts
│       │   ├── ConnectionStateMachine.ts
│       │   ├── eventNormalizer.ts
│       │   ├── reconnectPolicy.ts
│       │   ├── recovery.ts
│       │   └── types.ts              # PendingApproval, ConnectionState (re-export from shared)
│       ├── config/
│       │   ├── ConfigManager.ts
│       │   ├── ConfigProvider.ts     # DI interface
│       │   ├── serverJsonReader.ts   # CORRECTED cross-platform paths
│       │   ├── serverJsonSchema.ts
│       │   ├── settingsSchema.ts
│       │   ├── worktreeMapping.ts
│       │   └── types.ts              # BackendAuth, KiloServerConfig, WorktreeMapping
│       ├── provider/
│       │   ├── NotificationProvider.ts   # interface + shared provider types
│       │   ├── BaseProvider.ts
│       │   ├── ProviderContext.ts
│       │   ├── TelegramProvider.ts
│       │   ├── TelegramApiClient.ts
│       │   ├── FetchTelegramClient.ts
│       │   ├── PollingLoop.ts
│       │   ├── messageFormatter.ts
│       │   ├── messageTemplates.ts
│       │   ├── backoff.ts
│       │   ├── ApprovalStore.ts
│       │   ├── createProvider.ts
│       │   └── adapters/
│       │       ├── NtfyProvider.ts
│       │       ├── DiscordProvider.ts
│       │       └── PushoverProvider.ts
│       ├── security/
│       │   ├── SecurityModule.ts
│       │   ├── SecretVault.ts
│       │   ├── HmacSigner.ts
│       │   ├── HandleMap.ts
│       │   ├── RateLimiter.ts
│       │   ├── envelope.ts           # 42-byte layout constants + assertTokenLength()
│       │   ├── types.ts
│       │   └── index.ts
│       ├── state/
│       │   ├── ApprovalStateManager.ts
│       │   ├── PendingStore.ts
│       │   ├── TtlSweeper.ts
│       │   ├── DedupStore.ts
│       │   ├── AuditLog.ts
│       │   ├── types.ts
│       │   └── index.ts
│       ├── orchestrator/
│       │   └── Orchestrator.ts
│       └── shared/
│           ├── logger.ts             # structured logger + redact()/redactToken()/redactPassword()
│           ├── errors.ts             # ExtensionErrorKind + ExtensionError + module error classes
│           ├── types.ts              # CONTRACT BIBLE (canonical re-exports)
│           ├── eventBus.ts
│           ├── metrics.ts            # MetricsCollector + MetricsSnapshot
│           ├── health.ts             # HealthSignal
│           └── test/doubles/FakeExtensionContext.ts
└── test/
    ├── fixtures/                     # server.json variants, SSE samples, Telegram transcripts
    ├── connector/                    # KiloBackendConnector, eventNormalizer, reconnectPolicy, recovery
    ├── config/                       # serverJsonReader (OS paths), schemas, ConfigManager
    ├── provider/                     # TelegramProvider, PollingLoop, messageFormatter, byteBudget, FakeProvider contract, ApprovalStore
    ├── security/                     # HmacSigner, SecretVault, HandleMap, RateLimiter, SecurityModule, AuditLog
    ├── state/                        # PendingStore, DedupStore, TtlSweeper, AuditLog, ApprovalStateManager
    ├── orchestrator/                 # EventBus, Orchestrator, StatusBar, Metrics, uncaught handlers
    └── integration/                  # MockKiloClient + FakeProvider full-loop, provider drain+resend, gated E2E_TELEGRAM smoke
```

---

## 10. Security Model Summary

- **Authentication / authorization.** Only Telegram user ids present in `allowedTelegramUserIds` (mirrored into `SecurityModule.getAuthorizedUserIds()`) may approve. `callback_query.from.id` is **server-authenticated by Telegram** and cannot be forged, so the allow-list check is authoritative. Empty `allowedTelegramUserIds` ⇒ **reject-all mode** (safe default) enforced by `ApprovalStateManager`.
- **Replay protection** (defense in depth):
  - 8-byte random **handle** (unique per `requestId`+`action`) → maps to routing context; once consumed/expired the handle is forgotten, so a replayed token resolves to `unknown_handle`.
  - 8-byte random **nonce** bound into the HMAC.
  - 8-byte **expiry** (Unix seconds) bounds token lifetime to `approvalTtlMs` (+ `clockSkewSec` tolerance).
  - **16-byte truncated HMAC-SHA256** (128-bit, NIST SP 800-107) over `version|action|handle|nonce|expiry`.
  - **`callback_query_id` dedupe** in `DedupStore` (first-wins, `dedupeTtlMs` TTL) prevents double-processing of the same tap.
  - `RateLimiter` caps HMAC verifications at 100/sec (sliding window) to block DoS.
- **Secrets (never logged).** Bot token + HMAC secret live **only** in VS Code `SecretStorage` (OS keyring), with an encrypted file fallback at `%APPDATA%\mko-ainotify\secrets.json.enc` (Windows) / `~/.config/mko-ainotify/secrets.json.enc` (Unix). `password` from `server.json` is file-only and redacted as `"***"`. `redactToken()`/`redactPassword()` guarantee no secret reaches logs or exceptions.
- **No local public exposure.** The extension makes **only outbound HTTPS** to `api.telegram.org`; `getUpdates` polling (no webhooks) means no listening socket, no port-forward, no cloud relay. Secret rotation (`rotateSecret`) keeps a previous secret during `secretGraceMs`.

---

## 11. Configuration Summary (`mkoAinotify.*` settings)

| Setting key | Type | Default | Range / Notes |
|---|---|---|---|
| `mkoAinotify.provider` | string enum | `"telegram"` | `telegram`\|`discord`\|`ntfy`\|`pushover` (others are stubs) |
| `mkoAinotify.pollingIntervalMs` | number | `2000` | 1000–5000 (Telegram poll cadence) |
| `mkoAinotify.approvalTtlMs` | number | `1800000` | ≥ 60000 (30 min default) |
| `mkoAinotify.allowedTelegramUserIds` | string[] | `[]` | empty ⇒ reject-all mode |
| `mkoAinotify.backendDiscovery` | string enum | `"serverJson"` | `serverJson`\|`processScan` |
| `mkoAinotify.connectionTimeoutMs` | number | `30000` | 5000–120000 |
| `mkoAinotify.dedupeWindowMs` | number | `5000` | ≥ 1000 (SSE event dedupe) |
| `mkoAinotify.dedupeTtlMs` | number | `30000` | ≥ 5000 (`callback_query_id` dedupe TTL) |
| `mkoAinotify.clockSkewSec` | number | `60` | 0–600 (envelope expiry tolerance) |
| `mkoAinotify.sweepIntervalMs` | number | `60000` | ≥ 5000 (TTL sweeper) |
| `mkoAinotify.secretGraceMs` | number | `300000` | ≥ 0 (HMAC rotation grace) |
| `mkoAinotify.auditRetentionDays` | number | `30` | ≥ 1 |
| `mkoAinotify.logLevel` | string enum | `"info"` | `error`\|`warn`\|`info`\|`debug` |
| `mkoAinotify.statusBarDebounceMs` | number | `1000` | 100–5000 |

Commands (Part 4): `mkoAinotify.setBotToken`, `mkoAinotify.rotateSecret`, `mkoAinotify.showAuditLog`, `mkoAinotify.flushQueue`.

---

## 12. Error Handling & Retry Summary

- **Unified taxonomy.** Every module throws/returns errors typed by `ExtensionErrorKind` (Part 4 §6.1): config, backend/SSE, reply, provider/Telegram, security/callback, and `Internal`. No module re-throws another module's operation.
- **Connector backoff.** SSE connect uses exponential backoff (base 1000ms, ×2, cap 30000ms, full jitter); connection timeout (default 30s) triggers a single retry then reconnect; `replyToPermission` gets one immediate retry, 401 ⇒ re-auth + reconnect, 404 ⇒ no retry (`not_found`). After >10 failed attempts → `Degraded`. `Last-Event-ID` + `dedupeWindowMs` prevent duplicate processing.
- **Telegram 429 backoff.** Honor `retry_after` header when present; else exponential 1→2→4→8→16→32s full jitter. `sendMessage` retries up to `maxSendRetries` (3) then queues (bounded 1000, TTL = `approvalTtlMs`); `getUpdates` keeps a single in-flight request and resumes from persisted offset. `answerCallbackQuery` has a 5s timeout + one retry and **never blocks** decision flow.
- **Crash isolation.** A global `uncaughtException`/`unhandledRejection` handler plus per-module circuit breakers ensure one failing subsystem (e.g. Telegram outage) degrades gracefully (status bar `Degraded`) without taking down the connector or the extension host. Every `await` in loops/handlers is wrapped; errors are logged, not thrown to the event loop.

---

## 13. Testing Strategy Summary

- **Unit tests (Vitest).** Per-module suites: `eventNormalizer` (v1+v2 exact mapping), config schemas + **correct cross-platform `server.json` paths**, `reconnectPolicy` (fake timers), `recovery`, `messageFormatter` (HTML escaping + 64-byte token boundary), `PollingLoop` (offset advance/persist, 429 backoff, stop cleanup), `HmacSigner` + **byte-length proof**, `SecretVault`, `HandleMap`, `RateLimiter`, `AuditLog`, `PendingStore`/`DedupStore`/`TtlSweeper`, `ApprovalStateManager`, `EventBus`/`Orchestrator`/`StatusBar`/`Metrics`/uncaught handlers.
- **`MockKiloClient` integration.** Full-loop tests drive `PendingApproval` → `OutboundApproval` → provider → `InboundDecision` → `ResolvedDecision` → `replyToPermission` using `MockKiloClient` + `FakeProvider`/`FakeTelegramApiClient`; covers reconnection, config hot-reload, provider drain+resend.
- **`FakeProvider` contract test.** A provider-agnostic suite proves `NotificationProvider` is neutral — run against `TelegramProvider`, `FakeProvider`, and the ntfy/Discord/Pushover stubs (expected `NotSupportedError`).
- **Gated live smoke.** `E2E_TELEGRAM=1` flag (default **off**, never in CI) for manual release validation only.
- **CI.** lint → typecheck → unit → integration → package. Hard-to-test concerns mitigated with `FakeExtensionContext` (Memento-backed `SecretStorage`), injected `Scheduler`/`now()` (clock skew), and network-error injection (offline/queue-TTL).

---

## 14. Future Extensibility

- **Alternate providers via `NotificationProvider`.** ntfy / Discord / Pushover stubs already implement the interface and are selectable via `mkoAinotify.provider` + `createProvider()`. Each new provider only needs to (a) implement `sendApprovalRequest`/`start`/`stop`/`onDecision`/`editMessage` and (b) consume opaque signed `callback_data` tokens from `SecuritySeam` — no changes to crypto, state, or backend modules. ntfy/Discord need their own callback-return channel; Pushover is one-way (`editMessage` throws `NotSupportedError`).
- **Local-only / self-hosted relay option.** Because the provider boundary is transport-agnostic, a `LocalRelayProvider` could replace Telegram with a LAN/self-hosted push server, keeping the same `OutboundApproval`→`InboundDecision` contract and the same HMAC envelope (the 64-byte budget is provider-relevant only for Telegram; a relay can carry the full token).
- **MCP server variant.** The orchestrator's `validateAndConsume` + `replyToPermission` logic could be exposed behind an MCP server (tools: `list_pending`, `approve`, `reject`) by adding an `McpProvider` that implements `NotificationProvider`-like inbound/outbound semantics, reusing `ApprovalStateManager` and `SecurityModule` unchanged.
- **Multi-instance.** The 8-byte handle gives 2⁶⁴ unique values for a single extension instance; for multi-instance deployments the handle-generation algorithm in `SecurityModule` is the only thing that must become collision-resistant (envelope already versioned for evolution).

---

## 15. Milestone Roadmap Summary (M0–M5)

> Detailed per-phase deliverables, dependencies, and acceptance live in `plans/04_lifecycle_config_testing.md` §10 and the part plans' milestone sections.

| Phase | Objective | Anchored in | Key deliverables |
|---|---|---|---|
| **M0 — Scaffold** | Extension skeleton + foundation types | Part 4 §11 (T-P4-01…07) | `package.json`, `tsconfig`, `vitest.config`, `shared/logger.ts`, `shared/errors.ts`, `shared/types.ts` (contract bible), `EventBus.ts`, `FakeExtensionContext`. |
| **M1 — Connect + Config** | Backend connection working | Part 1 (M1–M5) | `ConfigManager` (cross-platform `server.json`), `KiloBackendConnector` (SSE + normalize + reply + reconnect + recovery), `ExtensionSettings` schema. |
| **M2 — Notify** | Outbound notification path | Part 2 (M1–M6) + Part 4 T-P4-17…25 | `NotificationProvider` interface, `TelegramProvider`, `messageFormatter`, `PollingLoop`, `createProvider()` factory; orchestrator wires `PendingApproval`→`OutboundApproval`→`sendApprovalRequest`. |
| **M3 — Secure Approve** | Authenticated, replay-safe decisions | Part 3 (M1–M6) + Part 4 T-P4-26…33 | `SecurityModule` (sign/verify, `SecretStorage`, `HandleMap`, `RateLimiter`), `ApprovalStateManager` (register/validate/consume/expire), `ContextProvider` integration; full decision flow wired. |
| **M4 — Observability + Commands** | Status bar, logs, resilience | Part 4 §11 (T-P4-34…44) | `StatusBarController`, `MetricsCollector`, global handlers, `setBotToken`/`rotateSecret`/`showAuditLog`/`flushQueue` commands, config hot-reload, `deactivate()` cleanup. |
| **M5 — Provider Tests + QA** | Swap-safety + full coverage | Part 2 §11 + Part 4 §11 (T-P4-45…52) | `FakeProvider` contract suite, full-loop integration, gated `E2E_TELEGRAM` smoke, CI pipeline green, README complete. |

**Walking-skeleton principle:** M0 + M1 + the first M2 slice yields an end-to-end approval flow through `FakeProvider`, proving the architecture before Telegram integration.

---

*Canonical source of truth for contracts: `plans/04_lifecycle_config_testing.md` §8 (contract bible). Module internals, folder layouts, milestones, and backlogs: `plans/01`–`03`. Validated decomposition: `research/validation_priority.md`.*
