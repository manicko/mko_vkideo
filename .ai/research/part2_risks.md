# Notification Provider Layer & Telegram Bot Risk Analysis

## 1. RISK REGISTER

| ID | Risk | Likelihood | Impact | Detection | Mitigation | Owner |
|----|------|------------|--------|-----------|------------|-------|
| R10 | Telegram API rate limits (HTTP 429) | MEDIUM | HIGH - Missed approvals, polling blocked | HTTP 429 response from Bot API, error logs | Exponential backoff: 1s → 2s → 4s → 8s (max 32s), queue unsent notifications in memory | TelegramProvider |
| R11 | getUpdates long-poll conflicts (multiple processes) | LOW | MEDIUM - Race condition, duplicate callbacks | Multiple `polling` status indicators, duplicate approval processing | Use single extension instance per bot token, store `lastUpdateId` in extension state, dedupe via callback_query_id | TelegramProvider |
| R12 | callback_data 64-byte overflow | HIGH | HIGH - Approval data truncated or rejected | Validation error on sendMessage, truncated callback_data in debug | Structure: `HMAC(32) + nonce(8) + expiry(8) + action_id(16)` = 64 bytes max; truncate action_id if needed | SecurityModule |
| R13 | Network failures to api.telegram.org | MEDIUM | HIGH - Notifications/failures undelivered | ECONNREFUSED/ETIMEDOUT errors, `can't reach Telegram` logs | Retry with exponential backoff, queue approvals in memory with TTL, status bar warning on connectivity loss | TelegramProvider |
| R14 | Telegram server outages | LOW | HIGH - No approval delivery/responses | Failed HTTP requests across all endpoints, Telegram status page check | Queue approvals in memory, provide fallback notification (VS Code native) when Telegram unavailable | TelegramProvider |
| R15 | Bot token compromise (SecretStorage breach) | LOW | CRITICAL - Unauthorized approval sending/fake approvals | Suspicious approval activity, unknown messages in Telegram | Rotate token immediately, never log token, use SecretStorage with OS keyring, provide `Reset Token` command | SecurityModule |
| R16 | Unauthorized user pressing buttons | MEDIUM | HIGH - Wrong person approves destructive commands | Unknown user_id in callback_query, audit trail mismatch | Validate `from.user_id` against authorized admin list, reject unauthorized users silently | TelegramProvider |
| R17 | Message flooding on concurrent approvals | MEDIUM | MEDIUM - Telegram rate limit triggered, chat spam | Multiple rapid sendMessage calls, user complaint | Debounce rapid approvals (max 1 notification per 2s), batch multiple approvals into single message with multiple buttons | TelegramProvider |
| R18 | answerCallbackQuery timeout | MEDIUM | MEDIUM - User sees spinning indicator forever | Unhandled promise rejection, user taps button but no feedback | Set 5s timeout on answerCallbackQuery, retry once on failure, show error toast in VS Code | TelegramProvider |
| R19 | editMessageText failures on old/expired messages | MEDIUM | LOW - UI inconsistency | HTTP 400/404 on editMessageText, message may be deleted by user | Wrap in try/catch, fallback to sendMessage for status update, clear error silently | TelegramProvider |
| R20 | Multiple admin users / chat confusion | LOW | MEDIUM - Wrong admin responds, unclear responsibility | Multiple users in same chat, config mismatch | Support configurable admin user_ids list, tag message with requesting session/worktree, track primary admin | ConfigManager |

## 2. NON-FUNCTIONAL REQUIREMENTS & SLOs

| Category | Requirement | Target SLO |
|----------|-------------|------------|
| Notification Latency | Command approval to Telegram delivery | ≤ 3s median, ≤ 5s p95 |
| Polling Responsiveness | getUpdates polling interval | 1-2s default (configurable 0.5-5s range) |
| Polling Throughput | Updates per polling cycle | Max 100 updates, process all before next poll |
| Rate Limit Handling | 429 backoff strategy | Exponential: 1s → 2s → 4s → 8s → 16s → 32s (max) |
| Offline Queue | Approvals queued during network outage | Queue in memory, TTL 30 min, min 10, max 1000 items |
| Callback Validation | HMAC signature verification | Verify within 1ms, reject invalid immediately |
| Memory Bound | Provider state size | ≤ 50MB, bounded queue with LRU eviction |
| Connectivity Loss | Detection and recovery time | Detect within 5s, recover within 30s of connectivity restored |

## 3. EDGE CASES

1. **Phone offline when approval requested**: Telegram server queues message; user sees notification on next online. Extension should track queued state and retry if no callback received within extended TTL.

2. **User approves after TTL expired**: SecurityModule HMAC verification includes expiry timestamp. ApprovalStateManager rejects with `expired` status; user notified via Telegram "Request expired" message.

3. **Concurrent duplicate callbacks**: `callback_query_id` deduplication in ApprovalStateManager. First valid response wins, subsequent responses rejected with appropriate error logging.

4. **User rejects vs approves**: Approve triggers `client.permission.reply(approve: true)`, Reject triggers `client.permission.reply(approve: false)`. Reject with optional reason logged.

5. **VS Code sleeps/laptop closed**: Extension host suspends; no polling occurs. When resumed, extension starts polling from last known `update_id`. Could miss callbacks if phone approves during sleep.

6. **User switches chat/migrates to supergroup**: `chat.id` changes after migration; message editing may fail. Use `message_thread_id` for topics, re-send notification if edit fails.

7. **Inline keyboard callback with wrong data format**: User tampers with callback_data. SecurityModule.verifyCallback() returns false; log attempt and ignore silently.

8. **Multiple bots configured accidentally**: SecretStorage conflict, wrong token used. Validate token on startup via `getMe` call; show error if unauthorized.

## 4. TESTABILITY NOTES

| Component | Challenge | Test Strategy |
|-----------|-----------|---------------|
| TelegramProvider | Requires real bot/token | Mock Bot API via `nock` (Node) or `responses` (Python); fake `getUpdates` stream with controlled update_id sequence |
| sendMessage callback_data | 64-byte constraint hard to verify | Unit test HMAC structure encoding, assert Base64Url length ≤ 64 |
| Polling loop | Real timing/hard to simulate | Inject `PollingStrategy` interface, use fake timers for interval control |
| Callback verification | Security-critical path | Property-based testing with `fast-check` or `hypothesis`; test expired/tampered/invalid signatures |
| answerCallbackQuery timeout | Network-dependent behavior | Mock HTTP timeout via `nock`'s `.delay()` and abort controller; test timeout handling |
| Network outage simulation | Hard to reproduce reliably | Mock ECONNREFUSED/ETIMEDOUT errors; verify queue behavior and retry logic |
| Rate limiting (429) | Real Telegram ban if triggered | Mock 429 responses, verify exponential backoff, test queue persistence |
| NotificationProvider interface | Ensure modularity for other providers | Contract tests with `FakeProvider` implementing same interface; verify KiloBackendConnector works with any provider |
| Multi-admin scenarios | Complex approval routing | Inject `AdminRegistry` interface, test with mock user lists |