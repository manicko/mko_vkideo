# Part 1: Backend Connector & Config/Port Discovery Requirements

## 1. Functional Requirements (FR)

### KiloBackendConnector
| ID | Requirement |
|----|-------------|
| FR-1.1 | Discover active opencode backend port by reading `~/.config/kilo/server.json` (cross-platform path resolution) |
| FR-1.2 | Establish SSE connection to `http://127.0.0.1:{port}/global/event` with Basic Auth (`kilo:{password}`) |
| FR-1.3 | Subscribe to and filter `permission.asked` and `permission.v2.asked` SSE events |
| FR-1.4 | Extract permission event data: requestID, sessionID, permission/tool name, patterns, metadata (command/args) |
| FR-1.5 | Call SDK `client.permission.reply({ sessionID, requestID, reply })` with "once", "always", or "reject" |
| FR-1.6 | Handle SSE disconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s) retry strategy |
| FR-1.7 | Recover missed events on reconnect via `client.permission.list()` with directory filtering |
| FR-1.8 | Support multiple concurrent worktree sessions by maintaining separate port mappings |

### ConfigManager
| ID | Requirement |
|----|-------------|
| FR-2.1 | Read `server.json` from cross-platform paths: `~/.config/kilo/server.json` (Unix) or `%USERPROFILE%\.config\kilo\server.json` (Windows) |
| FR-2.2 | Validate config schema: port (1-65535), password (32-char hex string), pid (positive integer) |
| FR-2.3 | Watch config file changes via FileSystemWatcher to detect port/password rotation |
| FR-2.4 | Provide extension settings: polling interval (1-5s), approval expiry (default 30 min), allowed Telegram user IDs array |
| FR-2.5 | Expose `getActivePort()` returning current port or null if unavailable |
| FR-2.6 | Track worktree-to-port mapping for Agent Manager sessions |
| FR-2.7 | Validate config on extension activation and log errors for malformed/invalid configs |
| FR-2.8 | Return typed configuration objects (Pydantic models) for all consumers |

## 2. Non-Functional Requirements (NFR)

| NFR | Description |
|-----|-------------|
| NFR-1 | **Reliability**: SSE connection must auto-reconnect within 30s of backend restart; missed events recovered via list polling |
| NFR-2 | **Latency**: Event detection to notification dispatch < 2s; SSE stream maintains < 100ms event-to-handler lag |
| NFR-3 | **Cross-platform**: Support Windows 10/11, macOS 12+, Ubuntu 20.04+/Debian 11+; use Node.js `os.homedir()` for path resolution |
| NFR-4 | **Resource**: SSE connection uses single HTTP keep-alive; memory < 5MB for pending state; no persistent background threads outside VS Code host |
| NFR-5 | **Security**: Never log password; file stored with 0600 permissions; all requests use HTTPS/localhost only |
| NFR-6 | **Observability**: Structured logging with logger name; status bar indicator shows connection state (connected/reconnecting/error) |
| NFR-7 | **Graceful degradation**: If config missing, fall back to process scanning; if SSE fails, report error without crashing extension host |

## 3. Goals & Success Criteria

### Primary Goals
1. **Real-time event capture**: 100% of permission.asked events intercepted within 1 second of emission
2. **Reliable reply delivery**: Approval decisions delivered to backend within 4s of receipt
3. **Zero config loss**: No missed approvals during backend restarts longer than 30s

### Success Criteria
- [ ] Extension activates and connects within 5s of VS Code startup complete
- [ ] SSE stream remains stable for 8+ hours of continuous operation
- [ ] Config validation rejects invalid JSON, out-of-range ports, malformed passwords
- [ ] Status bar shows "AINotify: Connected" / "Reconnecting..." / "Error: {reason}"
- [ ] All pending approvals survive extension host reload via VS Code global state

## 4. Responsibility Zones

### KiloBackendConnector OWNS
- SSE subscription lifecycle (connect, disconnect, reconnect)
- Event normalization (converting raw SSE to standard PermissionRequest format)
- SDK client initialization and auth header management
- Reply execution via `client.permission.reply()`

