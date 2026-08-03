# Mko-AINotify Part 2: Notification Provider Layer & Telegram Bot Requirements

## 1. Functional Requirements

### TelegramProvider (FR-1 to FR-8)

**FR-1: Send Approval Notifications**
- Send message to configured Telegram chat via `sendMessage` API
- Include command, working directory, project name, reason, and timestamp in message body
- Attach inline keyboard with 4 buttons: Approve, Reject, Approve Once, Always Allow

**FR-2: Long-Polling for Callback Queries**
- Implement `getUpdates` with `allowed_updates=["callback_query"]`
- Use long-polling timeout (20-30s) for efficient delivery
- Track `update_id` offset to avoid duplicate processing

**FR-3: Callback Query Handling**
- Parse `CallbackQuery.data` (max 64 bytes UTF-8) from incoming updates
- Extract action and approval ID from signed callback data
- Call `answerCallbackQuery` with user feedback notification within 10s

**FR-4: Message Feedback on Decision**
- Call `editMessageText` to update original notification with decision status
- Show approved/rejected timestamp and action taken
- Disable inline keyboard on processed messages

**FR-5: Chat Identity Verification**
- Verify `CallbackQuery.from.id` matches authorized admin user(s)
- Reject callbacks from unauthorized users silently

**FR-6: Pending State Management**
- Store message_id and chat_id for each sent notification
- Enable message editing after decision received

**FR-7: Error Recovery**
- Handle Telegram API rate limits (HTTP 429) with exponential backoff
- Retry failed sends up to 3 times before marking as failed
- Log errors without blocking approval flow

**FR-8: Graceful Shutdown**
- Cancel polling on extension deactivation
- Ensure no pending HTTP requests on shutdown

### NotificationProvider Abstraction (FR-9 to FR-11)

**FR-9: Unified Provider Interface**
- Define abstract interface with methods: `sendRequest(approval)`, `startPolling()`, `stopPolling()`, `onResponse(callback)`
- Support registration of approval state handlers via dependency injection

**FR-10: Pluggable Provider Architecture**
- Enable TelegramProvider as primary implementation
- Design for future ntfy, Discord, Pushover providers (different response mechanisms per provider)

**FR-11: Response Normalization**
- Map provider-specific response format to common `ApprovalResponse` model
- Include: requestID, action (approve/reject/approve_once/always_allow), user ID, timestamp

## 2. Non-Functional Requirements

| Requirement | Target | Source |
|-------------|--------|--------|
| **Latency** | Notification delivery < 2s, response processing < 500ms | Telegram Bot API docs |
| **Reliability** | Survive VS Code restart, queue unsent notifications | research_03 comparison |
| **Rate-Limit Compliance** | Respect 30 msg/sec limit, implement backoff | Telegram API 10.2, research_02 |
| **Cross-Platform** | Works on Windows/macOS/Linux via SecretStorage | VS Code Extension API |
| **Resource Usage** | Polling interval 1-2s when active, idle when no pending | Architecture constraint |
| **Offline Handling** | Telegram queues messages; timeout after 30 min default | research_02 design |
| **Security** | No local port exposure, token in SecretStorage | research_02 validated |

## 3. Goals & Success Criteria

### Primary Goal
Enable remote two-way approval/reject from mobile phone with single-tap buttons, eliminating indefinite blocking of autonomous Kilo sessions.

### Success Criteria
1. **Approval Flow**: User receives notification with inline keyboard → taps button → VS Code receives decision → Kilo continues execution
2. **Modularity**: NotificationProvider interface allows dropping-in alternative providers without modifying core logic
3. **Security**: No public port exposure; HMAC verification (owned by SecurityModule) prevents forged approvals
4. **Reliability**: Works when phone is on different network; survives short extension restarts

### Failure Modes to Prevent
- Duplicate approvals (dedupe via ApprovalStateManager)
- Stuck progress indicator (mandatory `answerCallbackQuery`)
- Token exposure in logs (SecretStorage only)

## 4. Responsibility Zones

### TelegramProvider OWNS
- Telegram Bot API HTTP client (axios/node-fetch)
- `sendMessage` with inline keyboard construction
- `getUpdates` long-polling loop
- `answerCallbackQuery` calls
- `editMessageText` for feedback
- Chat ID and message tracking for pending approvals

