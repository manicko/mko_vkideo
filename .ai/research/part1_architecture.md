# Part 1: Backend Connector & Config/Port Discovery Architecture

## 1. Internal Architecture: Connection Lifecycle

### State Diagram (HIGH confidence - verified via source)
```
┌─────────────┐
│    INIT     │
└──────┬──────┘
       │ discover port
       ▼
┌─────────────┐      ┌─────────────────────┐
│ DISCOVERING │─────▶│    DISCOVERED       │
└─────────────┘      │ port, password, dir  │
       │ Auth fail   └───────┬───────────────┘
       │                     │ connect SSE
       │                     ▼
       │              ┌─────────────┐
       │              │ CONNECTING  │
       │              └──────┬──────┘
       │                     │ SSE stream open
       │                     ▼
       │              ┌─────────────┐      ┌─────────────┐
       │              │ SUBSCRIBED  │◀───▶│ KEEPALIVE   │
       │              │ listening   │      │ ping every  │
       │              │ to events   │      │ 30s         │
       │              └──────┬──────┘      └─────────────┘
       │                     │ disconnect
       │                     ▼
       │              ┌─────────────┐
       │              │ RECONNECT   │
       │              │ backoff: 1s,2s,4s,8s max 30s
       │              └──────┬──────┘
       │                     │
       └───────────────────────┘ (loop back to CONNECTING)
```

**Connection Steps:**
1. **Port Discovery**: Read `~/.config/kilo/server.json` (Linux/Mac) or `C:\Users\<user>\.config\kilo\server.json` (Win). If not found, scan process list for `kilo serve --port <num>`.
2. **Auth (Basic)**: Username: `kilo`, Password: from `server.json.password` or `KILO_SERVER_PASSWORD` env var. Auth header: `Base64(kilo:<password>)`.
3. **Connect SSE**: `GET http://127.0.0.1:{port}/global/event?directory=<encoded_dir>` with `x-kilo-directory` header or query param.
4. **Subscribe**: Filter events where `payload.type === "permission.asked"` or `"permission.v2.asked"`.
5. **Keepalive**: SDK does not natively ping; implement heartbeat by tracking `server.connected` events or periodic config fetch.
6. **Reconnect**: On SSE disconnect or 4xx/5xx, exponential backoff starting at 1s, max 30s.

## 2. Layer Interaction Diagrams (ASCII)

### 2.1 Connector → ApprovalStateManager (Normalized Event Emission)
```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  KiloBackendConnector│     │                     │     │                     │
│                     │     │ ApprovalStateManager│     │                     │
├─────────────────────┤     ├─────────────────────┤     │   TelegramProvider  │
│ SSE stream          │─────▶│ PendingApproval(id,   │────▶│ (next layer)        │
│   payload.type      │      │  sessionID, perm,    │     │                     │
│   = "permission.asked"│   │  patterns, metadata, │     │                     │
│                     │      │  always, tool)       │     │                     │
│   ↓ extract &       │      │ register()           │     │                     │
│   normalize         │      │ validateHMAC()       │     │                     │
│                     │      │ dedupe(callback_id)  │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### 2.2 ApprovalStateManager → Connector (Reply Path)
```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│                     │     │ SecurityModule      │     │ KiloBackendConnector│
│   TelegramProvider  │     │ (validates HMAC)    │     │ (calls SDK)         │
│   callback_query    │────▶│ verify(signature)   │────▶│ client.permission.  │
│   callback_data     │     │ ←─ passes if valid ──┘     │ reply(requestID,    │
│                     │                                 │  reply: "once" |    │
└─────────────────────┘                                 │  "always" |         │
                                                          │  "reject")         │
                                                          └─────────────────────┘
                                                                 ↓
                                                          Backend resolves Deferred
```

### 2.3 ConfigManager → Connector (Config Feed)
```
┌─────────────────────┐     ┌─────────────────────┐
│   ConfigManager      │     │ KiloBackendConnector│
├─────────────────────┤     ├─────────────────────┤
│ getActivePort()      │────▶│ Reads:              │
│   - parse server.json│      │   port: number       │
│   - fallback process │      │   password: string   │
│     scanning         │      │ getDirectoryWorkspaces() │
│ watchConfigChanges() │     │   - map sessions to  │
│   - fs.watch on      │      │     their ports      │
│     ~/.config/kilo/  │      │     (Agent Manager)  │
└─────────────────────┘     └─────────────────────┘
```

## 3. Key Integrations & Exact Data Contracts

### 3.1 server.json Schema (Cross-platform)
```json
{
  "port": 4097,                    // OS-assigned ephemeral port
  "password": "a1b2c3d4e5f6...",   // 32-char hex from KILO_SERVER_PASSWORD
  "version": "7.4.11",             // Kilo version string
  "pid": 12345                     // Backend process PID (useful for validation)
}
```

**Paths:**
- Linux/Mac: `~/.config/kilo/server.json` → `path.join(os.homedir(), ".config/kilo/server.json")`
- Windows: `%USERPROFILE%\.config\kilo\server.json` → `C:\Users\<user>\.config\kilo\server.json`

### 3.2 SSE `permission.asked` Event (v2 types)
**From types.gen.ts (EventPermissionAsked / EventPermissionV2Asked):**
```typescript
// EventPermissionAsked
{
  id: string,           // Global event ID
  type: "permission.asked",
  properties: {
    id: string,         // Request ID (primary key for reply)
    sessionID: string,  // Originating session
    permission: string, // Tool name: "bash", "edit", "read", etc.
    patterns: string[], // File patterns being accessed
    metadata: {         // Opaque - may contain command/args for bash
      [key: string]: unknown
    },
    always: string[],   // Selected "always allow" patterns
    tool?: {
      messageID: string,
      callID: string
    }
  }
}

