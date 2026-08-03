# Plan 03 — Security & Approval State (Part 3 of 5) - REVISED

**Project:** Mko-AINotify — companion VS Code extension that forwards Kilo Code (opencode backend) permission approval requests to a mobile notification channel (Telegram) and relays decisions back.

**This part delivers:** The **security-critical core** of the system:
- **SecurityModule** — HMAC-SHA256 sign/verify of a 42-byte `callback_data` envelope (≤64-byte Telegram limit), secret + bot-token storage in VS Code `SecretStorage`, and persistence of a `handle → (requestId, sessionId, directory, action)` map.
- **ApprovalStateManager** — registers pending approvals with TTL, validates + consumes incoming decisions (dedupe by `callback_query_id` via `SecurityModule.verifyCallback`, plus allowed-user authorization), and expires stale approvals.

**Source research:** `part3_requirements.md`, `part3_architecture.md`, `part3_risks.md`, `validation_priority.md`, and the upstream contracts `01_backend_connector.md` (Part 1) + `02_notification_provider.md` (Part 2).

> **Dependency note (read first).** This part is the crypto + state authority. It does NOT own transport, backend replies, or config discovery. The following are consumed as interfaces from other parts:
> - **Part 1 — KiloBackendConnector / ConfigManager:** type `PendingApproval` (§4.1 of plan 01), `ExtensionSettings` (`approvalTtlMs`, `allowedTelegramUserIds`, `pollingIntervalMs`, …), and `connector.replyToPermission(requestId, sessionId, directory, reply: PermissionReply)` (the orchestrator in Part 5 calls this after a verified decision; Part 3 never calls it directly).
> - **Part 2 — TelegramProvider:** forwards a raw `InboundDecision` upward (callback_query_id, userId, rawCallbackData, chatId, messageId). Part 3 consumes it; it never sends messages itself.
> Where Part 2 interfaces are not yet finalized, this plan pins the corrected contract shape and flags the seam with `// DEPENDS-ON: Part2`.

---

## 1. Scope & Goals

### 1.1 What this part delivers
- **`SecurityModule`** — single owner of:
  - 256-bit HMAC secret generation/storage (exclusively `SecretStorage`).
  - `signCallback(requestId, action) → string` producing opaque ≤64-byte token (42-byte envelope → base64url = 56 chars). REVISED: Takes only (requestId, action) - handle map stores sessionId/directory from context.
  - `verifyCallback(token) → VerifyOutcome` extracting handle, validating hmac/nonce/expiry.
  - Bot-token lifecycle (`getBotToken` / `setBotToken` / `deleteBotToken`).
  - Handle context storage: Maps handle → (requestId, sessionId, directory) for routing.
  - Secret rotation (`rotateSecret`).
  - Rate-limited verification to prevent DoS attacks.
- **`ApprovalStateManager`** — single owner of:
  - Pending-approval registration with TTL + persistence.
  - `callback_query_id` deduplication (consume-once).
  - Allowed-user authorization at decision time.
  - Expiry sweeps (`expireOld`) + status reporting (`getStatus`).
  - Audit trail for security decisions.
  - Orchestration of `SecurityModule.verifyCallback` + handle resolution to produce a `ResolvedDecision`.

### 1.2 Explicit out-of-scope (owned by other parts)
| Responsibility | Owning part / module |
|---|---|
| Backend reply execution (`client.permission.reply`) | Part 1 — KiloBackendConnector (`replyToPermission`) |
| Sending the Telegram message / polling `getUpdates` | Part 2 — TelegramProvider |
| Normalizing `PendingApproval` → `OutboundApproval` | Part 5 — orchestrator |
| Building the inline keyboard / formatting text | Part 2 — `messageFormatter` |
| Config file discovery & `ExtensionSettings` schema | Part 1 — ConfigManager |
| Status-bar UI, `activate()`/`deactivate()` glue | Part 5 — extension |

---

## 2. Module Responsibilities & Boundaries

### 2.1 SecurityModule — OWNS
| Responsibility | Notes |
|---|---|
| 256-bit HMAC secret generation + storage | `SecretStorage` only; never log/expose/cache plaintext. |
| `signCallback()` envelope creation | Builds 42-byte envelope, generates 8-byte handle, stores mapping, signs, base64url-encodes. |
| `verifyCallback()` signature validation | Decodes token, recomputes HMAC, validates nonce/expiry, resolves handle. |
| Bot-token lifecycle | `SecretStorage` backed; never in logs. |
| Handle → (requestId, sessionId, directory) map | Persisted to `globalState`; survives extension reload. |
| Rate-limited verification | Max 100 verifications/sec; returns `rate_limited` if exceeded. |

