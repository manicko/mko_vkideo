# Part 4 Requirements - Cross-Cutting Concerns (Extension Lifecycle, Global Config, Observability)

## 1. Functional Requirements (FR)

| ID | Requirement |
|----|-------------|
| FR-1 | extension.ts activates via onStartupFinished + * for workspace commands; orchestrates 5 modules without modifying Kilo. |
| FR-2 | Status-bar item displays connection state (connected, reconnecting, error) + pending approval count (max 99). |
| FR-3 | Extension settings schema: pollingIntervalMs (1000-5000), approvalTtlMs (default 30 min), allowedTelegramUserIds (array), backendDiscovery enum, connectionTimeoutMs, dedupeWindowMs. |
| FR-4 | Structured logging via OutputChannel + EventEmitter; no secrets in logs; correlation via requestId/eventId. |
| FR-5 | Unified error taxonomy: ConfigNotFoundError, BackendUnreachableError, ProviderError, SecurityError, ReplyTransportError. |
| FR-6 | Retry policy: exponential backoff (1s-30s) + jitter for SSE/backend; Telegram 429 backoff respecting retry_after. |
| FR-7 | Internal API contract document defines PendingApproval -> OutboundApproval -> InboundDecision -> ResolvedDecision flow. |
| FR-8 | Testing strategy: unit (Vitest) for all modules, integration smoke (nock), fake timers for backoff, contract tests for providers. |

## 2. Non-Functional Requirements

| ID | Requirement |
|-----|-------------|
| NFR-1 | Security: All secrets in VS Code SecretStorage only; HMAC truncated to 16 bytes (NIST SP 800-107); tokens <=64 bytes UTF-8. |
| NFR-2 | Reliability: SSE connection with 30s timeout; Last-Event-ID recovery; no unhandled promise rejections. |
| NFR-3 | Observability: Debug-level logs off by default; INFO for state changes; WARN for recoverable errors; ERROR for schema failures. |
| NFR-4 | Performance: ApprovalStore bounded; polling interval >=1s to respect Telegram rate limits. |
| NFR-5 | Maintainability: Small files (<100 lines), strict TypeScript, dependency injection for all I/O. |

## 3. Goals and Success Criteria

| Goal | Success Criterion |
|------|-------------------|
| G1 - Seamless Kilo integration | No activate() exports; companion pattern proven via KiloBackendConnector SSE subscription. |
| G2 - Mobile approval workflow | Approval request -> Telegram notification -> callback -> backend reply in <3s median. |
| G3 - Multi-provider ready | NotificationProvider interface; stubs compile; factory pattern for provider selection. |
| G4 - Production observability | All error paths logged; status bar reflects actual connection state; no token leaks. |
| G5 - Resilient operation | Reconnect within 60s of backend restart; missed events recovered; expired approvals auto-rejected. |

## 4. Responsibility Zones

| Component | Responsibilities |
|-----------|------------------|
| Orchestrator (extension.ts) | Wire modules together; hold NotificationProvider instance; route PendingApproval -> provider; handle InboundDecision -> ResolvedDecision -> replyToPermission. |
| KiloBackendConnector (Part 1) | SSE lifecycle only; emit normalized events; accept replies. |
| ConfigManager (Part 1) | Discover server.json; read extension settings; ConfigProvider interface. |
| SecurityModule (Part 3) | HMAC signing/verification; SecretStorage; handle->requestId mapping. |
| ApprovalStateManager (Part 3) | TTL tracking; dedupe; authorization check; ResolvedDecision production. |
| TelegramProvider (Part 2) | Send notifications; poll callbacks; editMessage feedback. |
| ConfigManager Part1 vs Global Settings | Part 1 owns server.json discovery + ConfigProvider interface. Global settings (contributes.configuration) feed into ExtensionSettings consumed by all layers. |

## 5. Key Integrations and VS Code Contribution Points

| Manifest Section | Configuration |
|------------------|---------------|
| contributes.configuration | Settings schema: mkoAInotify namespace with pollingIntervalMs, approvalTtlMs, allowedTelegramUserIds, backendDiscovery, connectionTimeoutMs, dedupeWindowMs. |
| activationEvents | [*] for workspace scope, onStartupFinished to avoid slowing VS Code startup. |
| contributes.commands | mkoAInotify.setBotToken, mkoAInotify.rotateSecret, mkoAInotify.showAuditLog. |
| API Usage | window.createStatusBarItem(), window.createOutputChannel(Mko-AINotify), EventEmitter<T>, context.secrets (SecretStorage), context.globalState (Memento), workspace.getConfiguration(). |
| Activation Timing | onStartupFinished fires after all * extensions activated; orchestrator must initialize before first permission.asked event. |

Source: VS Code Extension API docs (Context7: /websites/code_visualstudio_api)

## 6. Open Questions

| Question | Status |
|----------|--------|
| Q1 - Single vs Multi-Instance | Can telegram callback route to correct worktree session? Handles must encode sessionId or orchestrator must track active worktree. |
| Q2 - Status Bar UX | Should count show total pending or pending requiring attention? Should color change on pending > 0? |
| Q3 - Telemetry Opt-In | No telemetry planned; only structured logs to OutputChannel. Future: optional crash/error reporting. |
| Q4 - Extension Versioning | SDK version must match opencode backend; require version check on startup; warn but allow graceful degradation. |
| Q5 - Cross-Instance Secret Rotation | When secrets rotate, does Kilo reconnect with new password? Must watch server.json for changes. |

---

Part 4 validated against: VS Code Extension API v1.89+ (StatusBarItem, OutputChannel, EventEmitter, SecretStorage, activationEvents), Telegram Bot API v10.2, NIST SP 800-107 (truncated HMAC).
