# Plan 02 — Notification Provider Layer & Telegram Bot (Part 2 of 5)

**Project:** Mko-AINotify — companion VS Code extension that forwards Kilo Code (opencode backend) permission approval requests to a mobile notification channel and relays decisions back.

**This part delivers:** The **NotificationProvider** abstraction (pluggable interface + `BaseProvider` + Telegram implementation) and the **TelegramProvider** (Bot API HTTP client, message construction, getUpdates polling loop, callback forwarding). It makes Telegram swappable for ntfy / Discord / Pushover later.

**Source research:** `part2_requirements.md`, `part2_architecture.md`, `part2_risks.md`, `validation_priority.md`, and the Part 1 contract `01_backend_connector.md`.

> **Dependency note (read first).** This part is a *transport + presentation* layer only. It does NOT own cryptography, pending-state, or backend replies. The following are consumed as interfaces (owned by other parts):
> - **Part 1 — KiloBackendConnector / ConfigManager:** type `PendingApproval` (§4.1 of plan 01) and extension settings (`pollingIntervalMs`, `approvalTtlMs`, `allowedTelegramUserIds`, etc.).
> - **Part 3 — SecurityModule:** `getBotToken()`, `getAuthorizedUserIds()`, `signCallback(actionId, action)` → opaque signed token (≤64 bytes UTF-8), `verifyCallback(token)` (used by Part 3, not here).
> - **Part 3 — ApprovalStateManager:** `consume(callbackQueryId)` for dedupe (used by Part 3, not here), and the PendingApproval→OutboundApproval normalization.
> Where Part 3 interfaces are not yet finalized, this plan pins the **contract shape** this part needs and flags the seam with `// DEPENDS-ON: Part3`.

---

## 1. Scope & Goals

### 1.1 What this part delivers
- **NotificationProvider interface** — a stable, provider-agnostic contract for two-way approval notifications.
- **BaseProvider** — shared lifecycle (`start`/`stop`/`isRunning`), `onDecision` registry, default no-op `editMessage`, error/backoff scaffolding, injected dependencies.
- **TelegramProvider** — concrete implementation that:
  - builds the approval message text + inline keyboard (4 buttons) from an `OutboundApproval` + pre-signed callback tokens,
  - sends via Bot API `sendMessage`,
  - runs a `getUpdates` long-poll loop (no webhooks, no public port),
  - parses `callback_query`, performs **fast local** user-ID authorization, then immediately `answerCallbackQuery` (clear spinner),
  - forwards a raw `InboundDecision` upward (verification/consume happens in Part 3),
  - edits the original message when the decision result comes back down,
  - retries sends and applies Telegram 429 backoff.
- **Message formatter** — pure function: `OutboundApproval` + signed tokens → `{ text, replyMarkup }`.
- **Polling loop** — isolated, injectable `getUpdates` pump with offset management and backoff.
- **Telegram HTTP client abstraction** — `TelegramApiClient` interface + `FetchTelegramClient` impl, injectable for `nock`/`msw` testing.
- **Provider stubs** — `NtfyProvider`, `DiscordProvider` implementing the interface as documented no-op/throw scaffolds (real impl is a future part).

### 1.2 Explicit out-of-scope (owned by other parts)
| Responsibility | Owning part/module |
|---|---|
| HMAC signing of `callback_data` (produces the signed token this part embeds) | Part 3 — SecurityModule |
| Bot-token / secret storage (SecretStorage) and retrieval | Part 3 — SecurityModule |
| Authorized-user list source of truth | Part 3 — SecurityModule (`getAuthorizedUserIds`) |
| `callback_data` byte-budget serialization / truncated-HMAC decision | Part 3 — SecurityModule |
| Pending-approval TTL, `callback_query_id` dedupe, consume/verify, action→requestId mapping | Part 3 — ApprovalStateManager |
| Converting `PendingApproval` → `OutboundApproval` (extract command/cwd/project/reason) | Part 3 — ApprovalStateManager / orchestrator |
| Backend reply (`client.permission.reply`) after a verified decision | Part 1 — KiloBackendConnector |
| Final authorization decision ("who may approve") | Part 3 + SecurityModule |
| VS Code status bar UI, extension `activate()`/`deactivate()` glue | Part 5 — extension glue |

This part **formats/sends messages, polls, and forwards raw callbacks upward**. It must never decrypt, verify HMAC, or mutate approval state. It MAY do a cheap `userID ∈ authorizedSet` check (the set is supplied by SecurityModule) to avoid forwarding obvious noise, but the authoritative authorization still happens in Part 3.

---

## 2. Module Responsibilities & Boundaries

### 2.1 TelegramProvider — OWNS
- Telegram Bot API **HTTP client** lifecycle (one client instance; `fetch`/axios only, outbound HTTPS to `api.telegram.org`).
- `sendMessage` with inline keyboard construction (delegating signing to SecurityModule for the 4 tokens).
- `getUpdates` **long-polling loop** (offset, `timeout`, `allowed_updates=["callback_query"]`).
- `answerCallbackQuery` (prompt acknowledgement to avoid stuck spinner).
- `editMessageText` for post-decision feedback.
- Tracking `(chat_id, message_id)` per sent notification so it can be edited later.
- **Fast** user-ID allow-list check (`from.id` ∈ authorized set) before forwarding.

### 2.2 TelegramProvider — DELEGATES
| Delegated to | What it provides | How consumed |
|---|---|---|
| **SecurityModule** | `getBotToken()`, `getAuthorizedUserIds()`, `signCallback(actionId, action) => string` (opaque ≤64-byte token) | Injected; called during `initialize()` and `sendApprovalRequest()`. |
| **ApprovalStateManager** (Part 3) | `consume(callbackQueryId)` dedupe, `verifyCallback`, `requestId→action` mapping | NOT called inside this part. The raw `InboundDecision` is emitted via `onDecision`; verification/consume happens in the orchestrator (Part 3/5). |
| **KiloBackendConnector** (Part 1) | `replyToPermission(...)` | NOT called inside this part. Decision delivery to backend is orchestrator responsibility. |

### 2.3 NotificationProvider interface — OWNS
- The abstract contract every provider implements: `id`, `sendApprovalRequest`, `start`, `stop`, `onDecision`, `editMessage`, `isRunning`.
- Provider-agnostic event/response normalization boundary.

### 2.4 BaseProvider — OWNS
- Common `isRunning` flag and `start`/`stop` guarding.
- `onDecision` listener registry (returns a `Disposable` for unsubscribe).
- Default `editMessage` (throws `NotSupportedError` for one-way providers like Pushover).
- Injected `ProviderContext` (logger, settings) wiring.

### 2.5 Dependency direction
```
Orchestrator (Part 3/5)
   │  holds NotificationProvider (concrete TelegramProvider)
   │  calls sendApprovalRequest(OutboundApproval)
   ▼
TelegramProvider ──uses──▶ SecurityModule (signCallback, getBotToken, getAuthorizedUserIds)   [Part 3]
   │  emits onDecision(InboundDecision)
   ▼
Orchestrator ──▶ ApprovalStateManager.consume/verify  [Part 3]
   │  returns ResolvedDecision
   ▼
TelegramProvider.editMessage(reference, text)   ← message feedback
   ▼
Orchestrator ──▶ KiloBackendConnector.replyToPermission(...)   [Part 1]
```
The provider depends **only** on `SecurityModule` (for tokens/identity) and on the injected `TelegramApiClient`/`PollingLoop` seams. It never imports `ApprovalStateManager` or `KiloBackendConnector` directly → keeps it swappable.

---

## 3. Folder Structure

