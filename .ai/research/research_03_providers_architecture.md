# Remote Approval System: Provider Comparison & Architecture Alternatives

## 1. Notification Provider Comparison

| Provider | Two-Way Interaction | Setup Friction | Self-Host | Reliability | Latency | Cost | Mobile Support | Modularity |
|----------|---------------------|----------------|-----------|-------------|---------|------|----------------|------------|
| **Telegram Bot API** | ✅ Inline keyboards + callback queries. User taps button, bot receives callback immediately. Works on both iOS/Android. | Low - Create bot via @BotFather, get token | ✅ Possible (tdlib, telegram-server) | High - Telegram infrastructure is robust | Low - Global CDN, typically <1s delivery | Free | Excellent - Official apps on all platforms, no account required for bot users | Good - Standard Bot API, multiple SDKs |
| **ntfy.sh** | ✅ Action buttons support (Android/iOS apps). User taps button, HTTP POST/callback to configured endpoint. | Minimal - Install app, choose topic name | ✅ Full self-host (Go binary, Docker) | Depends - Public server is stable, self-hosted can be made HA | Low - WebSocket/HTTP, typically <1s | Free (Pro ~$5/mo for reserved topics) | Good - Android, iOS, web, desktop apps | Good - Simple HTTP API, topic-based pub-sub |
| **Pushover** | ❌ Limited - No native button callbacks. Can include URL for action, but requires user to tap link and open app. | Medium - Register app, get user key + API token | ❌ No (managed service) | High - Established service, good uptime | Low - Fast delivery | Paid (one-time $5/device + optional Teams) | Good - Android, iOS apps | Good - REST API |
| **Discord** | ✅ Button components with interaction handlers. User taps, bot receives interaction event. Mobile works via Discord app. | Medium - Create application, configure bot, invite to server | ❌ No (managed) | High - Discord infrastructure | Low - Typically <1s | Free (Nitro optional) | Good - Official mobile apps | Good - Rich API, many SDKs |
| **Slack** | ✅ Block Kit buttons - interactive components with callback URLs. Mobile works via Slack app. | High - Create app, configure interactivity, ngrok for dev webhook | ❌ No (managed) | High - Enterprise-grade | Low - Fast | Paid (free tier limited) | Good - Mobile apps | Good - Webhook-based |
| **FCM** | ✅ Action buttons in notifications (Android) / Interactive notifications (iOS). Requires dedicated mobile app. | High - Firebase project, APNs cert, mobile app dev | ✅ Self-host not applicable (infrastructure is Google) | High - Google infrastructure | Low - Fast | Free (within limits) | Platform-native | Poor - Tied to Firebase/mobile app ecosystem |

## 2. Architecture Alternatives

### Alt A: Companion VS Code Extension + Local Relay + Telegram Bot (Recommended)

**Description:** A separate VS Code extension watches for Kilo Code approval events via VS Code events/API, communicates with a lightweight local relay service (Node.js/Python) that manages Telegram bot communication.

**Tradeoffs:**

| Factor | Assessment |
|--------|-------------|
| Complexity | Medium - Extension + relay + bot = 3 components |
| Maintainability | Good - Clear separation, each component has single responsibility |
| Required Permissions | VS Code API access, local network access, Telegram bot token storage |
| Reliability | Good - Bot handles offline, local relay can buffer |
| Latency | Low - Local relay adds minimal overhead |
| Portability | Excellent - Works on Win/Mac/Linux |
| Implementation Effort | Medium (2-3 days for MVP) |
| Risks | Security: Bot token exposure; Complexity: Multiple moving parts |
| Kilo Intrusion | None - Observes VS Code events externally |

### Alt B: External Standalone Helper Service (Node/Python)

**Description:** A standalone service runs on the developer's machine, monitoring Kilo state via log files or process inspection. When an approval is detected, it sends Telegram notification and waits for response.

**Tradeoffs:**

| Factor | Assessment |
|--------|-------------|
| Complexity | Low - Single service + Telegram bot |
| Maintainability | Good - One codebase to maintain |
| Required Permissions | File system access, process monitoring |
| Reliability | Fair - Depends on log format stability |
| Latency | Medium - Polling or filesystem event delays possible |
| Portability | Excellent - Python/Node scripts cross-platform |
| Implementation Effort | Low-Medium (1-2 days) |
| Risks | Log format changes break detection; Process monitoring may miss events |
| Kilo Intrusion | None - External monitoring |

### Alt C: MCP-Server-Based Approach

**Description:** Kilo talks to an MCP server that wraps Telegram capabilities. The MCP server handles notifications and approval waiting internally, using Telegram as transport. The agent explicitly calls the MCP tool for approvals.

**Tradeoffs:**

| Factor | Assessment |
|--------|-------------|
| Complexity | Medium - MCP server + Telegram bot logic |
| Maintainability | Good - Modular server design |
| Required Permissions | MCP server registration, Telegram bot token |
| Reliability | Good - MCP handles reconnections |
| Latency | Low - Direct communication |
| Portability | Excellent - MCP is platform-agnostic |
| Implementation Effort | Medium (2 days) |
| Risks | MCP protocol still evolving; Requires agent to explicitly use tool |
| Kilo Intrusion | Minimal - Uses standard MCP mechanism |

## 3. Recommended Approach: Alt A (Companion Extension + Local Relay + Telegram)

**Justification:**

1. **Least Intrusive:** No modifications to Kilo Code source. The companion extension observes VS Code's extension host events.

2. **Production Quality:** Telegram's infrastructure is proven at scale with excellent uptime and global delivery.

3. **Modular Replaceability:** The relay service abstracts the notification provider. Switching to Discord, ntfy, or Pushover requires only replacing the relay's notification adapter.

4. **Security Model:** Local relay keeps bot token off the internet (uses outbound connections only). Approval responses come back through Telegram's authenticated bot API.

5. **Two-Way UX:** Inline keyboard buttons in Telegram provide instant one-tap approval/rejection. No typing or UUID copying required.

6. **Cross-Platform:** Works identically on Windows, macOS, and Linux since it's just a VS Code extension + local service.

7. **Offline Handling:** Telegram bots can queue messages; if the phone is offline, approvals are delivered when online. The local relay can timeout and reject if no response within threshold.

**Implementation Sketch:**
- VS Code extension listens to `onDidExecuteTask` or terminal events
- Local Node.js relay runs on localhost:PORT with simple HTTP API
- Relay maintains Telegram bot long-polling connection
- Approval requests trigger `sendMessage` with inline keyboard
- `answerCallbackQuery` + message edit provides user feedback
- Approval decision writes to local state file that extension polls

## 4. Rejected Approaches

### Pushover (Rejected)
- No native button callbacks. User must open the app and manually tap, or rely on notification URLs that open a browser.
- Poor two-way interaction UX compared to Telegram/Discord button systems.

### FCM (Rejected)
- Requires building and maintaining a mobile application.
- Complex setup: Firebase project, APNs certificates, separate Android/iOS code.
- Not modular - tightly coupled to Firebase ecosystem.

### Pure ntfy (Rejected for Primary)
- While ntfy supports action buttons, the ecosystem is smaller than Telegram.
- Telegram has more reliable delivery and better mobile experience.
- ntfy is recommended as a fallback for self-hosted scenarios.

### Log-Watching Only (Rejected)
- Brittle - depends on log format stability.
- May miss events or detect false positives.
- No direct integration with VS Code's approval flow.

### MCP-Only (Deferred)
- Requires explicit agent tool calls rather than intercepting existing approvals.
- Better as a future enhancement for explicit approval workflows, not retrofitting existing Kilo approval system.