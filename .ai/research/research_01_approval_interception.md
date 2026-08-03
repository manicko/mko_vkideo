# Research: Kilo Code 7.4.11 Execution Approval Interception

## Key Facts

### 1. Extension Identity and Activation
- **Extension ID**: `kilocode.kilo-code` (source: package.json line 2-11)
- **Activation events**: `onStartupFinished` and `onUri` (launched immediately on VS Code startup)
- **Architecture**: The extension spawns an embedded `opencode` CLI backend that communicates via HTTP + SSE

### 2. Permission Approval Implementation (HIGH CONFIDENCE)

**SSE Event Flow:**
- CLI backend emits `permission.asked` events via Server-Sent Events stream
- Events are received by `SdkSSEAdapter` (in `packages/kilo-vscode/src/services/cli-backend/sdk-sse-adapter.ts`)
- `KiloConnectionService.onEvent()` broadcasts to all registered listeners (line 60-66 in connection-service.ts)
- `KiloProvider` receives events and forwards to webview as `permissionRequest` message via `postMessage()`

**Permission Response Mechanism:**
- Webview sends `permissionResponse` message with `{ permissionId, sessionID, response: "once" | "always" | "reject" }`
- `KiloProvider.handlePermissionResponse()` calls `client.permission.reply({ requestID, directory, reply })`
- SDK endpoint: `POST /permission/{requestID}/reply` (source: sdk.gen.ts)

### 3. Public Extension API Availability

**CRITICAL FINDING**: Kilo Code VS Code extension does NOT export a public API.
- `activate()` function in `packages/kilo-vscode/src/extension.ts` returns nothing (implicit `undefined`)
- No `API` class export like Roo Code/Cline had. Each codebase variant differs.
- The legacy `src/exports/api.ts` and `src/extension/api.ts` files exist in some forks but are NOT used in the modern `packages/kilo-vscode` architecture
- The legacy `return new API(...)` pattern exists in the old `src/extension.ts` but the modern VS Code package (`packages/kilo-vscode/src/extension.ts`) returns nothing

**Verification**: Search for `vscode.extensions.getExtension("kilocode.kilo-code").exports` - no documented or implemented API surface.

### 4. Event Subscription Without Source Modification (VIABLE)

**YES - via KiloConnectionService `onEvent()` method:**
```typescript
// Companion extension can access via:
const kiloExtension = vscode.extensions.getExtension("kilocode.kilo-code")
// But no exports available - must use alternative
```

**WORKING APPROACH - Direct SDK Integration:**
The CLI backend exposes a local HTTP server on `http://127.0.0.1:{port}`. A companion extension can:

1. **Spawn and connect to the same backend** using `createKiloClient()` from `@kilocode/sdk/v2/client`
2. **Subscribe to SSE events** via `client.global.event()` AsyncGenerator
3. **Intercept `permission.asked` events** before KiloProvider processes them
4. **Call `client.permission.reply()`** to approve/reject - this works because the backend tracks permissions by requestID globally

**Source evidence**:
- `KiloConnectionService` demonstrates this pattern (connection-service.ts lines 121-123)
- `registerToggleAutoApprove()` successfully uses `connectionService.onEvent()` for runtime permission handling (toggle-auto-approve.ts)
- The SDK `Permission.reply()` endpoint works with requestID + directory

### 5. Required Information Flow for Remote Approval

**Permission data available in `permission.asked` SSE event:**
```typescript
type PermissionRequest = {
  id: string           // Unique request identifier
  sessionID: string    // Session that requested permission  
  permission: string   // Tool name (e.g., "bash", "edit")
  patterns: string[]   // File patterns for the request
  metadata: object     // Contains command/args in some cases
  always: string[]     // Existing "always allow" patterns
  tool?: { messageID, callID }
}
```

### 6. Delivering Approval Decisions Back

**Viable mechanisms:**
1. **SDK direct call**: `client.permission.reply({ requestID, directory, reply })` - highest reliability
2. **VS Code commands**: If Kilo exposed commands like `kilo-code.permission.approve` - NOT currently available
3. **IPC/WebSocket**: Could be added but requires extension modification
4. **Keyboard automation**: Not reliable for programmatic responses