Additions under the Part 1 extension layout (`mko-ainotify/`). Only Part 2 folders shown; the rest are as in plan 01.

```
mko-ainotify/
├── src/
│   ├── core/
│   │   ├── connector/            # (Part 1) unchanged
│   │   ├── config/               # (Part 1) unchanged; provides ExtensionSettings + ConfigProvider
│   │   ├── provider/
│   │   │   ├── NotificationProvider.ts     # interface + shared types (InboundDecision, OutboundApproval, MessageReference, ResolvedDecision)
│   │   │   ├── BaseProvider.ts              # shared lifecycle + onDecision registry + default editMessage
│   │   │   ├── ProviderContext.ts           # injected deps: logger, settings, SecurityModule seam
│   │   │   ├── TelegramProvider.ts          # main class (orchestrates client + loop + formatter)
│   │   │   ├── TelegramApiClient.ts         # interface (sendMessage, getUpdates, answerCallbackQuery, editMessageText, getMe)
│   │   │   ├── FetchTelegramClient.ts       # concrete fetch/axios implementation
│   │   │   ├── PollingLoop.ts               # isolated getUpdates pump (offset, backoff, dispatch)
│   │   │   ├── messageFormatter.ts          # pure fn: OutboundApproval + signed tokens → {text, replyMarkup}
│   │   │   ├── messageTemplates.ts          # text layout constants + inline keyboard builder
│   │   │   ├── telegramTypes.ts             # raw Bot API DTOs (Update, CallbackQuery, Message, etc.)
│   │   │   ├── backoff.ts                    # 429 + send-retry exponential backoff helper
│   │   │   ├── ApprovalStore.ts             # Part 2 local tracking: message_id, chat_id per requestId
│   │   │   └── adapters/
│   │   │       ├── NtfyProvider.ts          # stub implementing NotificationProvider
│   │   │       ├── DiscordProvider.ts       # stub implementing NotificationProvider
│   │   │       └── PushoverProvider.ts      # stub implementing NotificationProvider (one-way)
│   │   ├── security/               # (Part 3) SecurityModule — referenced, not implemented here
│   │   └── state/                  # (Part 3) ApprovalStateManager — referenced, not implemented here
│   └── test/
│       └── provider/
│           ├── TelegramProvider.test.ts
│           ├── PollingLoop.test.ts
│           ├── messageFormatter.test.ts
│           ├── byteBudget.test.ts           # 64-byte callback_data boundary
│           ├── FakeProvider.test.ts        # contract test for ANY provider
│           ├── ApprovalStore.test.ts       # message reference persistence test
│           ├── fixtures/
│           │   ├── getUpdates.stream.json   # scripted update_id sequence
│           │   ├── sendMessage.ok.json
│           │   └── telegram.error.429.json
│           └── doubles/
│               ├── FakeTelegramApiClient.ts
│               ├── FakePollingLoop.ts
│               └── FakeSecurityModule.ts
```