### 2.2 SecurityModule — DELEGATES
| Delegated to | Purpose |
|---|---|
| **VS Code `SecretStorage`** (`SecretVault` wrapper) | OS-keyring-backed secret persistence. |
| **`globalState` (Memento)** (`HandleMap`) | Handle mapping persistence across reloads. |
| **`ContextProvider`** (NEW) | Provides sessionId/directory for signing. |

### 2.3 ApprovalStateManager — OWNS
| Responsibility | Notes |
|---|---|
| Pending-approval registration | TTL + persistence; rejects if `allowedTelegramUserIds` empty. |
| `callback_query_id` deduplication | First-wins consume. |
| Allowed-user authorization | Empty array = reject-all mode. |
| Decision validation + consume | Orchestrates verify + authz. |
| Expiry + status | TTL sweep + status methods. |
| Audit trail | Records userId, action, timestamp. |

### 2.4 ApprovalStateManager — DELEGATES
| Delegated to | Purpose |
|---|---|
| **SecurityModule** | Signature verification, handle resolution. |
| **`globalState`** (`PendingStore`, `DedupStore`) | Persistence across reloads. |
| **`AuditLog`** | Records security-relevant decisions. |

### 2.5 Dependency direction
```
Part 5 Orchestrator
   │  registerPending(OutboundApproval)
   ▼
ApprovalStateManager ──verifyCallback──▶ SecurityModule
   │  dedupe + authz + pending state
   ▼
Part 1 KiloBackendConnector ◀── replyToPermission ── Part 5
Part 2 TelegramProvider ◀── editMessage(ResolvedDecision) ── Part 5
```

---

## 3. Folder Structure
```
mko-ainotify/
├── src/
│   ├── core/
│   │   ├── security/
│   │   │   ├── SecurityModule.ts        # main class
│   │   │   ├── SecretVault.ts           # SecretStorage wrapper + fallback
│   │   │   ├── HmacSigner.ts            # pure crypto
│   │   │   ├── HandleMap.ts             # handle persistence
│   │   │   ├── envelope.ts              # 42-byte layout constants
│   │   │   ├── RateLimiter.ts           # NEW: rate limiting
│   │   │   ├── types.ts                 # types + interfaces
│   │   │   └── index.ts
│   │   ├── state/
│   │   │   ├── ApprovalStateManager.ts
│   │   │   ├── PendingStore.ts
│   │   │   ├── TtlSweeper.ts
│   │   │   ├── DedupStore.ts
│   │   │   ├── AuditLog.ts              # NEW
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   └── test/
│       ├── security/
│       │   ├── HmacSigner.test.ts
│       │   ├── SecretVault.test.ts
│       │   ├── HandleMap.test.ts
│       │   ├── SecurityModule.test.ts
│       │   ├── RateLimiter.test.ts      # NEW
│       │   └── doubles/
│       └── state/
│           ├── PendingStore.test.ts
│           ├── DedupStore.test.ts
│           ├── TtlSweeper.test.ts
│           ├── AuditLog.test.ts         # NEW
│           └── ApprovalStateManager.test.ts
```

---

## 4. Interfaces / API Contracts (TypeScript)

### 4.1 Envelope (`src/core/security/envelope.ts`)
```typescript
export type ApprovalAction = "approve" | "reject" | "approve_once" | "always_allow";

export const ActionCode = { approve: 0, reject: 1, approve_once: 2, always_allow: 3 } as const;
export const ENVELOPE_VERSION = 0x01;
export const ENVELOPE_SIZE = 42;
export const HMAC_TRUNCATE_BYTES = 16;
export const HMAC_INPUT_BYTES = 26;
export const HANDLE_BYTES = 8;

export function assertTokenLength(token: string): void {
  if (Buffer.byteLength(token, "utf8") > 64) {
    throw new SecurityError("token_malformed", "Token exceeds Telegram limit");
  }
}
```