### KiloBackendConnector MUST NOT
- Store or validate config files (delegated to ConfigManager)
- Parse HMAC signatures or manage secrets (delegated to SecurityModule)
- Track pending approval TTL or deduplicate callbacks (delegated to ApprovalStateManager)
- Send Telegram notifications (delegated to TelegramProvider)

### ConfigManager OWNS
- Config file discovery and parsing
- Cross-platform path resolution
- FileSystemWatcher for config changes
- Extension settings retrieval from VS Code configuration API

### ConfigManager MUST NOT
- Make SDK API calls (no connection logic)
- Process permission events (no event handlers)
- Validate HMAC signatures (SecurityModule responsibility)
- Store pending approvals or manage their lifecycle

### Boundaries vs Other Modules
| Module | Connector Boundary | ConfigManager Boundary |
|--------|------------------|----------------------|
| TelegramProvider | Emits normalized PermissionRequest events | None |
| ApprovalStateManager | Consumes normalized events; provides reply calls with validated sessionID/requestID | Receives config on startup; no runtime config access |
| SecurityModule | Supplies password for auth header (ConfigManager reads it) | Supplies bot token path for SecretStorage access |

## 5. Key Integrations & Contracts

### Kilo SDK @kilocode/sdk/v2
```typescript
// Connection
import { createKiloClient } from "@kilocode/sdk/v2/client";
const client = createKiloClient({
  port: number,
  password: string
});

// SSE Event Stream
for await (const event of client.global.event({ directory })) {
  if (event.type === "permission.asked") { /* handle */ }
}

// Permission Reply
await client.permission.reply({
  path: { sessionID, requestID },
  body: { reply: "once" | "always" | "reject" }
});
```
*Source: Context7 /kilo-org/kilocode*

### server.json Schema
```json
{
  "port": 4097,
  "password": "a1b2c3d4e5f6...",
  "version": "7.4.11",
  "pid": 12345
}
```
*Source: GitHub catgirl3d/kilocode-legacy-p/docs/file-locations.md*

### SSE Event Shape (permission.asked)
```typescript
{
  id: string,
  type: "permission.asked" | "permission.v2.asked",
  properties: {
    id: string,          // requestID for reply
    sessionID: string,   // Originating session
    permission: string,  // Tool: "bash", "edit"
    patterns: string[],  // File patterns
    metadata: object,    // May contain { command, args }
    always: string[]     // Existing allow patterns
  }
}
```
*Source: research_01_approval_interception.md lines 59-67*

### VS Code APIs Used
| API | Purpose |
|-----|---------|
| `vscode.SecretStorage` | Store bot token and HMAC secret (OS keyring integration) |
| `vscode.FileSystemWatcher` | Watch `~/.config/kilo/server.json` for changes |
| `vscode.EventEmitter` | Emit normalized permission events to subscribers |
| `vscode.ExtensionContext.globalState` | Persist pending approvals across reloads |
| `vscode.workspace.getConfiguration()` | Read extension settings (polling interval, expiry) |
| `vscode.StatusBarItem` | Show connection status indicator |

*Source: VS Code SecretStorage documentation (TylerLeonhardt comments, GitHub microsoft/vscode#213903)*

## 6. Open Technical Questions for Planner

| Q# | Question | Priority |
|----|----------|----------|
| Q1 | How does Agent Manager map worktrees to separate opencode ports? Must we create N SSE connections or use single global? | HIGH |
| Q2 | Does SDK version 7.4.11 need to match opencode backend exactly, or is `/api/event` backward compatible? | HIGH |
| Q3 | What is exact `metadata` structure for bash commands? Is `metadata.command` and `metadata.args` always populated? | HIGH |
| Q4 | Can multiple SDK clients reply to same permission? Does backend accept first-wins or reject duplicates? | MEDIUM |
| Q5 | What happens to `server.json` when user has multiple VS Code windows with different projects open? | MEDIUM |
| Q6 | Should ConfigManager handle the fallback to process scanning (`ps aux | grep "kilo serve --port"`) if server.json missing? | MEDIUM |
| Q7 | Where is `sessions.db` located for SQLite fallback on port discovery? Does it contain active session info? | LOW |

---
*Sources: research_01_approval_interception.md, research_02_remote_delivery_security.md, validation_priority.md, Context7 /kilo-org/kilocode*