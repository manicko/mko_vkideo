# Mko-AINotify Part 3: Security & Approval State Requirements

## 1. Functional Requirements

### SecurityModule (FR-1 to FR-6)

**FR-1: HMAC Secret Generation & Storage**
- Generate a cryptographically-secure 256-bit HMAC secret on first run or rotation
- Store secret exclusively in VS Code `SecretStorage` (OS keyring: Keychain/dpapi/KWallet)
- Provide `getHmacSecret(): Promise<string>` returning raw hex/base64 secret
- Never log, expose, or cache the secret in plaintext memory

**FR-2: Sign Callback Data (42-Byte Envelope)**
- Create `signCallback(actionId, action): Promise<string>` producing opaque token ≤64 bytes
- Envelope structure (raw 42 bytes):
  | Field | Bytes | Description |
  |-------|-------|-------------|
  | version | 1 | Protocol version (currently 0x01) |
  | action | 1 | Action enum (0=approve, 1=reject, 2=approve_once, 3=always_allow) |
  | handle | 8 | Random handle mapping to (requestId, sessionId) |
  | nonce | 8 | Random bytes for replay protection |
  | expiry | 8 | Unix timestamp (seconds) UTC |
  | hmac | 16 | Truncated HMAC-SHA256 (128-bit per NIST SP 800-107) |
- Encode: `base64url(rawEnvelope)` → 56 chars ≤ 64-byte Telegram limit
- Store handle→(requestId,sessionId,action) mapping in persistent Memento

**FR-3: Verify Callback Signatures**
- `verifyCallback(token): Promise<VerifiedCallback | null>` extracting handle, validating hmac/nonce/expiry
- Return `{requestId, sessionId, action}` if valid; `null`/throw on invalid/tampered/expired
- Reject callbacks where `Date.now()/1000 > expiry + 1` (clock-skew tolerance configurable)

**FR-4: Bot Token Management**
- `getBotToken(): Promise<string>` retrieving from `SecretStorage`
- `storeBotToken(token): Promise<void>` storing securely
- `deleteBotToken(): Promise<void>` for rotation/revoke
- Throw `ProviderError('token_missing')` if unset during operations

**FR-5: Authorized User Management**
- `getAuthorizedUserIds(): Promise<number[]>` returning configured admin Telegram IDs
- Support array of IDs (single admin or multi-admin mode)
- Cache in-memory for fast allow-list check at callback time

**FR-6: Secret Rotation Support**
- `rotateHmacSecret(): Promise<void>` generating new secret, invalidating old handles
- New secret stored in SecretStorage, migration path documented

### ApprovalStateManager (FR-7 to FR-10)

**FR-7: Register Pending Approvals**
- `registerPending(approval): Promise<void>` storing with ISO timestamp + TTL
- Key by `requestId` from Kilo backend; store full `OutboundApproval` + metadata
- TTL derived from `ExtensionSettings.approvalTtlMs` (default 30 min)

**FR-8: Validate & Consume Incoming Decisions**
- `consume(callbackQueryId): Promise<DecisionRecord | null>` for deduplication
- First call returns decision; subsequent calls return `null` (already processed)
- `DecisionRecord`: `{callbackQueryId, requestId, sessionId, userId, status}`

**FR-9: Expire Stale Approvals**
- `expireOld(ttlMs): Promise<number>` removing approvals older than TTL
- Cleanup on extension activation and periodic intervals (e.g., every 5 min)
- Return count of expired entries for logging

**FR-10: Handle Resolution for Callback Routing**
- On verified callback, resolve handle to (requestId, sessionId) via SecurityModule mapping
- Emit resolved decision to orchestrator for backend reply routing

---

## 2. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|----------|-------------|--------|-------|
| **Security** | HMAC verification latency | <1ms | Signed token validation must not block event loop |
| **Security** | Secret storage | OS keyring via SecretStorage | Never in plain files, logs, or memory longer than needed |
| **Security** | No token leakage | All secrets redacted in logs | Use `redactToken()` helper in logger |
| **Cross-Platform** | SecretStorage support | Windows/macOS/Linux | Electron safeStorage API / DKE for web |
| **Reliability** | Handle map persistence | Survives VS Code reload | Store in `globalState` (extension Memento) |
| **Reliability** | Deduplicate window | ≥24 hours | Telegram updates cached server-side |
| **Memory** | State bounds | ≤5MB | Bounded map entries, TTL cleanup |

---

## 3. Goals & Success Criteria

### Primary Goals
1. **Authenticated Approvals**: Only verified Telegram users with valid HMAC tokens can approve
2. **Replay Protection**: Nonce + expiry + handle uniqueness prevents replay attacks
3. **No Token Leakage**: Bot token/HMAC secret never logged, only via `SecretStorage`
4. **Handle Routing**: 8-byte handle maps to correct `requestId`/`sessionId` for multi-worktree support

### Success Criteria
- Telegram `callback_data` passes HMAC verification in 1ms (p95)
- All secrets stored via `SecretStorage` (verified by audit)
- Extension restarts preserve handle→requestId mapping (survives `globalState` persistence)
- Unauthorized user callbacks rejected silently with no backend impact
- Token rotation flow documented and tested