### 4.2 Security types (`src/core/security/types.ts`)
```typescript
export interface HandleValue {
  requestId: string;
  sessionId: string;
  directory: string;
  action: ApprovalAction;
}

export type VerifyOutcome =
  | { status: "valid"; handle: Uint8Array; requestId: string; sessionId: string; directory: string; action: ApprovalAction; expiry: number; }
  | { status: "expired"; handle: Uint8Array; requestId: string; sessionId: string; directory: string; action: ApprovalAction; }
  | { status: "tampered" }
  | { status: "unknown_handle" }
  | { status: "malformed" }
  | { status: "rate_limited" };  // NEW

export type SecurityErrorKind = "token_missing" | "secret_missing" | "secret_unavailable" | "rotation_failed" | "token_malformed";

export interface ContextProvider {
  getContext(requestId: string): Promise<{ sessionId: string; directory: string }>;
}
```

### 4.3 SecurityModule
```typescript
export class SecurityModule {
  constructor(options: { vault: SecretVault; handleMap: HandleMap; contextProvider: ContextProvider; ... });
  signCallback(requestId: string, action: ApprovalAction): Promise<string>;  // REVISED
  verifyCallback(token: string): Promise<VerifyOutcome>;
  getBotToken(): Promise<string>;
  setBotToken(token: string): Promise<void>;
  deleteBotToken(): Promise<void>;
  rotateSecret(): Promise<void>;
  forgetHandle(requestId: string): Promise<void>;
}
```

### 4.4 RateLimiter (NEW)
```typescript
export class RateLimiter {
  constructor(options: { maxRequests?: number; windowMs?: number });
  tryEnter(): boolean;
  getStats(): { allowed: number; rejected: number };
}
```

### 4.5 AuditLog (NEW)
```typescript
export interface AuditRecord {
  requestId: string;
  callbackQueryId: string;
  userId: number;
  action: ApprovalAction;
  status: string;
  timestamp: number;
}

export class GlobalStateAuditLog implements AuditLog {
  record(entry: AuditRecord): Promise<void>;
  getAll(): Promise<AuditRecord[]>;
  prune(maxAgeMs: number): Promise<number>;
}
```

---

## 5. Security Model (Enhanced)

### 5.1 HMAC Envelope Correctness (VERIFIED)
- **Raw envelope**: 42 bytes (version=1 + action=1 + handle=8 + nonce=8 + expiry=8 + hmac=16)
- **Base64url encoding**: ceil(42 × 4/3) = 56 characters (no padding needed)
- **Telegram limit**: 64 bytes → 56 ≤ 64 ✅
- **Runtime check**: `assertTokenLength()` validates each token

### 5.2 Replay Protection (VERIFIED)
- 8-byte random handle (unique per requestId+action)
- 8-byte random nonce (bound into HMAC)
- 8-byte expiry timestamp (Unix seconds, UTC)
- Truncated HMAC-SHA256 (16 bytes = 128-bit, NIST SP 800-107 compliant)
- `callback_query_id` deduplication (first-wins, 24h TTL)
- Clock-skew tolerance: 60s default

### 5.3 Secrets Management (VERIFIED)
- HMAC secret + bot token in `SecretStorage` ONLY
- Never logged; redaction helper required
- Cross-platform fallback: `process.env.APPDATA` on Windows, `~/.config/mko-ainotify` on Unix
- Rotation: previous secret kept during grace period

### 5.4 Authorization (VERIFIED)
- `allowedTelegramUserIds` from settings
- Empty array = reject-all mode (no approvals accepted until configured)
- Telegram `CallbackQuery.from.id` is server-authenticated (cannot be forged)
- Fast pre-check in TelegramProvider; authoritative check in ApprovalStateManager

### 5.5 Rate Limiting (NEW) - DoS Protection
- 100 HMAC verifications per second sliding window
- Excess requests return `rate_limited` status (no crash)
- Stats available for diagnostics

### 5.6 Audit Trail (NEW)
- All accepted decisions recorded with userId, action, timestamp
- Persisted to `globalState` under `mko-ainotify.audit`
- 30-day retention (configurable)

---

## 6. Testing Strategy

### New tests for security enhancements
- `RateLimiter.test.ts` — sliding window enforcement
- `AuditLog.test.ts` — record/prune operations
- `SecurityModule.rateLimit.test.ts` — `rate_limited` outcome
- `HmacSigner.byteProof.test.ts` — runtime length assertion
- `OutboundApproval.directory.test.ts` — context provider integration

