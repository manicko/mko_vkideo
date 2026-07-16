---
name: 05-integrations
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 05 Audit — External Integrations

## Purpose

This phase audits how the system talks to the **outside world**: browsers, external
services/APIs, subprocesses (ffmpeg, yt-dlp, etc.), credential providers, and any
third-party SDKs or libraries used for I/O. The goal is to find correctness,
reliability, and security defects in the *boundary* between application logic and
external dependencies.

This file is written as a **reusable handbook** for the integration phase of any audit.
It deliberately avoids naming specific files, function names, or paths — instead it
describes *what to discover and verify*. Apply it to whatever external integrations
the current system actually has.

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the integration architecture. For **each**
external dependency the system uses, answer the questions below. The set of
dependencies is system-specific (e.g. headless browser automation, network/captured
traffic, media transcoding binaries, credential stores, cloud/file APIs). Do not
assume a fixed list — enumerate what the code actually imports and calls.

1. **External Integration Discovery** — Enumerate every external system the
   application depends on. For each, identify: the library/SDK/binary used, the
   entry-point object or client that wraps it, and the lifecycle (who creates it,
   who owns it, who tears it down). Map the initialization flow from configuration
   or environment into the client.
2. **Authentication / Credential Discovery** — For each integration that requires
   auth (browser sessions, API keys, tokens, cookies, OAuth): trace how credentials
   are obtained, stored, refreshed, and injected into the client. Identify fallback
   paths when credentials are missing or invalid.
3. **Error Handling Discovery** — For each integration: what happens when the
   external system is unreachable? When credentials are rejected? When rate limits
   are hit? When the external process crashes or returns malformed output? Identify
   which errors are caught, which are retried, and which propagate.
4. **Config Injection Discovery** — Trace how configuration (endpoints, timeouts,
   credentials, feature flags, SSL settings) flows from the settings/config model
   into each integration client. Identify anywhere a hardcoded value or silent
   default bypasses configuration.
5. **Resource Lifecycle Discovery** — Identify every long-lived external resource
   (browser instances, network monitors, open subprocesses, file handles, sessions).
   Map where each is opened and where (and whether) it is always closed, including
   on error and on interruption.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the
commands provided in the project's commands file. Skip only if a step is impossible
— document why.**

### Step R1 — Import Verification

Import all integration modules and the application entry point. Verify no import
errors, no missing optional dependencies, and that integrations degrade or fail
clearly when an optional dependency is absent.

### Step R2 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R3 — Run Test Suite

Run the project's test suite, focusing on integration-related tests (and any tests
that mock external systems).

- Record pass/fail counts and failure output.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the integrations the system
> actually has. A dimension is omitted from the report if no problem is found in it.

### 1. External Client Initialization & Lifecycle

| Check | Description |
|-------|-------------|
| Client is created correctly | The external client is constructed with the correct endpoint, identity, and options from configuration — not hardcoded. |
| Lifecycle is managed | The client/resource is properly opened and closed (context manager, `try/finally`, or equivalent). It is not leaked across invocations. |
| Startup failure is handled | If the external system cannot be reached at startup, the failure is reported clearly and the app does not hang or crash with an opaque traceback. |
| teardown on every exit path | The resource is released on normal completion, on error, and on user interruption (e.g. Ctrl+C). |

**Evidence required:** Read the integration wrapper end-to-end. Trace creation →
use → teardown. Verify cleanup runs in all exit paths, including `KeyboardInterrupt`.

### 2. Authentication, Credentials & Secrets

| Check | Description |
|-------|-------------|
| No hardcoded credentials | API IDs, tokens, keys, session secrets, and identifiers come from configuration or a credential store, never from source literals. |
| Credentials not logged | Secrets are never passed to log/debug calls at any verbosity level. |
| Credentials are user-local / not committed | Session files, token caches, or cookie stores live in a user directory, never in the package directory or the source tree. |
| Auth supports all configured modes | If the system supports multiple auth strategies (e.g. none / browser / file), each path is actually implemented and exercised. |
| Re-auth / refresh is handled | When a credential expires or is rejected, the system refreshes or re-acquires rather than failing permanently without explanation. |

**Evidence required:** Search for any hardcoded secrets. Search for log calls near
credential-handling code. Trace each credential from its source to the client.

### 3. Error Handling & Retry Behavior

| Check | Description |
|-------|-------------|
| Rate-limit / backoff is handled | Transient "too busy" or rate-limit responses trigger a wait-and-retry with a sane duration (and optional jitter). |
| Other transient errors are retried | Recoverable errors (timeouts, network blips, temporary unavailability) use bounded retries with backoff. |
| Permanent errors are not retried forever | After max retries, the error is logged and the unit of work is skipped — not retried indefinitely. |
| External process failures are captured | When shelling out to a binary (ffmpeg, yt-dlp, etc.), non-zero exit codes and stderr are captured and surfaced, not silently ignored. |
| Malformed external output is handled | If the external system returns unexpected/empty/corrupt data, the system degrades gracefully instead of crashing mid-pipeline. |

**Evidence required:** Read the integration's call sites and error wrappers. Verify
retry bounds, backoff, and that external subprocess failures are detected.

### 4. Config-to-Integration Flow

| Check | Description |
|-------|-------------|
| Every config field reaches the integration | Each setting the integration needs (endpoint, timeout, SSL flag, credential path, feature toggle) is actually passed through to the client. |
| No config fields are ignored | Every field in the relevant config section is consumed by the corresponding integration. |
| No hardcoded fallbacks | The integration does not silently fall back to a hardcoded value when configuration is missing. |
| No global config singleton bypass | Integrations receive configuration via constructor/parameter, not by reaching into a global settings object in a way that hides data flow. |

**Evidence required:** Trace each config field from the settings model → constructor
→ client call. Verify no field is silently ignored or overridden.

### 5. Cross-Integration Coupling

| Check | Description |
|-------|-------------|
| Integrations are isolated | A failure in one external system does not cascade to unrelated parts of the pipeline. |
| Shared state is explicit | Where multiple integrations share state (e.g. a captured network stream consumed by an extractor), the handoff is explicit and documented, not implicit global state. |
| Concurrency is safe | If multiple integrations (or multiple concurrent units of work) share a client/browser/session, access is synchronized; there is no race on a shared external resource. |

**Evidence required:** Identify the seams between integrations. Verify the data
handoff and any shared resource is thread/async safe.

---

## Report Output

Write findings to: `/.ai/audit/05-integrations/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `INT-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, test failures, code analysis showing the bug, or captured external failures.
  2. **Not just:** "violates invariant X" — show the exact integration code that violates it and the exact consequence (leaked resource, silent credential in logs, permanent hang, uncaught subprocess error).
