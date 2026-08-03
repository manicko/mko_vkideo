# Part 1: Backend Connector & Config/Port Discovery Risk Analysis

## 1. RISK REGISTER

| ID | Risk | Likelihood | Impact | Detection | Mitigation | Owner |
|----|------|------------|--------|-----------|------------|-------|
| R01 | SDK vs bundled opencode backend version mismatch | MEDIUM | HIGH - Runtime crashes, missing API | Compare SDK version against `~/.config/kilo/version` or server `/version` endpoint | Bundle SDK in extension, implement version handshake on connect, fail gracefully with clear error | KiloBackendConnector |
| R02 | Backend not running/activation timing race | HIGH | HIGH - Missed approvals, extension unusable | SSE connection timeout, HTTP 404/ECONNREFUSED | Poll config file every 500ms for port, exponential backoff reconnect, status bar indicator | KiloBackendConnector |
| R03 | Port changes/password rotation during runtime | LOW-MEDIUM | MEDIUM - Stale credentials rejected | 401 Unauthorized on SSE/auth attempts | Watch `server.json` file via VS Code FileSystemWatcher, re-establish connection on change | ConfigManager |
| R04 | Multiple Kilo instances using different ports | MEDIUM | MEDIUM - Wrong session targeted | Parse worktree configurations, map sessionID to port | Track per-session configs under `~/.config/kilo/worktrees/`, route replies to correct port | ConfigManager/KiloBackendConnector |
| R05 | Race conditions: two SDK clients replying to same requestID | LOW | HIGH - Unpredictable approval state, potential security risk | Log duplicate requestID attempts, monitor SDK behavior | Use `callback_query_id` dedupe in ApprovalStateManager, only first reply succeeds | ApprovalStateManager |
| R06 | Missed `permission.asked` events during SSE reconnect | HIGH | HIGH - Silent approval loss | Event stream gap detection, heartbeat monitoring | Implement SSE reconnect with `Last-Event-ID`, buffer missed events in backend if available | KiloBackendConnector |
| R07 | Malformed/evil server.json (path traversal, invalid port) | LOW | HIGH - Security breach or crash | JSON parse errors, port validation (1-65535), path sanitization | Schema validate with Zod/Pydantic, sanitize paths, fail closed | ConfigManager |
| R08 | Cross-platform path differences | HIGH | MEDIUM - Config not found on some platforms | Test on Windows/macOS/Linux, log file resolution errors | Use `os.platform()` to map paths: Win=`%APPDATA%\kilo`, Mac/Linux=`~/.config/kilo` | ConfigManager |
| R09 | High CPU/memory from SSE + Telegram polling | LOW | MEDIUM - Extension host sluggish | Process Explorer, activity monitor, memory leaks overtime | Cap SSE reconnect delay (max 30s), debounce polling (min 1s), dispose on deactivate | KiloBackendConnector |

## 2. NON-FUNCTIONAL REQUIREMENTS & SLOs

| Category | Requirement | Target SLO |
|----------|-------------|------------|
| Detection Latency | SSE event to notification dispatch | ≤ 500ms median, ≤ 2s p95 |
| Reconnection Time | SSE disconnect to reconnection | ≤ 3s on first retry, ≤ 30s max backoff |
| CPU Usage | Persistent SSE connection | ≤ 1% CPU idle, ≤ 5% during active event stream |
| Memory Cap | Total extension memory footprint | ≤ 100MB, no growth after warm-up |
| Config Validation | JSON schema compliance | Reject malformed within 100ms of read |
| Cross-Platform | Windows 10/11, macOS 12+, Ubuntu 20.04+ | All paths resolve correctly, unit tests on each |
| Secret Storage | Bot token in VS Code SecretStorage or OS keyring | Never logged, never persisted in plaintext |
| File Watch | Config change detection lag | ≤ 1s after external modification |

## 3. EDGE CASES

1. **Restart recovery**: Extension host reload clears in-memory state; pending approvals in `server.json` may still exist. Recover state from backend on reconnect or mark as orphaned.

2. **Offline desktop**: No network connectivity blocks Telegram API polling. Queue approvals in memory with TTL (default 30 min), show VS Code status indicator.

3. **Concurrent approvals**: Multiple permission requests in flight simultaneously. Each gets unique requestID; track in map, handle responses by ID.

4. **Extension host reload mid-approval**: VS Code reloads while user deliberates. Telegram callback arrives after reload; extension must re-read `server.json` and re-establish SSE.

5. **User closes VS Code mid-approval**: No way to deliver response to backend. Approval times out in backend (default 30 min), notify user via Telegram.

6. **Worktree deletion during session**: `server.json` may reference deleted worktree. Validate worktree path exists before routing.

7. **Port conflict: new Kilo spawns secondary server**: `server.json` overwritten; companion loses connection to original session's approvals.

8. **Telegram callback with stale/expired HMAC**: Malicious replay or user delayed reply. Reject via expiry timestamp (max 1 hour).

## 4. TESTABILITY NOTES

| Component | Hard to Test | Test Strategy |
|-----------|--------------|---------------|
| Live Kilo backend connection | Cannot mock real SSE stream | Inject mock SSE client via constructor, test with `nock` HTTP mocking for `/permission/reply` |
| Port discovery logic | File I/O and process inspection | Provide `ConfigProvider` interface, inject fake config in tests |
| Event parsing | Real events have specific shape | Use fixture files from actual Kilo backend SSE output, property-based testing for payload variations |
| Reconnection behavior | Real timing delays, flaky in CI | Use fake timers (Jest `jest.useFakeTimers()`) for reconnect delays, simulate disconnect via mock server |
| Race condition detection | Hard to reproduce timing | Unit test dedupe logic with concurrent mock replies, track `processedCallbackIds` state |
| Cross-platform paths | Need all OS variants | Test on all supported platforms, mock `os.platform()` and `process.env` in unit tests |

**Recommended test doubles**: `MockSSEClient`, `FakeConfigReader`, `InMemoryApprovalStore`.