// EventPermissionV2Asked (newer)
{
  id: string,
  type: "permission.v2.asked",
  properties: {
    id: string,
    sessionID: string,
    action: string,
    resources: string[],
    save?: string[],
    metadata?: { [key: string]: unknown },
    source?: { type: "tool", messageID: string, callID: string }
  }
}
```

### 3.3 `client.permission.reply()` Request/Response
**v1 Global Reply (deprecated):**
```typescript
// POST /permission/{requestID}/reply
Request: {
  path: { requestID: string },
  body: {
    reply: "once" | "always" | "reject",
    message?: string
  },
  query?: { directory?: string, workspace?: string }
}
Response: 200 OK with boolean body (true)
// Error: 404 NotFoundError if requestID invalid/expired
```

**v2 Session-scoped Reply (preferred):**
```typescript
// POST /api/session/{sessionID}/permission/{requestID}/reply
Request: {
  path: { sessionID: string, requestID: string },
  body: {
    reply: "once" | "always" | "reject",
    message?: string
  }
}
Response: 204 No Content
// Errors: 400 InvalidRequestError, 401 UnauthorizedError, 404 NotFoundError
```

### 3.4 Multiple Kilo Sessions / Agent Manager Worktrees
**Architecture (source: agent-manager.md):**
- Each Agent Manager worktree gets a **deterministic port** derived from its path hash
- Formula: `port = 4000 + (cksum(worktree_path) % 1000)` [0. agent-manager.md]
- The companion extension must:
  - Track ALL active worktrees via `/worktree` endpoint or process inspection
  - Create **one SSE connection per worktree port** (no fan-out on single connection)
  - OR use a single global connection that receives ALL events with filtering by `sessionID`

**Recommendation:** Use single global SSE connection with `directory` param, filter events by `sessionID` matching project workspace.

## 4. Connection Recovery Design

| Scenario | Detection | Recovery Action |
|----------|-----------|---------------|
| **Backend restart** | SSE disconnect + health check fails | Re-read server.json, exponential backoff reconnect |
| **Port changes** (new session) | Old port health fails, new port detected via process scan | Close old SSE, open new connection, replay any missed events via `/permission` list |
| **Password rotates** | 401 Unauthorized on SSE or API call | Re-read server.json, update auth header, reconnect |
| **Extension host reload** | `activate()` called again | Wait for `onStartupFinished` to ensure Kilo is initialized; read fresh server.json |
| **Worktree added** | Watch for process spawn or poll `/worktree` | Create new connection for that worktree's port |

**Recovery Flow:**
1. On disconnect/error, store pending approvals in VS Code global state
2. On reconnect, call `client.permission.list()` with directory filter
3. Compare list with stored pending state; emit any missing as `permission.asked`
4. Clean up stale entries (TTL > 30 min → auto-reject)

## 5. Risks & Mitigations

| Risk | Confidence | Mitigation |
|------|------------|------------|
| **SDK/Backend version drift** | HIGH | Bundle matching SDK version; verify on startup via `/global/health` version check; log warning on mismatch |
| **Race with multiple SDK clients** | MEDIUM | First valid reply wins (backend uses Deferred); store `callback_query_id` as dedupe key with TTL; ignore duplicate requestIDs |
| **Missed events during reconnect window** | HIGH | Poll `/permission` list on reconnect; keep 30s event buffer in memory; mark approvals stale after TTL |
| **Password on disk (server.json)** | HIGH | File permissions 0600; never log; clear on uninstall; optional OS keyring fallback |
| **Worktree port collision** | LOW | Deterministic port assignment reduces collision; monitor logs for "address in use" errors |

## Sources
- [1] Kilo SDK types.gen.ts: lines 4717-4733 (EventPermissionAsked), 4768-4781 (EventPermissionV2Asked), 8782-8795 (PermissionReplyData), 15465-15476 (V2SessionPermissionReplyData)
- [2] TESTING.md: Backend startup and auth patterns (`kilo:{password}` Basic auth)
- [3] agent-manager.md: Worktree port assignment formula (4000 + cksum % 1000)
- [4] permission/index.ts: Event schemas and Deferred-based reply handling