# Part 2: Notification Provider Layer & Telegram Bot Architecture

## 1. Internal Architecture of TelegramProvider

### Bot Lifecycle

```
----------------------¬
¦ Extension Activation ¦
L----------T-----------
           ¦
           ¡
----------------------¬     ------------------------¬
¦ SecurityModule      ¦     ¦ SecretStorage         ¦
¦ getBotToken()        ¦<--->¦ (OS keyring)          ¦
L----------T-----------     L------------------------
           ¦
           ¡
--------------------------------------¬
¦ TelegramProvider.initialize()       ¦
¦ - Validate token via getMe()          ¦
¦ - Retrieve allowedTelegramUserIds   ¦
¦ - Initialize offset = 0             ¦
L--------------------------------------
           ¦
           ¡
--------------------------------------¬
¦ TelegramProvider.start()              ¦
¦ - Spawn polling loop Promise          ¦
¦ - Loop runs in extension host         ¦
¦ - Uses Node''s https/fetch only        ¦
L--------------------------------------
           ¦
           ¡ (continuous polling)
--------------------------------------¬
¦ Polling Loop                        ¦
¦ GET /getUpdates?offset=X&timeout=30 ¦
¦ ----------------------------------¬ ¦
¦ ¦ Response: Update[]              ¦ ¦
¦ ¦ - Parse update_id               ¦ ¦
¦ ¦ - Extract callback_query        ¦ ¦
¦ ¦ - Extract from.id (user ID)     ¦ ¦
¦ ¦ - Extract data (signed payload) ¦ ¦
¦ L-------------T-------------------- ¦
¦               ¡                     ¦
¦ ----------------------------------¬ ¦
¦ ¦ Handler Dispatch                  ¦ ¦
¦ ¦ callback_query -> processCallback ¦ ¦
¦ L---------------------------------- ¦
¦ ----------------------------------¬ ¦
¦ ¦ Offset Update                   ¦ ¦
¦ ¦ offset = max(update_id) + 1     ¦ ¦
¦ L---------------------------------- ¦
L--------------------------------------
```

### Polling Loop Design (Long Poll)

- Endpoint: https://api.telegram.org/bot<token>/getUpdates
- Parameters: offset, limit=100, timeout=30s, allowed_updates=["callback_query"]
- Concurrency: Single-threaded async loop in extension host; sequential offsets prevent race conditions
- Offset Management: Persist last processed update_id to extension global state; increment after each successful batch
- No Webhook Conflict: Extension never calls setWebhook, ensuring getUpdates works

### Concurrency Model

- Single Poller: One getUpdates call at a time; holds connection open via timeout=30
- Idempotency: Process callback_query_id through ApprovalStateManager to prevent double-processing
- Fast Response Required: answerCallbackQuery must be called within ~30s or client shows spinner indefinitely

---

## 2. Layer Interaction Diagram (ASCII)

```
------------------¬     ------------------¬     ------------------¬
¦ KiloBackend-    ¦     ¦ Telegram-       ¦     ¦ ApprovalState-  ¦
¦ Connector       ¦     ¦ Provider        ¦     ¦ Manager         ¦
L-------T----------     L---------T--------     L---------T--------
        ¦                         ¦                       ¦
        ¦ 1. permission.asked     ¦                       ¦
        ¦    (requestID, metadata)  ¦                       ¦
        ¡                         ¦                       ¦
----------------¬                 ¦                       ¦
¦ emit event    ¦                 ¦                       ¦
L-------T--------                 ¦                       ¦
        ¦                         ¦                       ¦
        ¦ 2. sendApprovalRequest()  ¦                       ¦
        +------------------------>¦                       ¦
        ¦                         ¦                       ¦
        ¦                         ¦ 3. SecurityModule.    ¦
        ¦                         ¦    signCallback()     ¦
        ¦                         +----------T-------------¬¦
        ¦                         ¦          ¦             ¦¦
        ¦                         <----------+-------------+
        ¦                         ¦ (signed ¦             ¦¦
        ¦                         ¦  token)¦             ¦¦
        ¦                         ¦         ¦             ¦¦
        ¦ 4. sendMessage with   ¦         ¦             ¦¦
        ¦    inline keyboard      ¦         ¦             ¦¦
        ¦    callback_data        ¦         ¦             ¦¦
        ¦ <-----------------------+         ¦             ¦¦
        ¦                         ¦         ¦             ¦¦
        ¦                         ¦         ¡             ¡¡
        ¦              ---------------------------------------¬
        ¦              ¦ User taps button                       ¦
        ¦              ¦ Telegram > callback_query              ¦
        ¦              L------------------T--------------------
        ¦                                 ¦
        ¦ 5. callback_query polling       ¦
        ¦    (data, from.id, id)         ¦
        ¦ <-------------------------------+
        ¦                                 ¦
        ¦                    6. validateAndConsume()
        ¦                     (callback_data, userId)
        ¦                     ----------->¦
        ¦                     ¦           ¦
        ¦                     <-----------+
        ¦                     ¦ (decision)¦
        ¦                     ¦           ¦
        ¦ 7. answerCallbackQuery()       ¦
        +-------------------------------+
        ¦                               ¦
        ¦ 8. editMessageText()          ¦
        +-------------------------------+
        ¦                               ¦
        ¦ 9. replyToPermission()        ¦
        +------------------------------->¦
        ¦                               ¦
        ¦                               ¡
        ¦                    --------------------------------¬
        ¦                    ¦ opencode backend              ¦
        ¦                    ¦ continues execution           ¦
        ¦                    L--------------------------------
```