---

## 7. Milestones (Part 3) - Revised

| Milestone | Objective | Key Additions |
|---|---|---|
| M1 | Crypto + SecretVault + RateLimiter | `RateLimiter.ts`, runtime byte-length assertion |
| M2 | HandleMap + ContextProvider | `ContextProvider` interface, multi-handle support |
| M3 | SecurityModule core + AuditLog | Rate limiting, audit recording on accept |
| M4 | Pending + Dedup stores | Audit integration |
| M5 | ApprovalStateManager | Reject if `allowedTelegramUserIds` empty |
| M6 | Integration + Verification | Byte-length assertion, cross-part compatibility |

---

## 8. Task Backlog (Enhanced)

1. T-P3-01: Implement `envelope.ts` with constants
2. T-P3-02: Implement `HmacSigner.ts` with runtime validation
3. T-P3-03: Implement `types.ts` (security)
4. T-P3-04: Implement `SecretVault.ts` (cross-platform fallback)
5. T-P3-05: Write `HmacSigner.test.ts` + byte-proof
6. T-P3-06: Write `SecretVault.test.ts` + `FakeSecretStorage.ts`
7. T-P3-07: Implement `RateLimiter.ts` (NEW)
8. T-P3-08: Write `RateLimiter.test.ts` (NEW)
9. T-P3-09: Implement `HandleMap.ts` + `ContextProvider` (NEW)
10. T-P3-10: Write `HandleMap.test.ts`
11. T-P3-11: Implement `AuditLog.ts` (NEW)
12. T-P3-12: Write `AuditLog.test.ts` (NEW)
13-24: Remaining tasks with audit/rate-limit integration

---

## 9. Dependencies Summary

| From | Contract | Action Required |
|---|---|---|
| **Part 1** | `ExtensionSettings` | Extend with `dedupeTtlMs`, `clockSkewSec`, `sweepIntervalMs`, `secretGraceMs` |
| **Part 2** | `SecuritySeam.signCallback` | REVISED: `(requestId, action)` + `ContextProvider` |

---

## 10. Backward Compatibility

- Secret rotation uses grace period (`secretGraceMs`)
- Handle map versioning key if envelope evolves
- Extension deactivation clears handles on grace expiry

---

## Validation Scorecard

| Category | Score (/10) | Notes |
|----------|-------------|-------|
| **Architecture** | 9 | Clean separation. Resolved contract mismatch. Added rate limiting and audit. Clear dependency direction. |
| **Implementation Risk** | 8 | 64-byte limit corrected with runtime check. Rate limiting added. Secret fallback cross-platform. Contract alignment complete. |
| **Maintainability** | 9 | Small files, pure crypto, injectable seams. Audit trail for security review. Clear milestones. |
| **Production Readiness** | 8 | DoS protection via rate limiting. Audit trail. Recovery documented. All secrets in SecretStorage. |

### Top Issues Found & Resolved

| Severity | Issue | Resolution |
|---|---|---|
| **CRITICAL** | Contract mismatch: `signCallback(actionId)` vs `signCallback(requestId, sessionId, directory, action)` | REVISED: `signCallback(requestId, action)` with `ContextProvider` injection. |
| **HIGH** | Missing `directory` in OutboundApproval | REVISED: `ContextProvider` provides session/directory; handle map stores full routing tuple. |
| **HIGH** | Secret fallback not cross-platform | REVISED: Use `%APPDATA%/mko-ainotify/secrets.json.enc` on Windows. |
| **HIGH** | Missing DoS protection on HMAC verification | REVISED: Added RateLimiter (100 req/sec sliding window). |
| **MEDIUM** | Empty `allowedTelegramUserIds` undefined behavior | REVISED: Empty array = reject-all mode. |
| **MEDIUM** | No audit trail for approvals | REVISED: Added AuditLog with AuditRecord for each decision. |
| **MEDIUM** | No runtime envelope length validation | REVISED: Added `assertTokenLength()` in verification path. |

---

*Plan validated against: Telegram Bot API v10.2 (64-byte callback_data limit), VS Code Extension API (SecretStorage, globalState), Kilo Code 7.4.11 / opencode backend API, NIST SP 800-107 (truncated HMAC).*