## Recommended Interception Approach

### Approach A: Companion Extension with SDK (Recommended)

1. **Connection**: Companion extension uses `@kilocode/sdk/v2` to connect to the same backend server
2. **Event monitoring**: Subscribe to `client.global.event()` or direct HTTP endpoint
3. **Permission detection**: Filter SSE events for `type === "permission.asked"`
4. **Notification**: Send permission details to mobile (Telegram) via HTTP webhook
5. **Remote response**: Mobile reply triggers companion extension to call `client.permission.reply()`

**Prerequisites:**
- Companion extension needs to discover the backend port (from `~/.config/kilo/server.json` or process inspection)
- The backend uses Basic Auth with password stored locally

### Approach B: File-based State Watching

1. Monitor `~/.config/kilo/kilo.jsonc` for `permission` settings changes
2. Watch for SQLite database changes in `~/.local/share/kilo/sessions.db`
3. **Limitation**: Only detects configuration changes, NOT real-time permission requests

### Approach C: Terminal/Process Monitoring

1. Use VS Code `vscode.window.onDidWriteTerminalData` or shell execution hooks
2. **Limitation**: Only detects executed commands, NOT permission approval prompts

## Rejected Approaches with Justification

| Approach | Rejection Reason |
|----------|-----------------|
| `vscode.extensions.getExtension("kilocode.kilo-code").exports` | No public API is exported; returns `undefined` |
| VS Code command interception (`kilo-code.permission.*`) | No such commands are registered; permission commands are webview-internal |
| Monkey-patching require cache | Requires modifying extension files; breaks on updates; security policy violations |
| Window/message hook injection | VS Code extensions run in isolated context; no DOM access to webview |
| Audio/output channel monitoring | Too unreliable; requires regex parsing of text output |
| Polling `permission.list()` only | High latency; misses timing; not real-time |

## Feasibility Assessment

### Non-intrusive interception: **VIABLE but requires SDK integration**

**Minimum viable mechanism:**
1. Companion extension bundles `@kilocode/sdk/v2/client`
2. Reads backend config from `~/.config/kilo/server.json` (port + password)
3. Creates independent `KiloClient` connection to `http://127.0.0.1:{port}`
4. Uses `client.global.event()` to subscribe to SSE events
5. Filters for `permission.asked` events and forwards to notification service
6. Implements HTTP endpoint/receiver for remote approval responses
7. Calls `client.permission.reply({ requestID, reply })` with Basic Auth authentication

**Risks:**
- Backend password stored in plaintext on disk (mitigatable via OS keychain)
- Multiple extensions connecting to same port may cause race conditions (untested)
- SDK version compatibility with bundled opencode backend
- Worktree sessions may use different port directories (requires tracking)
- No session-scoped event filtering by default - companion receives ALL events

## Key Source References

| Component | URL |
|-----------|-----|
| Extension entry point | https://github.com/Kilo-Org/kilocode/blob/cb0c58c0/packages/kilo-vscode/src/extension.ts |
| KiloConnectionService (SSE events) | https://github.com/Kilo-Org/kilocode/blob/cb0c58c0/packages/kilo-vscode/src/services/cli-backend/connection-service.ts |
| Permission handler | https://github.com/Kilo-Org/kilocode/blob/0f55066d/packages/kilo-vscode/src/kilo-provider/handlers/permission-handler.ts |
| SDK Permission API | https://github.com/Kilo-Org/kilocode/blob/c3d4309d/packages/sdk/js/src/v2/gen/sdk.gen.ts |
| SSE Event types | https://github.com/Kilo-Org/kilocode/blob/c3d4309d/packages/sdk/js/src/v2/gen/types.gen.ts |
| Toggle auto-approve example | https://github.com/Kilo-Org/kilocode/blob/0f55066d/packages/kilo-vscode/src/commands/toggle-auto-approve.ts |
| CLI permission events | https://github.com/Kilo-Org/kilocode/blob/be0ea199/packages/opencode/src/permission/index.ts |