### TelegramProvider DELEGATES
| Delegated To | Responsibility |
|--------------|----------------|
| **SecurityModule** | HMAC signing of callback_data, bot token retrieval from SecretStorage, chat identity verification |
| **ApprovalStateManager** | Pending state storage, TTL/expiration, callback_query_id deduplication, action_id resolution |
| **KiloBackendConnector** | `replyToPermission(requestID, Decision)` SDK call for final approval transmission |

### NotificationProvider Interface Contract
```typescript
interface NotificationProvider {
  // Send approval request, return provider-specific message reference
  sendRequest(approval: ApprovalRequest): Promise<MessageReference>
  
  // Start polling/receiving responses
  startPolling(): Promise<void>
  
  // Stop polling
  stopPolling(): Promise<void>
  
  // Register callback for incoming responses
  onResponse(callback: (response: ApprovalResponse) => void): void
  
  // Optional: edit message after decision
  editMessage(reference: MessageReference, text: string, replyMarkup?: any): Promise<void>
}
```

## 5. Key Integrations & Contracts

### Telegram Bot API Methods
| Method | Purpose | Constraints |
|--------|---------|-------------|
| `sendMessage` | Send notification with inline keyboard | chat_id, text, reply_markup required |
| `getUpdates` | Long-poll for callback_query updates | timeout=20-30s, allowed_updates=["callback_query"] |
| `answerCallbackQuery` | Acknowledge button press | Must be called within ~10s to avoid stuck indicator |
| `editMessageText` | Update message after decision | chat_id, message_id, text, reply_markup |

### callback_data Format (64-byte limit)
```
callback_data = base64url(HMAC(32) + nonce(8) + expiry(8) + action_id(remaining))
Total: ≤64 bytes
HMAC: 32 bytes (SecurityModule.signCallback())
Nonce: 8 bytes random
Expiry: 8 bytes Unix timestamp
Action ID: Remaining bytes (maps to Kilo's requestID)
```

### SecurityModule Integration
- `signCallback(actionId, action)` returns signed token ≤64 bytes
- `verifyCallback(token)` validates HMAC and expiry, throws on invalid
- `getBotToken()` returns token from VS Code SecretStorage
- `getAuthorizedChatId()` returns admin user ID(s) for verification

## 6. Provider-Abstraction Design

### Common Interface
- `sendRequest(approval)` - send notification with action buttons
- `startPolling/stopPolling` - lifecycle management
- `onResponse(callback)` - normalized approval response routing
- State handlers for pending/approved/rejected tracking

### Provider-Specific Variations
| Aspect | Telegram | ntfy | Discord | Pushover |
|--------|----------|------|---------|----------|
| **Two-Way** | Inline keyboard callback | Action buttons HTTP callback | Button interactions | No native buttons (URL only) |
| **State Management** | editMessageText | Cloud relay | Update message | Not applicable |
| **Identity Verification** | Telegram user_id | HTTP auth header | Discord user_id | User key in API |
| **Callback Data** | 64-byte signed token | Topic + action in URL | Custom ID | Not supported |
| **Polling** | getUpdates API | HTTP polling or SSE | Gateway events | N/A (one-way) |

### Extensibility Points
- Button rendering: Each provider defines its own "action button" format
- Response parsing: Provider extracts action from native callback format
- Message editing: Telegram/Discord support edits; ntfy/Pushover may not

## 7. Open Questions for Planner

1. **Multiple Admin Users**: Should the extension support multiple authorized Telegram user IDs, or single admin only? Current design assumes single admin.

2. **Message Update on Decision**: Should the original notification be edited to show "Approved" status, or send a new follow-up message? Editing retains context but requires stored message_id.

3. **Internationalization (i18n)**: Should button labels and messages be localized based on VS Code locale, or use English only?

4. **Worktree Port Mapping**: When multiple Kilo worktrees are active, how does TelegramProvider route responses to the correct KiloBackendConnector instance?

5. **Polling vs Webhook in Extension Host**: Long-polling in extension host may conflict with VS Code's single-threaded event loop during heavy IDE usage; should polling run in web worker?

6. **Approval Timeout Behavior**: After TTL expiry (default 30 min), should the extension auto-reject and notify user, or keep waiting with visual indicator?

---

**Sources**: Telegram Bot API 10.2 (core.telegram.org/bots/api), validated callback_data 64-byte limit and getUpdates long-polling semantics.