# Verify a coding-agent handoff

ClaimTrail ties a configured check to the worktree content it observed. In a
trusted project, its Codex `Stop` hook runs when the agent attempts to finish a
turn. A fresh verified receipt is reused. Missing, stale or incompatible evidence
causes one run of the approved check. A failed, timed-out or invalid check leaves
the handoff held.

## Install for a local Codex project

Use Python 3.9+ on macOS or Linux. The handoff CLI has no Python dependencies.
Download `claimtrail-handoff.pyz` and its checksum from the [v0.1 release](https://github.com/divyanshAgarwal123/claimtrail-standalone/releases/tag/v0.1). You can also build it from this checkout:

```bash
python3 -B scripts/build_handoff.py
```

Keep `dist/claimtrail-handoff.pyz` at a stable location. In the project you want
to check, create a policy file based on
[the pytest example](../examples/policies/pytest.json). Set its
`command` to the real check and choose the inputs the check depends on, including
source, tests, configuration and lockfiles when applicable. The command is an
argv array. The person installing the hook approves the command and worktree
that it will execute against. Include `.claimtrail` in `exclude` if the scope
includes the entire project.

In the project directory:

```bash
python3 /absolute/path/to/claimtrail-handoff.pyz install-codex --policy ./check-policy.json
```

This adds two handlers to the project's `.codex/hooks.json` and preserves other
handlers. Start Codex in the trusted project and review the two ClaimTrail
handlers in `/hooks` or the desktop app's hook review. Once trusted, subsequent
turns invoke the completion check automatically. Disable the two handlers in
Codex when you want to pause this workflow. Reinstall after moving the zipapp or
changing the approved policy. Install separately for a second Git worktree. Keep the generated `.codex/hooks.json` local because it contains absolute paths.

The install pins the policy and the checkout in the hook command. SessionStart
shows the agent the approved capture command. It can use that command for an
in-task full check and reuse the receipt at completion. Direct test commands
remain useful for targeted work. A direct pass does not create a receipt, so a
missing receipt can add a full check at the end of the turn.

## Read the handoff

`.claimtrail/handoff.json` records the latest completed gate invocation, its
decision, receipt hash, changed paths, timings and the Codex session and turn
IDs when present. Match the turn ID when reading it from another integration.
A missing or mismatched record leaves that turn unchecked. The most recent
receipt and explicit check record also live in `.claimtrail/`. Keep that
directory out of version control and the declared file scope.

The Stop hook uses one continuation at most to have Codex report a held
handoff. The hook may let the conversation finish with a held status. For an
actual job or CI gate, invoke the CLI directly and require exit zero.

## Use with another agent or runner

Use the same policy and checkout for both commands. Route the configured check
through `check` while the agent works, then call `handoff` from the runner after
the task:

```bash
python3 /absolute/path/to/claimtrail-handoff.pyz check --policy ./check-policy.json
python3 /absolute/path/to/claimtrail-handoff.pyz handoff --policy ./check-policy.json
```

The CLI emits JSON on stdout. Exit 0 means the handoff is verified, 1 means it
is held, and 2 means the invocation or policy was invalid. Use `check` to
capture a new result after investigating a held check. A workspace lock prevents
two supported ClaimTrail invocations from racing on a receipt.

## What can be reused

ClaimTrail verifies the configured command, declared file contents and a
runtime fingerprint. The runtime fingerprint covers OS and architecture, the
resolved executable's identity and timestamps, and selected environment
variables including `PATH`, `PYTHONPATH`, locale and `TZ`. It can conservatively
trigger a rerun when the agent's shell and the hook use different environments.
Specify the required toolchain and environment in the policy where practical.

Choose which inputs to declare and which checks suffice for your work. Runtime
permissions, services, installed packages and semantic test coverage are outside
the fingerprint. Local receipts are unsigned and require a trusted workspace.
For shared enforcement, keep the approved policy and the verifier under your
runner's control, isolate the execution environment and retain your normal CI
merge checks.

[Codex hook behavior and trust review](https://learn.chatgpt.com/docs/hooks)
