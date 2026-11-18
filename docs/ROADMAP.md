# Where ClaimTrail can help

The clearest fit is a team that uses coding agents on worktrees and already
runs a slow test suite, build, or integration check before review. ClaimTrail
can show whether a local pass still applies to the final files and tell the
reviewer when a fresh check is required.

## Priorities after v0.1

1. **Make setup and failures easier to diagnose.** Preview what the policy will
   track, check whether the configured executable and hook are available, and
   distinguish infrastructure errors from test failures. The initial Django
   trial and the earlier loopback failure show why these details matter.
2. **Support several named checks per task.** Keep one receipt each for the
   suite, build, and other required checks. Rerun only the checks whose
   declared inputs or runtime changed. Start with explicit scope and
   dependency declarations.
3. **Attach evidence to the patch review.** Emit a compact Markdown or JSON
   summary with the command, result, changed paths, and the worktree or commit
   it covers. GitHub's checks are tied to commits. A local handoff can
   document edits before the code is committed, while repository CI remains
   the merge authority. [GitHub Checks](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks)
4. **Add one more agent adapter.** Reuse the CLI contract through a second
   agent's lifecycle hooks. Compare how often agents use the capture command
   and how much setup their developers need. [Claude Code hooks](https://code.claude.com/docs/en/hooks)

## Adjacent use cases

| Area | What a receipt could answer | What else it needs |
| --- | --- | --- |
| Slow integration suites or builds | Does the prior result cover the final inputs? | Explicit toolchain and dependency identity |
| Database migration review | Does the dry run cover this migration and schema snapshot? | A disposable database and a pinned schema or fixture |
| Data and ML pipelines | Do these validation results belong to this code, data version, and configuration? | Immutable data and artifact manifests |
| Release engineering | Which checks completed for this artifact? | Trusted runner evidence and signed provenance for cross-team verification |

Start with local test and build handoffs. Use independent developer trials to
measure setup time, stale receipts caught, duplicate runs avoided, and repeat
use before expanding to other domains. Local receipts are unsigned. Release
provenance belongs in the trusted build pipeline. [SLSA provenance](https://slsa.dev/spec/v1.2/provenance)
