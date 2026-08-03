# Mko-AINotify Priority Direction Validation

## Validated Synthesis

| Aspect | Status | Notes |
|--------|--------|-------|
| Kilo spawns opencode backend on localhost | ✅ CONFIRMED | Port+password in `~/.config/kilo/server.json` |
| No public VS Code extension API | ✅ CONFIRMED | `activate()` returns undefined, no exports |
| Companion extension via SDK works | ✅ CONFIRMED | Proven by registerToggleAutoApprove pattern |
| Telegram two-way via inline keyboards | ✅ CONFIRMED | Native callback_query support |
| No local machine public exposure | ✅ VALIDATED | Using getUpdates polling (no webhooks) |
| No external relay required | ✅ CORRECTED | getUpdates polling eliminates relay need |

## Recommended Architecture Shape

### Core Architecture: Companion Extension + Telegram Polling (No Relay)

```
┌──────────────────┐     ┌───────────────────────┐
│ Telegram Servers │←→  │ VS Code Extension       │
│ (Bot API)        │     │ (Extension Host)        │
└────────┬─────────┘     └───────────┬───────────┘
         │                           │
         │ 1. sendMessage              │
         │    (notification with       │
         │     inline keyboard)        │
         └─────────────────────────────┘
                                    │
                                    │ 2. getUpdates (polling)
                                    │    receives callback_query
                                    ▼
         ┌─────────────────────────────────────┐
         │ 3. SDK: client.permission.reply()   │
         │    → Kilo opencode backend            │
         └─────────────────────────────────────┘
```

### Key Decisions

1. **Telegram bot runs inside VS Code extension host** - Simplifies deployment, keeps bot token in SecretStorage, no separate process management needed.

2. **getUpdates polling (not webhooks)** - Eliminates need for public port exposure or cloud relay. Extension makes outbound HTTPS only to `api.telegram.org`. Polling interval 1-2s for responsiveness.

3. **HMAC-signed callback_data** - Structure: `HMAC(32) + nonce(8) + expiry(8) + action_id(remaining)` within 64-byte Telegram limit.

4. **SecretKeyManager abstraction** - Uses VS Code SecretStorage (OS keyring integration) with encrypted file fallback.

## Component Decomposition (5 Modules)

### 1. KiloBackendConnector
- **Purpose**: SDK integration with opencode backend
- **Responsibilities**: 
  - Discover active session port from `~/.config/kilo/server.json` or process inspection
  - Maintain SSE connection to `permission.asked` events
  - Call `client.permission.reply()` for approvals
- **Interface**: `subscribeToPermissionEvents()`, `replyToPermission(requestID, reply)`

### 2. TelegramProvider
- **Purpose**: Notification delivery and response reception
- **Responsibilities**:
  - Send messages with inline keyboard buttons
  - Poll Telegram Bot API via `getUpdates`
  - Parse callback_query responses
  - Answer callback queries for user feedback
- **Interface**: `sendApprovalRequest(approval)`, `pollForResponses()`, `validateCallback(callback_data)`

### 3. ApprovalStateManager
- **Purpose**: Track approval lifecycle and prevent replays
- **Responsibilities**:
  - Store pending approvals with timestamps
  - Validate HMAC signatures on incoming callbacks
  - Deduplicate callback_query_id to prevent double-processing
  - Expire and reject stale approvals
- **Interface**: `registerPending(approval)`, `validateAndConsume(response)`, `expireOld(timeoutMs)`

### 4. SecurityModule
- **Purpose**: Cryptographic operations and secret management
- **Responsibilities**:
  - Generate/store HMAC secret for callback signing
  - Sign callback_data payloads
  - Verify callback signatures
  - Manage bot token in SecretStorage
- **Interface**: `signCallback(approvalID, action)`, `verifyCallback(token, signature)`, `getBotToken()`

### 5. ConfigManager
- **Purpose**: Configuration and settings management
- **Responsibilities**:
  - Read Kilo config files
  - Track worktree/session configurations
  - Manage extension settings (polling interval, expiry time)
  - Validate configuration on startup
- **Interface**: `getActivePort()`, `getConfig()`, `watchConfigChanges()`

## Mandatory Risks to Mitigate

| Risk | Mitigation Strategy |
|------|---------------------|
| **SDK/Backend Version Drift** | Bundle SDK version must match opencode backend. Investigate if SDK types are versioned with backend releases. Require version check on startup. |
| **Port/Session Discovery** | Multiple Kilo instances may use different ports. Parse `server.json` dynamically or watch for process argument changes. Map worktree IDs to correct ports. |
| **Callback Race with Multiple Clients** | Use `callback_query_id` as primary dedupe key. Store processed IDs in extension state with TTL. Only first response to requestID succeeds. |
| **Telegram Rate Limiting** | Respect API limits: 1-3 req/sec for getUpdates. Implement exponential backoff. Queue unsent notifications. |
| **Approval Timeout/Orphaned Requests** | Auto-reject approvals after configurable TTL (default 30 min). Clean up stale state. Provide visual indicator in VS Code status bar. |
| **Token Compromise** | Store token only in SecretStorage. Provide token rotation command. Never log or expose token in plaintext. |

## Open Questions for Implementation Planning

1. **Worktree Port Management**: How does Agent Manager map worktrees to backend ports? Must the companion connect to each worktree's opencode instance separately?

2. **SDK Compatibility**: Is `@kilocode/sdk/v2` version-locked to the bundled opencode backend? Can it connect to any opencode version?

3. **Permission Event Structure**: The research shows `metadata` may contain command details - validate exact field names for `metadata.command` and `metadata.args`.

4. **Session Isolation**: When multiple Kilo sessions are active, do permission requestIDs collide? Must responses include sessionID for routing?

5. **Extension Activation Timing**: Kilo activates on `onStartupFinished`. How does companion ensure it's ready before permission events arrive?