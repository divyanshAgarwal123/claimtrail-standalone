# ClaimTrail

Verify that a passing check still applies to the files an AI coding agent is
handing back. ClaimTrail captures the command, result, and fingerprints of the
inputs you declare. At handoff, it reuses a fresh pass or reruns the approved check
once when evidence is missing or stale.

[Download v0.1](https://github.com/divyanshAgarwal123/claimtrail-standalone/releases/tag/v0.1) ·
[Codex setup](docs/CODEX_HANDOFF.md) · [Benchmarks](benchmarks/README.md) ·
[Roadmap](docs/ROADMAP.md)

## Try it with Codex

1. Download `claimtrail-handoff.pyz` from the release and put it at a stable path.
   The CLI needs Python 3.9+ and works with local Codex on macOS or Linux.
2. In your project, save a policy such as [the pytest example](examples/policies/pytest.json)
   as `check-policy.json`. Update its command and file scope for your repository.
3. From that project, install the hooks and review them in Codex with `/hooks`.

```bash
python3 /path/to/claimtrail-handoff.pyz install-codex --policy ./check-policy.json
```

When the agent wants to run the full check, it can use the capture command shown
at session start. Codex invokes the verifier automatically at the end of the
turn. The result goes to `.claimtrail/handoff.json`. For a CI job or another
agent, use the same CLI's `check` and `handoff` commands directly.

## See the evidence

Two local Codex tasks on pinned pytest and Django revisions reused successful
checks. Fresh reruns took 52.78 seconds total. Receipt capture overhead and
verification took 2.89 seconds, for an estimated 49.89 seconds of duplicate
check time avoided in that comparison. [Recorded results and reproduction instructions](benchmarks/README.md)

For an offline walkthrough using 30 controlled cases:

```bash
python3 -B src/review_app.py --verification-report examples/verification/recorded/report.json --port 8768
```

Open [the local viewer](http://127.0.0.1:8768/) and choose **source changed**
to see how an edit invalidates an earlier pass. A separate [synthetic claim
review demo](docs/SYNTHETIC_DEMO.md) shows how to inspect recorded events.

## Develop and verify

```bash
python3 -B -m unittest discover -s tests -v
python3 -B src/verification_report.py examples/verification/recorded/report.json
python3 -B scripts/build_handoff.py
python3 dist/claimtrail-handoff.pyz --version
```

The configured command and declared inputs define the result. The [scope
verification guide](docs/SCOPE_VERIFICATION.md) explains the boundary, including
runtime checks and local receipt trust. ClaimTrail is [MIT licensed](LICENSE).
See [third-party notices](THIRD_PARTY_NOTICES.md) for upstream materials.