---

## 4. Responsibility Zones

### SecurityModule OWNS
| Responsibility | Notes |
|----------------|-------|
| HMAC secret generation/storage | Uses VS Code `SecretStorage` only |
| `signCallback()` envelope creation | Creates 42-byte envelope, generates handle |
| `verifyCallback()` signature validation | Extracts handle, verifies hmac/nonce/expiry |
| Bot token lifecycle | `getBotToken()`, `storeBotToken()`, `deleteBotToken()` |
| Handle→(requestId,sessionId,action) mapping | Persists to `globalState` |

### SecurityModule DELEGATES
| Delegated To | Purpose |
|--------------|---------|
| **VS Code SecretStorage** | OS-keyring backed secret persistence |
| **ApprovalStateManager** | Receives verified handle for persistence; consumes mapping on callback |

### ApprovalStateManager OWNS
| Responsibility | Notes |
|----------------|-------|
| Pending approval registration | TTL, timestamps, requestId → approval data |
| `callbackQueryId` deduplication | First-wins, TTL cleanup |
| Expired approval rejection | `expireOld()` method |
| Decision status resolution | Maps verified callback to backend reply |

### ApprovalStateManager DELEGATES
| Delegated To | Purpose |
|--------------|---------|
| **SecurityModule** | `signCallback()` for tokens, `verifyCallback()` for validation, handle resolution |
| **KiloBackendConnector** | `replyToPermission()` after decision resolution |

---

## 5. Key Integrations & Contracts

### VS Code SecretStorage API
```typescript
import { SecretStorage } from "vscode";

// Access via extension activate():
const secretStorage: SecretStorage = context.secrets;

// Methods:
await secretStorage.store("bot-token", token);     // Store bot token (string)
await secretStorage.get("bot-token");              // Returns string | undefined
await secretStorage.delete("bot-token");           // Delete token
await secretStorage.store("hmac-secret", secret);   // Store HMAC secret (hex/base64)
await secretStorage.get("hmac-secret");
await secretStorage.delete("hmac-secret");
```
**Source**: VS Code Extension API — leverages OS keyring (Keychain/Windows DPAPI/KWallet) [1]

### HMAC-SHA256 Construction
```typescript
// Node.js Web Crypto API (available in Electron)
const { subtle } = globalThis.crypto;

const key = await subtle.importKey(
  "raw",
  new TextEncoder().encode(secret),
  { name: "HMAC", hash: "SHA-256" },
  false,
  ["sign"]
);

const signature = await subtle.sign("HMAC", key, dataBuffer);
// Returns ArrayBuffer, convert to Uint8Array
```
**Source**: Node.js Web Crypto HMAC — https://nodejs.org/api/webcrypto.html [2]

### Base64url Encoding
```typescript
// Node.js native (v15.7.0+):
const token = Buffer.from(envelopeBuffer).toString("base64url");
// Produces URL-safe string without '=' padding

// Falls back to:
const token = btoa(String.fromCharCode(...bytes))
  .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
```
**Source**: Node.js Buffer `base64url` encoding RFC 4648 §5 [3]

### 42-Byte Envelope Layout
```
Offset  Size  Field       Description
------  ----  ----        -----------
0       1     version     Protocol version (0x01)
1       1     action      Action enum (0-3)
2       8     handle      Random uint48 (2^48 unique values)
10      8     nonce       Random bytes (replay protection)
18      8     expiry      Unix timestamp big-endian uint48
26      16     hmac        First 128 bits of HMAC-SHA256
------  ----  ----
Total: 42 bytes → base64url = 56 chars ≤ 64-byte Telegram limit
```

### TTL Configuration
- Default: 30 minutes (`1800000ms`)
- Configurable via `ExtensionSettings.approvalTtlMs`
- Clock-skew tolerance: reject if `now > expiry + 1` (config: `clockSkewSec`)

---

## 6. Open Questions for Planner

1. **Secret Rotation**: Should rotation invalidate all pending handles immediately, or support grace period with both secrets active?

2. **Multiple Admins**: Current design supports `number[]` for `allowedTelegramUserIds`. Should we track *which* admin approved for audit purposes, or just accept first-valid?

3. **Clock-Skew Tolerance**: What tolerance window (default 1-5 seconds) to handle device time drift between phone and desktop? Configurable or fixed?

4. **Handle Map Persistence Scope**: `globalState` survives extension reloads but is tied to single machine. For multi-machine setups, should handle→requestId be recreated on restart? How to handle approvals in-flight during restart?

5. **HMAC Truncation Verification**: 16-byte (128-bit) truncation meets NIST SP 800-107 recommendations, but should we document collision bounds for ~1000 active handles context?

6. **Pending State Recovery**: If extension restarts mid-approval, should we detect orphaned Kilo permission requests and re-queue notifications, or rely on Kilo's internal timeout?

---

## Sources

[1] VS Code SecretStorage API — https://code.visualstudio.com/api/references/vscode-api#SecretStorage
[2] Node.js Web Crypto HMAC — https://nodejs.org/api/webcrypto.html#cryptosubtlehmac
[3] Node.js Buffer base64url — https://nodejs.org/api/buffer.html#buffer_buffers_and_character_encodings