---

## 3. Data Contracts

### Telegram Message Payload

?? Kilo Code Approval Request
Command: <code>
WDirectory: <path>
Project: <name>
Reason: <reason>
Timestamp: <ISO date>

Inline Keyboard:
[
  [{"text": "[APPROVE]", "callback_data": "<signed-token-A>"}],
  [{"text": "[REJECT]", "callback_data": "<signed-token-R>"}],
  [{"text": "[APPROVE_ONCE]", "callback_data": "<signed-token-O>"}]
]

### getUpdates Response Parsing

interface TelegramUpdate {
  update_id: number;           // Sequential ID, persists offset
  callback_query?: {
    id: string;                // Unique query ID (telegram's callback_query_id)
    from: { id: number };      // User ID who pressed button
    data: string;              // Signed callback_data (<=64 bytes)
    message?: {
      message_id: number;
      chat: { id: number };    // Chat ID for editMessageText
    };
  };
}

### NotificationProvider Interface (TypeScript)

type ApprovalAction = 'approve' | 'reject' | 'approve_once';

interface ApprovalRequest {
  requestId: string;           // Unique, from opencode SDK
  command: string;
  workingDirectory: string;
  projectName: string;
  reason?: string;
  timestamp: number;
}

interface ApprovalResponse {
  requestId: string;
  action: ApprovalAction;
  userId?: number;             // From callback_query.from.id
  callbackQueryId?: string;   // For answerCallbackQuery
}

interface NotificationProvider {
  sendApprovalRequest(req: ApprovalRequest): Promise<void>;
  start(): Promise<void>;
  stop(): Promise<void>;
  onDecision(callback: (resp: ApprovalResponse) => void): void;
}
```

---

## 4. Provider Abstraction Internals

### Base Abstraction Structure

```
----------------------------------¬
¦   NotificationProvider          ¦  (abstract interface)
¦   - sendApprovalRequest()       ¦
¦   - start() / stop()            ¦
¦   - onDecision(cb)              ¦
L-------------T--------------------
              ¦
     ---------+--------T--------T---------¬
     ¡                 ¡        ¡         ¡
TelegramProvider   NtfyProvider DiscordProvider  PushoverProvider
¦                  ¦          ¦         ¦
¦ - Inline         ¦ - Action ¦ -       ¦ - No native buttons
¦   Keyboard       ¦   buttons¦  Button ¦ - URL redirect flow
¦ - getUpdates     ¦ - HTTP   ¦  comps  ¦ - Manual open
¦ - callback_query ¦   POST   ¦ - Intv  ¦  
¦                  ¦          ¦         ¦
L------------------+----------+----------
```

### Provider Mapping

| Provider | Interaction Mechanism | Limitations |
|----------|----------------------|-------------|
| Telegram | inline_keyboard with callback_data | 64-byte limit on callback_data |
| ntfy | Action buttons with HTTP POST callback | Requires HTTPS endpoint; port exposure |
| Discord | Button components + interaction callback | Requires bot in server; webhook or polling |
| Pushover | URL buttons only (no true callback) | User must tap link; no instant response |

### Abstraction State Requirements

- isRunning: boolean - Provider lifecycle state
- registeredRequests: Map<string, ApprovalRequest> - For correlation
- pendingCallbackQueryIds: Set<string> - Deduplication (30s TTL)
- botToken?: string - Retrieved at init, stored in SecretStorage

---

## 5. Edge Design

### Message Editing After Decision

After callback, call editMessageText to update message:
[APPROVED] by @user
Command: <code>
Status: Executed [OK]

Prevents confusion if user presses wrong button.

### Stale Messages

- callback_data contains embedded expiry (Unix timestamp)
- If expired, SecurityModule.verify() returns error
- TelegramProvider handles expired_token as reject automatically
- UX: Show "[EXPIRED] Request expired" in message edit

### Unauthorized User Handling

callback_query.from.id --> not in allowedTelegramUserIds?
       ¦
       +-- YES --> SecurityModule returns UNAUTHORIZED
       ¦            TelegramProvider calls answerCallbackQuery(text="[DENIED] Not allowed")
       ¦            No forward to Connector
       ¦
       L-- NO --> Normal flow (validate, consume, forward)

---

## 6. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rate Limit (30 req/sec) | Medium | Use timeout=30 long-polling; respect minimum 1s between requests; implement exponential backoff on 429 |
| getUpdates vs Webhook Conflict | High | Never call setWebhook; verify getWebhookInfo.url is empty on init |
| 64-byte callback_data Overflow | High | Encode: HMAC(32) + nonce(8) + expiry(8) + requestID(remaining~16); use Base64Url; truncate requestID if needed |
| Telegram API Outage | Medium | Queue unsent notifications; show VS Code status bar warning; reconnect with backoff |
| Duplicate callback_query | Medium | Use callback_query_id as deduplication key; TTL cleanup after 5min |
| Bot Token Compromise | High | Store ONLY in VS Code SecretStorage (OS keyring); never log; provide rotate-token command |
| User blocked bot | Low | sendMessage returns error; surface in VS Code status bar |
| Phone offline > 24h | Low | Updates expire after 24h on Telegram servers; auto-reject stale approvals |

### Sources

- Telegram Bot API v10.2: https://core.telegram.org/bots/api#getupdates (official)
- InlineKeyboardButton: callback_data max 64 bytes (line 5448 of official docs)
- CallbackQuery structure: lines 5612-5646 of official docs (id, from, data, message fields)
- Long polling guidance: "In order to avoid getting duplicate updates, recalculate offset after each server response" (official docs)