> **Naming/structure rule (project #8, #15):** small, single-responsibility files; no `any` (strict TS); all types in `*.ts`; pure functions (`messageFormatter`) kept separate from I/O (`FetchTelegramClient`, `PollingLoop`).

---

## 4. Interfaces / API Contracts (TypeScript)

### 4.1 Shared provider types (`src/core/provider/NotificationProvider.ts`)

```typescript
import { Disposable } from "vscode";

/** Stable action identifiers passed to SecurityModule.signCallback. */
export type ApprovalAction =
  | "approve"
  | "reject"
  | "approve_once"
  | "always_allow";

/**
 * Normalized outbound approval this provider renders + sends.
 * Produced UPSTREAM (Part 3 orchestrator) from Part 1 PendingApproval:
 *   requestId  <- PendingApproval.requestId
 *   sessionId  <- PendingApproval.sessionId
 *   command    <- PendingApproval.metadata.command (+ args joined)
 *   cwd        <- PendingApproval.directory (show in message)
 *   project    <- config/project name (Part 1 ConfigManager settings)
 *   reason     <- PendingApproval.metadata.reason | undefined
 *   timestamp  <- PendingApproval.receivedAt (ISO) or Date.now()
 *   ttlMs      <- ExtensionSettings.approvalTtlMs
 *   directory  <- PendingApproval.directory (required for reply routing via connector)
 * The provider MUST NOT compute this mapping itself.
 */
export interface OutboundApproval {
  requestId: string;
  sessionId: string;
  command: string;
  cwd: string;
  project: string;
  reason?: string;
  /** ISO-8601 timestamp of the request. */
  timestamp: string;
  /** TTL in milliseconds (from ExtensionSettings). */
  ttlMs: number;
  /** Workspace directory for reply routing (from PendingApproval.directory). */
  directory: string;
}

/** Opaque handle the provider keeps to later edit a sent message. */
export interface MessageReference {
  providerId: string;
  chatId: number | string;
  messageId: number;
  /** Provider-specific raw correlation id (e.g. callback_query_id once known). */
  correlationId?: string;
}

/**
 * RAW inbound decision forwarded UPWARD. The provider does NOT verify HMAC
 * or resolve the action — that is Part 3's job. It only packages what Telegram gave us.
 */
export interface InboundDecision {
  /** Telegram callback_query.id — primary dedupe key (Part 3 consumes it). */
  callbackQueryId: string;
  /** Telegram user id (CallbackQuery.from.id). */
  userId: number;
  /** Opaque signed callback_data payload (≤64 bytes UTF-8). NOT parsed here. */
  rawCallbackData: string;
  /** Chat + message to edit after the decision resolves. */
  chatId: number | string;
  messageId: number;
  /** ISO timestamp the tap was received by the extension. */
  receivedAt: string;
  /** requestId extracted from callback_data by SecurityModule.validate() - raw bytes passed through */
  requestId?: string;
}

/** Result the orchestrator (Part 3/5) pushes back DOWN to edit the message. */
export type DecisionStatus =
  | "approved"
  | "rejected"
  | "expired"
  | "invalid"      // bad signature / tampered
  | "unauthorized" // user not in allow-list
  | "error";

export interface ResolvedDecision {
  callbackQueryId: string;
  requestId: string;
  sessionId: string;
  directory: string;
  status: DecisionStatus;
  /** Human-readable one-liner for the edited message (already localized). */
  displayText: string;
  /** The chosen action, if known and valid. Maps to PermissionReply for backend. */
  action?: "approve" | "approve_once" | "always_allow" | "reject";
}

export interface EditOptions {
  /** Drop the inline keyboard after editing. Default true. */
  removeKeyboard?: boolean;
  /** Parse mode for the edited text. Default "HTML". */
  parseMode?: "HTML" | "MarkdownV2" | "Markdown";
}

/** The pluggable contract every notification provider implements. */
export interface NotificationProvider {
  /** Stable provider identifier, e.g. "telegram". */
  readonly id: string;

  /** True once start() has succeeded and polling/receiving is active. */
  readonly isRunning: boolean;

  /**
   * Send an approval request; resolve with a MessageReference used later for edits.
   * MUST throw a typed ProviderError on unrecoverable failure (after send retries exhausted).
   */
  sendApprovalRequest(approval: OutboundApproval): Promise<MessageReference>;

  /** Begin receiving responses (start polling loop / open socket). Idempotent. */
  start(): Promise<void>;

  /** Stop receiving; flush/cancel in-flight requests; resolve once fully stopped. */
  stop(): Promise<void>;

  /**
   * Register a decision listener. Fired with a RAW InboundDecision.
   * Returns a Disposable to unsubscribe.
   */
  onDecision(cb: (decision: InboundDecision) => void): Disposable;

  /**
   * Edit a previously sent message after a decision resolves.
   * One-way providers (Pushover) throw NotSupportedError.
   */
  editMessage(reference: MessageReference, text: string, options?: EditOptions): Promise<void>;
}
```

### 4.2 Injected context (`src/core/provider/ProviderContext.ts`)

```typescript
import { Logger } from "../shared/logger"; // from Part 1 shared/logger.ts
import type { ExtensionSettings } from "../config/types"; // Part 1 ConfigManager

/** Security seam — implemented by Part 3 SecurityModule. */
export interface SecuritySeam {
  /** Bot token from SecretStorage. Throws if missing. */
  getBotToken(): Promise<string>;
  /** Authorized Telegram user ids (for fast allow-list check). */
  getAuthorizedUserIds(): Promise<number[]>;
  /**
   * Produce an opaque signed callback_data token (≤64 bytes UTF-8).
   * actionId maps to OutboundApproval.requestId (globally unique).
   * // DEPENDS-ON: Part3 SecurityModule.signCallback
   */
  signCallback(actionId: string, action: ApprovalAction): Promise<string>;
}

export interface ProviderContext {
  logger: Logger;
  settings: ExtensionSettings;     // Part 1: pollingIntervalMs, approvalTtlMs, allowedTelegramUserIds...
  security: SecuritySeam;          // Part 3
}
```

### 4.3 TelegramProvider class (`src/core/provider/TelegramProvider.ts`)

```typescript
import { Disposable } from "vscode";
import { NotificationProvider, OutboundApproval, MessageReference,
         InboundDecision, ResolvedDecision, EditOptions } from "./NotificationProvider";
import { ProviderContext } from "./ProviderContext";
import { TelegramApiClient } from "./TelegramApiClient";
import { PollingLoop } from "./PollingLoop";
import { ApprovalStore } from "./ApprovalStore";

export interface TelegramProviderOptions {
  context: ProviderContext;
  /** Injectable HTTP client (FakeTelegramApiClient in tests). */
  apiClient?: TelegramApiClient;
  /** Injectable polling pump (FakePollingLoop in tests). */
  pollingLoop?: PollingLoop;
  /** Approval store for message references (inject for tests). */
  approvalStore?: ApprovalStore;
  /** getUpdates long-poll timeout seconds (default 25, Telegram max 50). */
  pollTimeoutSec?: number;
  /** Max send retries before throwing (default 3). */
  maxSendRetries?: number;
}

export class TelegramProvider implements NotificationProvider {
  readonly id = "telegram";

  constructor(options: TelegramProviderOptions);

  /** Validate token via getMe(); load authorized user ids; reset offset=0. Idempotent-safe. */
  initialize(): Promise<void>;

  sendApprovalRequest(approval: OutboundApproval): Promise<MessageReference>;
  start(): Promise<void>;
  stop(): Promise<void>;
  onDecision(cb: (decision: InboundDecision) => void): Disposable;
  editMessage(reference: MessageReference, text: string, options?: EditOptions): Promise<void>;

  get isRunning(): boolean;

  /**
   * Called by PollingLoop for each callback_query. Internal; exposed for tests.
   * 1) fast user-id allow-list check
   * 2) answerCallbackQuery (clear spinner) - non-blocking
   * 3) emit InboundDecision via onDecision
   * (verification/consume happens upstream)
   */
  handleCallbackQuery(raw: RawCallbackQuery): Promise<void>;

  /** Called by orchestrator after Part 3 consume/verify. Edits the message. */
  applyResolvedDecision(result: ResolvedDecision): Promise<void>;
}
```

### 4.4 Telegram API client (`src/core/provider/TelegramApiClient.ts`)

```typescript
import { OutboundApproval /* not used here, kept for symmetry */ } from "./NotificationProvider";

export interface TelegramSendMessageParams {
  chat_id: number | string;
  text: string;
  reply_markup?: InlineKeyboardMarkup;
  parse_mode?: "HTML" | "MarkdownV2" | "Markdown";
  message_thread_id?: number;
}

export interface TelegramGetUpdatesParams {
  offset?: number;
  limit?: number;       // 1..100
  timeout?: number;     // seconds
  allowed_updates?: string[];
}

export interface TelegramAnswerCallbackParams {
  callback_query_id: string;
  text?: string;
  show_alert?: boolean;
  cache_time?: number;
}

export interface TelegramEditMessageParams {
  chat_id: number | string;
  message_id: number;
  text: string;
  reply_markup?: InlineKeyboardMarkup;
  parse_mode?: "HTML" | "MarkdownV2" | "Markdown";
}

export interface TelegramApiClient {
  getMe(): Promise<{ id: number; username: string; is_bot: boolean }>;
  sendMessage(params: TelegramSendMessageParams): Promise<{ message_id: number; chat: { id: number | string } }>;
  getUpdates(params: TelegramGetUpdatesParams): Promise<TelegramUpdate[]>;
  answerCallbackQuery(params: TelegramAnswerCallbackParams): Promise<boolean>;
  editMessageText(params: TelegramEditMessageParams): Promise<boolean>;
}

/** Raw Bot API DTOs (subset). See telegramTypes.ts for full definitions. */
export interface TelegramUpdate { update_id: number; callback_query?: RawCallbackQuery; }
export interface RawCallbackQuery {
  id: string;
  from: { id: number; username?: string };
  data?: string;          // signed callback_data (≤64 bytes)
  message?: { message_id: number; chat: { id: number | string } };
}
export interface InlineKeyboardButton { text: string; callback_data?: string; url?: string; }
export interface InlineKeyboardMarkup { inline_keyboard: InlineKeyboardButton[][] }
```

### 4.5 PollingLoop (`src/core/provider/PollingLoop.ts`)

```typescript
import { Disposable } from "vscode";
import { TelegramApiClient, TelegramUpdate } from "./TelegramApiClient";

export type CallbackQueryHandler = (raw: RawCallbackQuery) => Promise<void>;

export interface PollingLoopOptions {
  client: TelegramApiClient;
  handler: CallbackQueryHandler;
  /** Polling cadence between batches (ms). Default from ExtensionSettings.pollingIntervalMs. */
  intervalMs: number;
  /** getUpdates long-poll timeout (sec). Default 25. */
  pollTimeoutSec: number;
  /** Persisted offset loader/saver (extension globalState). */
  offsetStore: OffsetStore;
  /** AbortSignal to cancel the loop. */
  signal: AbortSignal;
  /** Injectable scheduler (fake timers in tests). */
  scheduler?: Scheduler;
}

export interface OffsetStore {
  load(): Promise<number>;
  save(offset: number): Promise<void>;
}

export interface Scheduler {
  setTimeout(fn: () => void, ms: number): Disposable;
  now(): number;
}

export class PollingLoop {
  constructor(options: PollingLoopOptions);
  /** Start pumping getUpdates. Resolves once first batch scheduled. */
  start(): Promise<void>;
  /** Cancel current request, stop scheduling, flush. */
  stop(): Promise<void>;
  get isRunning(): boolean;
}
```

### 4.6 Approval Store (`src/core/provider/ApprovalStore.ts`) - NEW

```typescript
import { MessageReference } from "./NotificationProvider";

/**
 * In-memory store for sent approval message references.
 * Persists to VS Code globalState on changes for recovery after restart.
 */
export interface ApprovalStore {
  /** Store reference keyed by requestId. */
  set(requestId: string, ref: MessageReference): Promise<void>;
  /** Retrieve reference by requestId. */
  get(requestId: string): Promise<MessageReference | undefined>;
  /** Delete reference by requestId. */
  delete(requestId: string): Promise<void>;
  /** List all pending requestIds. */
  listPending(): Promise<string[]>;
  /** Cleanup stale entries older than ttlMs. */
  cleanup(ttlMs: number): Promise<number>;
}

export class GlobalStateApprovalStore implements ApprovalStore {
  constructor(private readonly globalState: vscode.Memento);
  // ... implementation
}
```

### 4.7 Message formatter & templates (`messageFormatter.ts`, `messageTemplates.ts`)

```typescript
import { OutboundApproval } from "./NotificationProvider";
import { InlineKeyboardMarkup, InlineKeyboardButton } from "./TelegramApiClient";

/** Four pre-signed opaque tokens supplied by SecurityModule.signCallback. */
export interface SignedActionTokens {
  approve: string;
  reject: string;
  approve_once: string;
  always_allow: string;
}

export interface RenderedMessage {
  text: string;
  replyMarkup: InlineKeyboardMarkup;
  parseMode: "HTML";
}

/**
 * PURE function. Combines an OutboundApproval with four signed tokens into a
 * Telegram-ready message. No I/O, no crypto, deterministic given inputs.
 */
export function formatApprovalMessage(
  approval: OutboundApproval,
  tokens: SignedActionTokens
): RenderedMessage;

/** Build the post-decision status text for editMessageText. */
export function formatDecisionText(approval: OutboundApproval, status: DecisionStatus, displayText: string): string;
```

### 4.8 Stub providers (`adapters/*.ts`)

```typescript
export class NtfyProvider implements NotificationProvider {
  readonly id = "ntfy";
  // Stub: throws NotSupportedError on sendApprovalRequest / start until future part.
}
export class DiscordProvider implements NotificationProvider {
  readonly id = "discord";
  // Stub: throws NotSupportedError until future part.
}
export class PushoverProvider implements NotificationProvider {
  readonly id = "pushover";
  // Stub: one-way — editMessage throws NotSupportedError; sendApprovalRequest throws NotSupportedError.
}
```
> The stubs exist so the **provider-selection factory** (Part 5) and **FakeProvider contract tests** compile and run today; real behavior is a later part. Each stub documents its planned response mechanism in a header comment (see §6 comparison table from research).

### 4.9 Shared error types (extend Part 1 `errors.ts`)
```typescript
export class ProviderError extends Error { constructor(public kind: ProviderErrorKind, message: string, public cause?: unknown) { super(message); } }
export type ProviderErrorKind =
  | "token_missing"        // SecurityModule.getBotToken failed
  | "unauthorized_user"     // from.id not in allow-list (still forwarded as InboundDecision? No — dropped silently, see §5)
  | "send_failed"          // retries exhausted
  | "rate_limited"         // 429 after backoff ceiling
  | "edit_failed"          // editMessageText error
  | "not_supported"        // one-way provider
  | "invalid_response";    // malformed Telegram payload
```

---

## 5. Data Flow & Event Flow

### 5.1 Outbound (send) — PendingApproval arrives, notification sent

```
[Part 3 Orchestrator]                         [TelegramProvider]                [SecurityModule Part3]
  normalize PendingApproval→OutboundApproval
  (extract command/cwd/project/reason)                │
        │ OutboundApproval                            │
        ├────────────────────────────────────────────▶│
        │                                             │ for each action in
        │                                             │ {approve,reject,approve_once,always_allow}:
        │                                             ├──── signCallback(requestId, action) ──▶│
        │                                             │◀───────── signed token (≤64B) ─────────┤
        │                                             │
        │                       formatApprovalMessage(approval, tokens)
        │                       → {text, replyMarkup}
        │                                             │
        │                               sendMessage(chat_id, text, replyMarkup)
        │                               ───────────▶ FetchTelegramClient ─▶ api.telegram.org
        │                               ◀─────────── {message_id, chat}
        │◀──────────── MessageReference {chatId,messageId} ──────────────┤
        │ (store ref in ApprovalStore keyed by requestId for later edit)
```

### 5.2 Inbound (callback) — user taps, raw decision forwarded up

```
 Telegram servers                PollingLoop                TelegramProvider.handleCallbackQuery
 SSE: callback_query ──▶  getUpdates (offset)  ─▶  callback_query(raw)
                                                        │
                                                        1) fast allow-list check:
                                                         raw.from.id ∈ authorizedUserIds ?
                                                        ├─ NO  → answerCallbackQuery("[DENIED] not allowed")
                                                        │         log WARN, DROP (no forward)
                                                        └─ YES → answerCallbackQuery()  ← clears spinner (<10s)
                                                        2) emit InboundDecision {
                                                           callbackQueryId, userId,
                                                           rawCallbackData, chatId, messageId }
                                                        via onDecision ──▶ Orchestrator
```

### 5.3 Decision resolves — message edited, backend notified (downstream of this part)

```
 Orchestrator (Part 3/5)                 TelegramProvider
   verifyCallback + consume(callbackQueryId)   │
   → ResolvedDecision {status, displayText, requestId, sessionId}
        │ applyResolvedDecision(result)        │
        ├────────────────────────────────────▶│
        │                                   editMessageText(chatId, messageId,
        │                                     formatDecisionText(...), removeKeyboard=true)
        │
        └─▶ KiloBackendConnector.replyToPermission(requestId, sessionId, directory, reply)   [Part 1]
              │ client.permission.reply({path, body})
              ▼
          Kilo opencode backend
              continues execution
```
> The provider only performs `applyResolvedDecision` (edit). The backend `replyToPermission` call is the orchestrator's job (Part 1/3/5), NOT the provider's.

### 5.4 Event/state flow summary
```
PendingApproval ─▶ OutboundApproval ─▶ sendMessage ─▶ user taps
   ─▶ getUpdates ─▶ answerCallbackQuery ─▶ InboundDecision(up)
   ─▶ [verify/consume in Part 3] ─▶ ResolvedDecision(down)
   ─▶ editMessageText ─▶ [replyToPermission in Part 1]
```

---

## 6. Message Formats

### 6.1 Telegram message text layout (HTML, escaped)
Single message per approval. Layout (constant template in `messageTemplates.ts`):

```
<b>⚠️ Kilo needs approval</b>
<b>Project:</b> {project}
<b>Command:</b> <code>{command}</code>
<b>Directory:</b> {cwd}
<b>Reason:</b> {reason}            (omitted if absent)
<b>Requested:</b> {timestamp}
<b>Expires in:</b> {expiresInSec}s
```

- All user-controlled fields (`command`, `cwd`, `project`, `reason`) **HTML-escaped** before interpolation (prevents Telegram parse errors / injection). Use a shared `escapeHtml()` in `messageFormatter`.
- `parse_mode = "HTML"`.
- Keep total text ≤ 4096 chars (Telegram limit); truncate `command`/`cwd` with ellipsis if needed (罕见 but guard in formatter).

### 6.2 Inline keyboard layout
4 buttons, each its own row (clear tap targets on mobile):

```
[ ✅ Approve ]            callback_data = tokens.approve
[ ❌ Reject ]             callback_data = tokens.reject
[ ⏯️ Approve Once ]       callback_data = tokens.approve_once
[ 🔁 Always Allow ]       callback_data = tokens.always_allow
```

- `inline_keyboard: InlineKeyboardButton[][]` (1 button per inner array = 4 rows).
- Button `text` is human-readable; the **only** machine data is `callback_data` (the signed token).
- After a decision, `editMessageText` is called with `reply_markup` omitted (keyboard removed).

### 6.3 callback_data envelope — 64-byte budget (FIXED)

Telegram hard limit: **`callback_data` ≤ 64 bytes UTF-8** (official Bot API docs). The signed token is produced by **SecurityModule (Part 3)**, but this plan pins the *constraint* and the *corrected math* because the research contains an arithmetic error that must be resolved before implementation.

**Research statement (part2_architecture/risks):** `base64url(HMAC(32) + nonce(8) + expiry(8) + action_id(remaining))` ≤ 64 bytes.
**Correction:** base64url inflates bytes by ~33% (4/3). `base64url(N bytes) = ceil(4N/3)` chars. For the result to fit **64 chars**, the raw binary envelope must be **≤ 48 bytes**. But `HMAC(32)+nonce(8)+expiry(8) = 48 bytes` already = 64 base64 chars, leaving **0 bytes** for `action_id`/`requestId`. The research's "action_id(remaining)" is therefore **impossible** with a 32-byte HMAC. This is tracked as risk **R12**.

**Required envelope (owned by SecurityModule, documented here for the boundary):**
| Field | Bytes | Notes |
|---|---|---|
| version | 1 | protocol version (allows future envelope evolution) |
| action | 1 | 0=approve,1=reject,2=approve_once,3=always_allow |
| handle | 8 | **opaque short handle → requestId**, generated at sign time by Part 3 |
| nonce | 8 | random (for replay protection) |
| expiry | 8 | Unix seconds (or 4 bytes if NIST allows; 8 for safety) |
| hmac | 16 | **truncated HMAC-SHA256 (16 bytes)** — ≥128-bit security (NIST SP 800-107) |
| **Total raw** | **42** | base64url(42) = 56 chars ≤ 64 ✅ (headroom preserved) |

**Security Note:** Truncated HMAC (16 bytes) provides 128-bit collision resistance per NIST SP 800-107. This is acceptable for this use case. The 8-byte handle provides 2^64 unique values which is sufficient for a single extension instance. For multi-instance deployments, the handle generation in SecurityModule must use a collision-resistant algorithm.

**Decision for Part 3 (mandated):** SecurityModule MUST use the 42-byte envelope above (version+action+handle+nonce+expiry+hmac=16). The provider only consumes the **opaque string** and asserts `Buffer.byteLength(token,"utf8") <= 64`; it never parses it.

**Handle resolution:** The SecurityModule maintains a handle→requestId mapping in memory, keyed by the 8-byte handle. This mapping MUST survive extension restarts (persist to globalState). When the provider receives a callback, SecurityModule.validate() looks up the handle to recover requestId and sessionId.

**Test boundary (§11):** `byteBudget.test.ts` asserts every signed token from `FakeSecurityModule`/`SecurityModule` is `≤64` bytes UTF-8, and that 4 distinct actions produce 4 distinct tokens.

### 6.4 Provider comparison (from research, for stub design)

| Provider | Response mechanism | editMessage | Notes |
|---|---|---|---|
| Telegram | inline_keyboard callback_query | yes | 64-byte callback_data limit |
| ntfy | action buttons → HTTP POST callback | no (cloud relay) | needs HTTPS endpoint; port exposure (out of scope for no-public-port goal) |
| Discord | button components + interaction | yes | needs bot in server; webhook or polling |
| Pushover | URL buttons only | no (one-way) | user taps link; no instant response |

---

## 7. Polling Design

### 7.1 getUpdates loop (long poll)
- Endpoint (via `FetchTelegramClient`): `https://api.telegram.org/bot<token>/getUpdates`.
- Params: `offset` (persisted), `limit=100`, `timeout=pollTimeoutSec` (default 25, max 50), `allowed_updates=["callback_query"]`.
- **Single in-flight request** at a time (no overlapping getUpdates — avoids duplicate updates per official docs).
- After a batch: `offset = max(update_id) + 1`; persist via `offsetStore.save(offset)`.
- `offsetStore` backed by VS Code `globalState` (survives extension restart; prevents reprocessing old updates).
- Loop cadence between batches: `intervalMs` (from `ExtensionSettings.pollingIntervalMs`, default 2000), via injected `Scheduler` (fake timers in tests).

### 7.2 Offset management
- On `initialize()`: `offset = await offsetStore.load()` (default 0).
- **Bootstrap guard:** never call `setWebhook`; on init optionally call `getWebhookInfo` and WARN if `url` is set (would starve getUpdates) — risk R11 mitigation.
- Each processed `update_id` advances offset even if the inner handler throws (so a poison update can't block the loop forever — but log + surface).

### 7.3 Backoff on 429 / network error
- On HTTP 429: read `retry_after` header if present, else use `backoff.ts` exponential: 1s→2s→4s→8s→16s→32s (max), full jitter. Loop pauses scheduling, then resumes.
- On `ECONNREFUSED`/`ETIMEDOUT`/fetch abort: same backoff; emit connectivity-lost log; after recovery, resume from persisted offset.
- Cap consecutive backoff attempts; after a long outage, log `degraded` and keep retrying with ceiling (do not crash).

### 7.4 Queueing unsent notifications
- `sendApprovalRequest` failures (network down) are retried up to `maxSendRetries` (default 3) with backoff, then the message is placed in an **in-memory bounded queue** (`max 1000`, LRU eviction, TTL = `approvalTtlMs`) and a WARN logged. On connectivity recovery the queue is flushed (best-effort re-send). If approval already expired (TTL passed) the queued item is dropped silently.
- Memory bound ≤ 50MB (per NFR); queue capped accordingly.

### 7.5 Stop / cleanup
- `stop()` aborts the `AbortSignal`, cancels the scheduled next tick (`Scheduler` disposable), awaits in-flight `getUpdates`/send to settle (with a short grace timeout ~2s), then sets `isRunning=false`.
- `deactivate()` (Part 5) MUST call `stop()` before disposal to avoid leaking HTTP sockets.
- Never call `deleteWebhook` (we never set one); just stop polling.

### 7.6 Concurrent approval deduplication
- **CRITICAL**: The 8-byte handle in callback_data MUST be unique per requestId to enable proper deduplication.
- Part 3 ApprovalStateManager tracks `callback_query_id` with 30-second TTL for dedupe.
- The first valid response to a `requestId` wins; subsequent responses are rejected with `[ALREADY_PROCESSED]` toast.

---

## 8. Error Handling & Retry Strategy

### 8.1 Per-error-class handling

| Error class | Detection | Handling |
|---|---|---|
| `token_missing` | `SecurityModule.getBotToken()` throws | `initialize()` rejects; status-bar error; no polling. |
| `invalid_response` (malformed Update) | DTO parse fails in `TelegramApiClient` | Skip that update, log ERROR with redacted payload, advance offset, continue. |
| `rate_limited` (HTTP 429) | status 429 | Backoff per §7.3; pause loop; resume. |
| network (`ECONNREFUSED`/`ETIMEDOUT`/abort) | fetch throws | Backoff + queue; connectivity WARN. |
| `send_failed` (retries exhausted) | send throws after `maxSendRetries` | Queue notification (§7.4); emit WARN; do NOT block approval flow. |
| `unauthorized_user` | `from.id` not in allow-list | `answerCallbackQuery("[DENIED] not allowed")`, log WARN, **drop** (no forward). |
| `edit_failed` | `editMessageText` 400/404 | Try once; on failure fallback `sendMessage` status update; else log INFO, clear silently (risk R19). |
| `not_supported` | one-way provider `editMessage` | Throw `NotSupportedError`; orchestrator must not call edit on Pushover. |

### 8.2 Retry strategy
- **Telegram 429 backoff:** exponential 1→2→4→8→16→32s, full jitter, respect `retry_after` header when present (overrides computed delay).
- **Send retries:** up to `maxSendRetries=3` with backoff before queueing.
- **answerCallbackQuery timeout:** wrap in `AbortController` with **5s** timeout; on timeout retry once; if still failing, log WARN + toast (risk R18). `answerCallbackQuery` is BEST-EFFORT — its failure must NEVER block `InboundDecision` emission.
- **getUpdates:** single in-flight; on failure the loop backs off and retries from persisted offset (no data loss).
- **No crash guarantee:** every `await` in the loop/handler is wrapped in try/catch; errors are logged, not thrown to the event loop.

### 8.3 Circuit breaker for degraded mode
- Track consecutive failures to Telegram API.
- After 5 consecutive failures, enter `degraded` mode (longer polling interval, more aggressive backoff).
- Reset to normal mode after 3 consecutive successful polls.

---

## 9. Configuration

All settings come from Part 1 `ExtensionSettings` (`src/core/config/types.ts`) and Part 3 `SecurityModule` (token + user ids). No new `package.json` contribution keys required for Part 2 beyond Part 1's.

| Setting | Source | Used by | Default |
|---|---|---|---|
| `pollingIntervalMs` | Part 1 settings | `PollingLoop.intervalMs` | 2000 (range 1000–5000) |
| `approvalTtlMs` | Part 1 settings | outbound `expiresInSec`, queue TTL | 1800000 (30 min) |
| `allowedTelegramUserIds` | Part 1 settings (mirror) → Part 3 `getAuthorizedUserIds()` | allow-list check | `[]` |
| Telegram bot token | **Part 3 SecretStorage** (`SecurityModule.getBotToken()`) | `FetchTelegramClient` auth | — (required) |
| `pollTimeoutSec` | TelegramProviderOptions | getUpdates `timeout` | 25 (max 50) |
| `maxSendRetries` | TelegramProviderOptions | send retry count | 3 |
| `provider` selection | Part 5 extension config / factory | which `NotificationProvider` to instantiate | `"telegram"` |

- **Token source:** exclusively `SecurityModule.getBotToken()` → SecretStorage (OS keyring). The provider NEVER reads the token from env/files directly.
- **Provider selection:** a `createProvider(kind, context)` factory (Part 5) returns `TelegramProvider` now; stubs wired for future kinds. Unknown kind → throw `ProviderError(not_supported)`.
- **Allowed users:** fast in-memory check uses `getAuthorizedUserIds()` resolved at `initialize()`; refresh on a configurable interval or via Part 3 event (out of Part 2 scope — resolved list cached for session).

---

## 10. Logging Strategy

- Use the shared structured logger from Part 1 (`src/core/shared/logger.ts`): `logger = logging.getLogger("mko-ainotify:provider:telegram")`. No `print()` (project rule #12).
- **Never log secrets:** bot token, `rawCallbackData` payload, and `callback_data` are **redacted**. Log only opaque metadata: `callbackQueryId` (short hash), `userId` (allowed? yes/no), `messageId`, `chatId`, `update_id`, `requestId` (from upstream, not from token).
- **Redaction helper:** `redactToken(s)` → returns `"<callback_data:len=NN>"`; `redactChat(id)` allowed (chat id is not secret but PII — log at DEBUG only).
- **Levels:** INFO for send success / loop start-stop / offset advances; WARN for 429/queue/allow-list denials; ERROR for malformed responses / repeated send failure; DEBUG for per-update raw (with redaction) off by default.
- **Correlation:** attach `requestId` (from `OutboundApproval`) and `callbackQueryId` to decision logs so Part 3 verification can cross-reference.
- **No token in exceptions:** error messages must not embed the token; include only error codes.

---

## 11. Testing Strategy

Tooling: **Vitest** (already chosen in Part 1), **nock** or **msw** to mock `api.telegram.org`, **fake timers** for polling/backoff, **`fast-check`** optional for property tests.

### 11.1 Unit tests
- **`messageFormatter.test.ts`** — pure function:
  - exact text layout for present/absent `reason`,
  - HTML escaping of command/cwd/project/reason (injection guard),
  - 4-button single-row keyboard with the 4 supplied tokens (no token leakage into `text`),
  - `formatDecisionText` for each `DecisionStatus`.
- **`byteBudget.test.ts`** — CRITICAL boundary:
  - every signed token from `FakeSecurityModule` ≤ 64 bytes UTF-8,
  - 4 actions → 4 distinct tokens,
  - `FakeSecurityModule` configured to emulate the 42-byte envelope (optionally via a real `SecurityModule` stub if available in Part 3),
  - assertion that `base64url(envelope)` fits: `Buffer.byteLength(t,"utf8") <= 64`.
- **`PollingLoop.test.ts`** — inject `FakeTelegramApiClient` + `FakePollingLoop` scheduler (fake timers):
  - offset advances by `max(update_id)+1` after a batch,
  - persisted via `OffsetStore` mock,
  - 429 response triggers backoff (assert delay sequence),
  - single in-flight guarantee (no overlapping getUpdates),
  - `stop()` aborts and settles in-flight request,
  - malformed update skipped, offset still advances.
- **`ApprovalStore.test.ts`** — NEW: test persistence and cleanup:
  - set/get/delete operations,
  - cleanup removes expired entries,
  - listPending returns correct keys.
- **`TelegramProvider.test.ts`** — full class with injected doubles:
  - `initialize()` calls `getMe()` + `getAuthorizedUserIds()`, resets offset,
  - `sendApprovalRequest` → `sendMessage` with correct markup; returns `MessageReference`,
  - `handleCallbackQuery` for **unauthorized user** → `answerCallbackQuery("[DENIED]")`, NO `onDecision` emit,
  - `handleCallbackQuery` for **authorized user** → `answerCallbackQuery()` (empty) THEN `onDecision` emits `InboundDecision` with raw (unparsed) `callback_data`,
  - `applyResolvedDecision` → `editMessageText` with `removeKeyboard`,
  - `sendApprovalRequest` network failure → retries (assert count) then throws `send_failed`,
  - `start()`/`stop()` idempotency and `isRunning` transitions.

### 11.2 Contract test (modularity proof)
- **`FakeProvider.test.ts`** — defines an in-memory `FakeProvider implements NotificationProvider` and runs a **provider-agnostic contract suite** (`sendApprovalRequest`, `start`/`stop`, `onDecision` fire+unsubscribe, `editMessage` optional) against BOTH `TelegramProvider` and `FakeProvider`. Proves the interface is provider-neutral and that Part 5 can swap providers without touching core logic. The stubs (`NtfyProvider`, `DiscordProvider`, `PushoverProvider`) must also pass the compile/interface portion (they throw `NotSupportedError` expectedly).

### 11.3 Fixtures & doubles
- `fixtures/getUpdates.stream.json` — scripted `update_id` sequence incl. duplicate + gap cases.
- `fixtures/sendMessage.ok.json`, `fixtures/telegram.error.429.json`.
- `doubles/FakeTelegramApiClient.ts` — scripted responses, records calls, simulates 429/timeout via `delay`.
- `doubles/FakePollingLoop.ts` — drives handler with injected updates, controllable scheduler.
- `doubles/FakeSecurityModule.ts` — returns deterministic ≤64-byte tokens (emulates the 42-byte envelope) + allow-list.

### 11.4 Edge-case coverage (from part2_risks §3)
- Phone offline → message queued, TTL drop on expiry.
- Tap after TTL → Part 3 returns `expired`; provider edits "[EXPIRED]".
- Duplicate `callback_query_id` → Part 3 consumes once; provider still emitted twice? No — provider emits raw each time Telegram sends; Part 3 dedupe is authoritative. Provider must tolerate re-emit.
- Tampered `callback_data` → `verifyCallback` (Part 3) returns `invalid`; provider edits "[INVALID]".
- Chat migration / deleted message → `editMessageText` 400/404 → fallback `sendMessage` or silent clear (R19).
- Multiple admins → verify allow-list accepts array; Part 3 maintains primary admin logic.
- Webhook conflict guard — verify `getWebhookInfo.url` empty on init.

---

## 12. Milestones (Part 2)

### M1 — Provider contract + shared scaffolding
- **Objective:** Define the stable `NotificationProvider` interface, `BaseProvider`, `ProviderContext`, and shared error types so all providers (present + future) share one shape.
- **Deliverables:** `NotificationProvider.ts`, `BaseProvider.ts`, `ProviderContext.ts`, `errors.ts` additions, `messageTemplates.ts` constants.
- **Dependencies:** Part 1 `ExtensionSettings`, `Logger` (shared), `Disposable`.
- **Acceptance:** Interfaces compile under strict TS; `BaseProvider` lifecycle + `onDecision` registry unit-tested; FakeProvider contract suite green.

### M2 — Telegram API client + raw types
- **Objective:** Typed, injectable Bot API client (no crypto, no polling logic).
- **Deliverables:** `TelegramApiClient.ts` (interface), `telegramTypes.ts` (DTOs), `FetchTelegramClient.ts` (fetch impl), escapeHtml helper.
- **Dependencies:** M1, `ProviderContext`.
- **Acceptance:** `getMe/sendMessage/getUpdates/answerCallbackQuery/editMessageText` contract tests via nock; token never logged; malformed JSON handled.

### M3 — Message formatter (pure)
- **Objective:** Deterministic, HTML-safe message + inline keyboard construction.
- **Deliverables:** `messageFormatter.ts` (`formatApprovalMessage`, `formatDecisionText`), `messageTemplates.ts`.
- **Dependencies:** M1, M2 types.
- **Acceptance:** Layout + escaping unit tests; 64-byte token boundary test (tokens ≤64, 4 distinct).

### M4 — Polling loop + ApprovalStore (isolated)
- **Objective:** Robust getUpdates pump with offset, backoff, single-in-flight, stop; persist message references.
- **Deliverables:** `PollingLoop.ts`, `backoff.ts`, `ApprovalStore.ts` (+ `OffsetStore`), `Scheduler` seam.
- **Dependencies:** M2.
- **Acceptance:** Offset advance/persist tests; 429 backoff sequence; stop() cleanup; fake-timer driven; ApprovalStore CRUD tested.

### M5 — TelegramProvider integration (send + callback + edit)
- **Objective:** Wire client + loop + formatter + SecuritySeam into the full provider.
- **Deliverables:** `TelegramProvider.ts` (`initialize`, `sendApprovalRequest`, `handleCallbackQuery`, `applyResolvedDecision`, `start`/`stop`).
- **Dependencies:** M1–M4, Part 3 `SecuritySeam` interface (signCallback/getBotToken/getAuthorizedUserIds), Part 1 `PendingApproval`→`OutboundApproval` mapping contract.
- **Acceptance:** End-to-end with `FakeTelegramApiClient`+`FakeSecurityModule`: send→poll→unauthorized-drop / authorized-emit→applyResolvedDecision-edit; send-retry+queue; `isRunning` transitions.

### M6 — Provider stubs + selection factory hook
- **Objective:** Future-proofing — stubs compile and are selectable.
- **Deliverables:** `adapters/NtfyProvider.ts`, `DiscordProvider.ts`, `PushoverProvider.ts` (throw `NotSupportedError` with documented planned mechanism).
- **Dependencies:** M1.
- **Acceptance:** Each stub implements `NotificationProvider`; contract suite confirms expected `NotSupportedError`; factory `createProvider("telegram")` returns `TelegramProvider`.

### M7 — Test coverage + integration smoke
- **Objective:** Full suite green; nock-based smoke against a recorded Bot API transcript.
- **Deliverables:** all `*.test.ts` from §11, fixtures, doubles, `byteBudget.test.ts`.
- **Dependencies:** M1–M6, Part 3 `FakeSecurityModule`.
- **Acceptance:** `vitest run` green; 64-byte boundary enforced; no token/callback_data in any log assertion; ApprovalStore tests green.

---

## 13. Task Backlog (Granular, independently implementable)

1. **T-P2-01** Define `NotificationProvider.ts` — interfaces `NotificationProvider`, `OutboundApproval`, `MessageReference`, `InboundDecision`, `ResolvedDecision`, `DecisionStatus`, `ApprovalAction`, `EditOptions`. Strict TS, no `any`.
2. **T-P2-02** Define `ProviderContext.ts` — `ProviderContext`, `SecuritySeam` (getBotToken/getAuthorizedUserIds/signCallback). Mark `// DEPENDS-ON: Part3`.
3. **T-P2-03** Extend `src/core/shared/errors.ts` with `ProviderError` + `ProviderErrorKind` (token_missing, unauthorized_user, send_failed, rate_limited, edit_failed, not_supported, invalid_response).
4. **T-P2-04** Implement `BaseProvider.ts` — `isRunning` flag, `start`/`stop` guards, `onDecision` listener registry returning `Disposable`, default `editMessage` throwing `NotSupportedError`.
5. **T-P2-05** Implement `messageTemplates.ts` — text layout constant, button labels, `escapeHtml()` helper.
6. **T-P2-06** Implement `TelegramApiClient.ts` — interface + `telegramTypes.ts` DTOs (`TelegramUpdate`, `RawCallbackQuery`, `InlineKeyboardMarkup/Button`).
7. **T-P2-07** Implement `FetchTelegramClient.ts` — fetch-based impl of all 5 methods; inject `baseUrl` + `token` getter; timeout via `AbortController`; typed parse + `invalid_response` on malformed JSON.
8. **T-P2-08** Implement `messageFormatter.ts` — pure `formatApprovalMessage(approval, tokens)` (HTML escape, 4-row keyboard) + `formatDecisionText(...)`.
9. **T-P2-09** Write `messageFormatter.test.ts` — layout, escaping/injection, 4 distinct tokens placed in keyboard only, decision text per status.
10. **T-P2-10** Implement `backoff.ts` — exponential 1→2→4→8→16→32s with full jitter; honor `retry_after` override; ceiling constant.
11. **T-P2-11** Implement `ApprovalStore.ts` + `OffsetStore` global state — `set/get/delete/listPending/cleanup`. Persist to VS Code globalState.
12. **T-P2-12** Implement `PollingLoop.ts` — single-in-flight getUpdates, offset advance/persist, abort, stop().
13. **T-P2-13** Write `PollingLoop.test.ts` — offset advance/persist, 429 backoff sequence, no overlapping requests, stop() settles, malformed-update skip.
14. **T-P2-14** Write `ApprovalStore.test.ts` — CRUD operations, cleanup removes expired, listPending works.
15. **T-P2-15** Implement `TelegramProvider.ts` — `initialize()` (getMe + load user ids + reset offset + webhook-info WARN), `sendApprovalRequest` (sign 4 tokens via SecuritySeam → format → sendMessage → MessageReference stored in ApprovalStore), `handleCallbackQuery` (allow-list → answerCallbackQuery → emit InboundDecision), `applyResolvedDecision` (editMessageText removeKeyboard), `start`/`stop`.
16. **T-P2-16** Implement `byteBudget.test.ts` — assert all signed tokens ≤64 UTF-8 bytes, 4 distinct, using `FakeSecurityModule` emulating 42-byte envelope.
17. **T-P2-17** Write `TelegramProvider.test.ts` — full flow with `FakeTelegramApiClient` + `FakeSecurityModule`: send, unauthorized-drop, authorized-emit (raw callback_data unparsed), applyResolvedDecision edit, send-retry→queue, isRunning.
18. **T-P2-18** Implement stubs `adapters/NtfyProvider.ts`, `DiscordProvider.ts`, `PushoverProvider.ts` — implement interface, throw `NotSupportedError`, header comment documenting planned response mechanism (see §6.4).
19. **T-P2-19** Implement `FakeProvider.test.ts` — provider-agnostic contract suite run against `TelegramProvider` + `FakeProvider` (in-memory) + stubs (expect `NotSupportedError`); proves swap-safety.
20. **T-P2-20** Add test doubles + fixtures: `FakeTelegramApiClient`, `FakePollingLoop`, `FakeSecurityModule`, `OffsetStore` mock, `getUpdates.stream.json`, `sendMessage.ok.json`, `telegram.error.429.json`.
21. **T-P2-21** Implement logging integration — `getLogger("mko-ainotify:provider:telegram")`, `redactToken()`, `redactChat()`; assert no token/callback_data in test-log assertions.
22. **T-P2-22** Document Part 2 in README: provider selection, token/SecretStorage flow, 64-byte constraint note + R12 correction, polling/backoff behavior, how to add a future provider (extend `NotificationProvider` + register in factory).

> **Implementation order note:** M1 (T-P2-01..04) → M2 (05..08) → M3 (09..10) → M4 (11..15) → M5 (16..17) → M6 (18) → M7 (19..22). T-P2-16/21 can run in parallel with M5. The `SecuritySeam` (T-P2-02) is an interface only in this part; its real implementation lands in Part 3.

---

## Validation Scorecard (REVISED)

### Issues Found & Resolved

| Severity | Issue | Impact | Resolution |
|---|---|---|---|
| **CRITICAL** | callback_data byte budget arithmetic error | Impossible to include action_id with 32-byte HMAC within 64 bytes | Mandated truncated HMAC (16 bytes) + 8-byte handle = 42-byte envelope, fits 64-byte limit |
| **HIGH** | Missing routing context (sessionId) in callback | Multi-worktree deployments could route decisions to wrong backend | Added `sessionId` to `OutboundApproval`, SecurityModule maps handle to requestId+sessionId pair |
| **HIGH** | Missing ApprovalStore for message references | Cannot edit messages after restart or for applyResolvedDecision | Added `ApprovalStore.ts` with globalState persistence |
| **HIGH** | Missing "always_allow" action in backend mapping | Users can't approve patterns permanently | Added action mapping: always_allow → PermissionReply.always |
| **HIGH** | SecurityModule.signCallback missing sessionId context | Handle collisions in multi-session deployments | SecuritySeam now includes sessionId context (handle is requestId-scoped) |
| **MEDIUM** | Missing circuit breaker pattern | Long Telegram outages cause aggressive retry spamming | Added degraded mode tracking in §8.3 |
| **MEDIUM** | Missing handle→requestId mapping lifecycle | Cannot resolve callbacks after extension restart | SecurityModule must persist handle mappings; documented requirement |
| **MEDIUM** | Missing Authorization interface in SecuritySeam | Unclear how multi-admin logic integrates | Added `getAuthorizedUserIds()` array, allow-list check in handleCallbackQuery |
| **LOW** | "Always Allow" button semantics unclear | User confusion about pattern approval | Documented action→backend mapping in §6.2 |
| **LOW** | Missing observability metrics | Hard to diagnose production issues | Added circuit breaker state tracking, debug-level counters |

### Cross-part dependencies (must be satisfied before M5 ships)
- **Part 1:** `PendingApproval` (type), `ExtensionSettings` (pollingIntervalMs, approvalTtlMs, allowedTelegramUserIds), `Logger`, `OffsetStore`↔`globalState`.
- **Part 3:** `SecurityModule.getBotToken()`, `getAuthorizedUserIds()`, `signCallback(actionId, action) => string (≤64B)`; `ApprovalStateManager.consume/verify` (consumes `InboundDecision` emitted here); `PendingApproval → OutboundApproval` mapping contract including sessionId.

---

## 14. Additional Requirements for Part 3 Compatibility

These items must be implemented in Part 3 to ensure Part 2 integration works correctly:

### 14.1 SecurityModule Requirements
```typescript
interface SecurityModule {
  getBotToken(): Promise<string>;
  getAuthorizedUserIds(): Promise<number[]>;
  // Returns 42-byte raw envelope, base64url-encoded to ≤64 chars
  signCallback(requestId: string, action: ApprovalAction): Promise<string>;
  // Validates HMAC, expiry, extracts handle→requestId+sessionId
  verifyCallback(token: string): Promise<{ valid: boolean; requestId?: string; sessionId?: string; action?: ApprovalAction }>;
}
```

### 14.2 ApprovalStateManager Requirements
- Maintain `handle→{requestId, sessionId}` mapping for callback resolution.
- Track `callback_query_id` with 30-second TTL for duplicate detection.
- Provide `consume(callbackQueryId)` returning `{requestId, sessionId, action}` or null if duplicate/expired.

---

*Plan revised against: Telegram Bot API v10.2 (getUpdates, callback_query, inline keyboard, 64-byte callback_data), VS Code Extension API (SecretStorage, globalState, EventEmitter/Disposable), Kilo Code 7.4.11 / opencode backend API.*

## Validation Scorecard

| Category | Score (/10) | Notes |
|----------|-------------|-------|
| **Architecture** | 8 | Clean provider seam, DI for client/loop/security; swappable. Added ApprovalStore for proper lifecycle management. |
| **Implementation Risk** | 6 | 64-byte budget corrected (R12); webhook-conflict guard (R11) added; sessionId routing addressed. |
| **Maintainability** | 9 | Small files, pure formatter, injectable loops, strict TS, ApprovalStore separated. |
| **Production Readiness** | 7 | Backoff/queue/redaction/cleanup defined; circuit breaker added; depends on Part 3 for crypto/state. |

### Top Issues Found & Resolved

1. **CRITICAL - callback_data byte budget arithmetic error**: Research incorrectly calculated that HMAC(32)+nonce(8)+expiry(8)+action_id fits in 64 bytes. With base64url encoding (4/3 inflation), this is mathematically impossible. Fixed: truncated HMAC (16 bytes) + 8-byte handle = 42-byte raw envelope, which encodes to 56 chars.

2. **HIGH - Missing routing context (sessionId) in callback**: Without sessionId, multi-worktree deployments would route approvals incorrectly. Fixed: Added sessionId to OutboundApproval and SecurityModule handle mapping.

3. **HIGH - Missing ApprovalStore for message references**: Original plan had no persistence mechanism for chat_id/message_id needed for editMessageText after restart. Fixed: Added ApprovalStore.ts with globalState persistence.

4. **HIGH - SecurityModule.signCallback interface incomplete**: Missing sessionId context could cause handle collisions. Fixed: Documented interface must map handle to requestId+sessionId pair.

5. **MEDIUM - Missing circuit breaker pattern**: Repeated Telegram API failures could cause excessive retry load. Fixed: Added degraded mode tracking in §8.3.

6. **MEDIUM - Missing Authorization interface**: Multi-admin scenarios weren't specified. Fixed: getAuthorizedUserIds() returns array, allow-list check documented.

---

**Overall Verdict**: Approved with mandatory Part 3 interface adjustments. The 64-byte callback_data constraint fix is critical; the SecurityModule interface must be updated to include handle→requestId+sessionId mapping persistence.
