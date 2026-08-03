# Part 3 — Security & Approval State Risk Analysis

**Scope:** SecurityModule (HMAC sign/verify, SecretStorage token + secret, handle map persistence) + ApprovalStateManager (pending state, TTL, dedupe by callback_query_id)

---

## 1. Risk Register

| ID | Risk | Likelihood | Impact | Detection | Mitigation | Owner |
|----|------|------------|--------|-----------|------------|-------|
| **R1** | Replay attack (captured callback_data reused after expiry window) | MEDIUM | HIGH | Verification step rejects due to nonce/expiry mismatch; audit logs show duplicate attempts | 30-minute TTL (configurable), 8-byte random nonce, server-side dedupe by callback_query_id, consume-once semantics | SecurityModule |
| **R2** | HMAC secret compromise / leakage (logs, memory dump) | LOW | CRITICAL | Code review, static analysis for `print()`/`console.log` calls; runtime detection via audit trail analysis | Generate 256-bit secret; never log; use cryptographically-secure random; erase from memory after use; store only in SecretStorage | SecurityModule |
| **R3** | Bot token compromise (stored in SecretStorage) | LOW | HIGH | Monitor bot for suspicious activity; token rotation detects compromise | Store only in VS Code SecretStorage (OS keyring); provide `rotateToken()` command; never embed in code/logs; use scoped bot permissions | SecurityModule |
| **R4** | Handle collision / map exhaustion (8-byte handle wraps) | LOW | MEDIUM | Handle collision detected during sign; test coverage for collision paths | 8-byte handle = 2^64 unique values; collision check on insert; reject and regenerate if collision; for multi-instance use UUID-based handles | ApprovalStateManager |
| **R5** | Clock skew causing valid callback rejected or expired accepted | MEDIUM | MEDIUM | Audit: approvals rejected outside expected time window; replay accepted unexpectedly | Use UTC timestamps; add ±60s grace window; reject if `now > expiry + grace` instead of `now > expiry`; log skew warnings | ApprovalStateManager |
| **R6** | Race: two callbacks for same requestId (dedupe by callback_query_id must hold) | LOW | HIGH | Test with parallel webhook simulation; production monitoring of duplicate responses | `callback_query_id` is globally unique per Telegram API; store in processed set with TTL; first consumes, subsequent rejected with `[ALREADY_PROCESSED]`; atomic check-and-set pattern | ApprovalStateManager |
| **R7** | VS Code reload loses in-memory pending/handle/processed maps (recovery strategy) | HIGH | MEDIUM | Test: extension reload during active approval flow | Persist `handle→{requestId,sessionId}` and `callback_query_id→processed` to `globalState`; rebuild maps on startup; cleanup stale entries on init | ApprovalStateManager |
| **R8** | SecretStorage unavailable (headless/remote VS Code, Linux without keyring) | MEDIUM | HIGH | Fail to retrieve token on startup; fallback to encrypted file | Graceful degradation: encrypted file fallback at `~/.config/mko-ainotify/secrets.json.enc`; warn in status bar; require manual token input; document keyring setup | SecurityModule |
| **R9** | Unauthorized Telegram user pressing buttons (authorization by allowedUserIds) | MEDIUM | HIGH | Test: callback from non-allowed user; production audit | Fast allow-list check in `handleCallbackQuery`; `answerCallbackQuery("[DENIED]")`; DO NOT forward to upstream; log WARN | SecurityModule |
| **R10** | TTL too long (window for replay) vs too short (user can't respond) | MEDIUM | MEDIUM | User experience feedback; audit of expired approvals | Default 30 minutes (1800000ms) based on research; configurable via settings; warning displayed if < 5m or > 2h; status bar shows countdown | ApprovalStateManager |

---

## 2. Non-Functional SLOs

| Metric | Target | Rationale |
|--------|--------|-----------|
| HMAC verify latency | < 5ms | Per research: verify must be fast to avoid blocking main thread; crypto operations in TypeScript/Node are optimized |
| HMAC signing latency | < 10ms | One-time operation during approval request; acceptable for async flow |
| HMAC secret strength | 256-bit entropy | Generated via `crypto.randomBytes(32)`; truncated to 16 bytes for signature (128-bit security per NIST SP 800-107) |
| TTL default | 30 minutes (1800000ms) | Research suggests 30-minute window for approval lifecycle; balances replay risk vs user availability |
| Replay window | ≤ TTL + 60s grace | Any callback_data with embedded expiry older than `now - grace` is invalid |
| Crypto algorithm | HMAC-SHA256 | Standard, well-vetted; truncate to 16 bytes for Telegram byte budget |
| Handle entropy | 64-bit random (8 bytes) | 2^64 unique values per extension instance; collision probability negligible |
| Offset persistence flush | Every successful batch | Prevents reprocessing duplicate updates after restart |
| Queue memory bound | ≤ 50MB, 1000 entries max | Per polling design §7.4; prevents memory exhaustion |

---

## 3. Edge Cases

| Case | Expected Behavior | Component Handling |
|------|-------------------|------------------|
| Expired approval tapped | `verifyCallback` returns `expired`; `editMessageText` shows `[EXPIRED]` | ApprovalStateManager expiry check |
| Duplicate tap (same button) | First `callback_query_id` consumed; subsequent rejected with `QUERY_ID_INVALID` by Telegram or `[ALREADY_PROCESSED]` toast | ApprovalStateManager dedupe set |
| User not allowed | `answerCallbackQuery("[DENIED] not allowed")`, drop event | SecurityModule allow-list check |
| Secret rotation mid-session | New approvals use new secret; old handle mappings invalidated after re-sign | SecurityModule + ApprovalStateManager |
| Remote/SSH VS Code without keyring | Fall back to encrypted file storage; prompt for token on startup | SecurityModule fallback path |
| Concurrent approvals for different sessions | Each requestId has unique handle; sessionId carried in OutboundApproval | ApprovalStateManager per-request mapping |
| Extension host reload mid-approval | Handle mappings restored from globalState; polling offset restored; expired approvals cleaned up | ApprovalStateManager rebuild on init |

---

## 4. Testability

| Test Target | Approach |
|-------------|----------|
| HMAC sign/verify round-trip | `signCallback(requestId, "approve")` → `verifyCallback(token)` returns valid=true with matching action |
| Tamper detection | Modify token bytes → `verifyCallback` returns valid=false |
| Expiry detection | Create token with past timestamp → verify returns expired=true |
| Dedupe by callback_query_id | Call `consume("cbq_123")` twice → second returns null/stale |
| SecretStorage mock | Inject `FakeSecretStore` implementing `Memento` interface; assert no token in logs |
| Persistence across reload | Use `FakeGlobalState` with in-memory map; simulate `ExtensionContext` reload lifecycle |
| Replay attack simulation | Reuse valid token after TTL → rejected; reuse within grace window → accepted |
| Handle collision test | Exhaustively test collision path with mock random; verify regeneration on collision |
| Clock skew tolerance test | Test with clock ±60s from server; verify grace window handling |

---

## 5-Line Summary

R1-R10 cover replay attacks, secret/token compromise, handle exhaustion, clock skew, race conditions, reload recovery, headless environments, and unauthorized users. SLOs mandate <5ms HMAC verify, 256-bit secrets, 30-min TTL defaults, and HMAC-SHA256 with 16-byte truncation. Edge cases include expired taps, secret rotation, concurrent sessions, and SSH environments. Testing focuses on round-trip crypto, tamper/expiry detection, and mocked SecretStorage/globalState. Handle collisions are managed via 64-bit random handles with regeneration on conflict.