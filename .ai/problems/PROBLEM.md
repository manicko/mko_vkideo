## Problem Statement

I use Kilo Code 7.4.11 as a VS Code extension for autonomous software development. The agent can work independently for long periods, but it frequently pauses execution whenever it requires approval to run certain commands (typically terminal commands that may modify the project or system).

This approval mechanism is important because I want to retain control over potentially sensitive or destructive operations. I do not want to disable execution approvals globally.

The problem is that when I am away from my computer, I receive no notifications that the agent is waiting for my approval. As a result:

- the agent becomes blocked indefinitely;
- development progress stops until I return to my computer;
- long-running autonomous sessions lose much of their value because they cannot continue without manual intervention.

## Desired Workflow

I want to continue using execution approvals, but receive approval requests on my mobile phone in real time.

The ideal workflow is:

1. Kilo Code requests permission to execute a command.
2. A notification is immediately sent to my phone.
3. The notification includes:
   - the command,
   - working directory,
   - project name,
   - reason (if available),
   - timestamp.
4. I can remotely choose:
   - Approve
   - Reject
   - Optionally "Approve Once" or "Always Allow Similar Commands".
5. My decision is securely delivered back to the local VS Code instance.
6. Kilo Code immediately continues execution without requiring me to remotely access my desktop.

## Constraints

- Kilo Code source code should remain unmodified if possible.
- The solution should integrate through official APIs, extension mechanisms, hooks, or external services whenever possible.
- Security is critical:
  - only authenticated approvals,
  - encrypted communication where applicable,
  - replay protection,
  - no public exposure of the local machine.
- The solution should be modular so Telegram can later be replaced by another notification provider (Slack, Discord, ntfy, Pushover, etc.).
- Cross-platform support is preferred (Windows, macOS, Linux).

## Research Goals

Investigate whether such a solution can be implemented using:

- Kilo Code APIs
- VS Code Extension API
- Kilo Gateway / Control UI
- MCP
- Extension events
- Command interception
- WebSocket communication
- Local helper services
- Telegram Bot API
- Other notification mechanisms

Determine the cleanest architecture with the least intrusion into Kilo Code itself.

The final outcome should be a production-ready architecture and implementation plan for enabling mobile approval of Kilo Code execution requests.