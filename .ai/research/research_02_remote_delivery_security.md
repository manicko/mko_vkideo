# Research: Remote Approval Delivery Security

**Date:** 2026-07-20  
**Focus:** How remote approvals from mobile phones can safely reach local VS Code instances

---

## 1. Delivery Channel Comparison

| Channel | Complexity | Latency | Reliability | Exposure Risk | Portability | Notes |
|---------|------------|---------|-------------|---------------|-------------|-------|
| **Local WebSocket Server (localhost)** | High | Low | Poor (same network only) | High if exposed publicly | Excellent | Requires port forwarding/tunnel; phone must reach desktop |
| **Local HTTP Callback Server** | High | Low | Poor (same network only) | High if exposed publicly | Excellent | Same limitations as WebSocket; NAT/firewall traversal issues |
| **Long-polling against Relay** | Medium | Medium (2-5s) | Good | Low | Excellent | Extension polls cloud relay; bot pushes to relay |
| **Push via Relay Service** | Medium | Low-Medium | Good | Low | Excellent | Preferred: bot pushes to relay, extension maintains persistent connection |
| **MCP Server** | Medium-High | Variable | Good | Low-Medium | Good | Can be stdio (local only) or HTTP (requires relay) |

### Key Findings:
- **Same-network only solutions (WebSocket/HTTP server)** fail when user is away from computer
- **Telegram webhooks require HTTPS** on ports 443, 80, 88, or 8443 with valid/self-signed cert
- **NAT/firewall traversal** without exposing localhost requires a relay/tunnel service
- **Self-signed certificates** are supported by Telegram but require manual cert management

---

## 2. Security Model Requirements

### Authentication
- **Telegram user identity** is enforced server-side via `CallbackQuery.from` - cannot be forged
- **Bot token** must be stored securely (VS Code SecretStorage using OS keyring)
- **Callback data integrity**: Telegram allows up to 64 bytes in `callback_data` field
- **Recommended**: Use HMAC-SHA256 signature on callback data with server-side secret
  - Formula: `Base64Url(HMAC(key, nonce + expiry + data) + nonce + expiry + data)`
  - Max ~57 bytes usable after 32-byte HMAC + 8-byte nonce + 8-byte expiry

### Replay Protection
- **Timestamp-based expiry**: Embed UTC expiry in callback data (e.g., 30-minute window)
- **Nonce**: Use random 8-byte nonce to prevent replay attacks
- **Telegram constraint**: `answerCallbackQuery` called twice raises `QUERY_ID_INVALID` in Bot API 8.0+
- **Implementation**: Server-side deduplication via `callback_query_id` unique index in storage

### Secret Storage Options (Desktop)
| Method | Platform | Security | Recommendation |
|--------|----------|----------|----------------|
| VS Code SecretStorage | All | OS keyring (Keychain/Windows DPAPI/KWallet) | **Recommended** - officially supported |
| node-keytar | All | OS keyring | Deprecated - VS Code removed shim in 2023 |
| Encrypted config file | All | File-level encryption | Fallback if SecretStorage unavailable |

### Transport Encryption
- **Relay connection (extension to relay)**: TLS via public certificate
- **Local connection only**: Self-signed cert on localhost + certificate upload to Telegram
- **MCP stdio**: No encryption needed (local process communication)

---

## 3. Architecture Comparison

### Fully Local Design
```
Phone (Telegram) → [Same Network] → Local Webhook Server (TLS) → VS Code Extension
```
**Pros:** No third-party dependency, lowest latency  
**Cons:** Requires phone on same network, port exposure, complex cert management  
**Risk:** High exposure if NAT traversal misconfigured

### Relay/Middleware Design
```
Phone → Telegram → Cloud Relay ← Outbound TLS → VS Code Extension
                ↑
           Bot pushes approval
```
**Pros:** Works from any network, no port forwarding, clean separation  
**Cons:** Third-party relay dependency, small latency overhead  
**Risk:** Low - only outbound HTTPS from desktop

---

## 4. Telegram Bot API Specifics

### Two-Way Communication Flow
1. **Outbound (approval request)**: Use long-polling `getUpdates` or server-side push
2. **Inbound (approval response)**:
   - Send inline keyboard with callback data
   - User presses button → Telegram sends `callback_query` to bot
   - Bot processes and pushes decision to relay/cloud store
   - Extension receives via polling or persistent connection

### Callback Query Constraints
- `callback_data` max: **64 bytes UTF-8**
- `answerCallbackQuery` required within timeout or progress indicator shows forever
- `secret_token` header supported for webhook verification (set via `setWebhook`)
- Webhooks only on ports: **443, 80, 88, 8443**

---

## 5. Recommended Secure Architecture

### Design: Cloud Relay with Persistent Polling

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│ Telegram        │       │ Relay Service      │       │ VS Code Extension   │
│ (Mobile Phone)  │       │ (Cloud/Relay)    │       │ (Local)             │
└────────┬────────┘       └────────┬─────────┘       └──────────┬──────────┘
         │                          │                            │
         │ Inline Keyboard            │                            │
         │ callback_data              │                            │
         │ (signed + expiry)          │                            │
         └────────────────────────────→                            │
                                      │                            │
                                      │ Push approval              │
                                      │ to queue                   │
                                      └───────────────────────────→
                                        (outbound HTTPS only)       │
                                                                Poll
                                                                  │
                                              Notification          │
                                              (command details)     │
                                        ←───────────────────────────┘
```

### Security Controls
1. **Authentication**: Bot token in VS Code SecretStorage, Telegram user_id verified
2. **Replay Protection**: Timestamp expiry (30 min), random nonce, server dedupe
3. **Message Integrity**: HMAC-SHA256 on callback_data using stored secret
4. **Transport**: HTTPS to relay service, no public port exposure on desktop
5. **Approval Format**: `{hmac}.{nonce}.{expiry}.{action_id}` ≤ 64 bytes

---

## 6. Identified Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Bot token compromise | High | VS Code SecretStorage, rotate tokens |
| Replay attack on approval | Medium | Timestamp expiry + nonce + deduplication |
| Man-in-the-middle on relay | Medium | TLS + certificate pinning on relay endpoint |
| Relay service compromise | High | Use reputable relay or self-hosted (hookly/bifrost) |
| Missing approval (timeout) | Medium | Approve-once fallback, auto-rejection after TTL |
| NAT/local network required | Blocking | Use relay; same-network is optional enhancement |

---

## 7. Recommended Approach

**Use a relay-based architecture** where:
1. VS Code extension **polls a cloud relay** (or uses persistent HTTPS connection)
2. Telegram bot **pushes approvals to the same relay** via HTTP API
3. **No ports opened on local machine** - all connections are outbound HTTPS
4. **Secrets stored in VS Code SecretStorage** (OS keyring integration)
5. **Callback data signed with HMAC** and includes expiry nonce action_id

This design satisfies:
- ✅ Works when phone is on different network
- ✅ No public exposure of local machine
- ✅ Authenticated approvals (Telegram user_id + HMAC)
- ✅ Replay protection (expiry + nonce + dedupe)
- ✅ Cross-platform (Windows/macOS/Linux via SecretStorage)

