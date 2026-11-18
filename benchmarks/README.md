# ClaimTrail handoff benchmark

On November 18, 2026, two local Codex tasks on macOS arm64 produced patches and
ran their configured checks. The native Stop hook reused a fresh receipt in
each final worktree.

| Task | Selected native result | Fresh rerun, median of two | ClaimTrail cost | Estimated saving |
| --- | --- | ---: | ---: | ---: |
| pytest regex mismatch diagnostics | 1,370 passed, 44 skipped, 1 deselected, 2 xfailed | 28.168 s | 0.117 s | 28.051 s |
| Django admin button types | 5,177 ran, 116 skipped, 2 expected failures | 24.612 s | 2.771 s | 21.841 s |
| **Total** | | **52.780 s** | **2.889 s** | **49.892 s** |

The original costs include in-process capture overhead plus Stop verification.
They exclude setup, interpreter startup, and agent time. This two-task result
applies to checks the agent already ran. Missing and stale receipts incur the
underlying check time. The comparison does not establish adoption, independent
replication, or savings across other workloads.

The tasks came from [pytest PR #13859](https://github.com/pytest-dev/pytest/pull/13859)
and [Django ticket #36423](https://code.djangoproject.com/ticket/36423).
The first Django attempt exposed a ClaimTrail receipt-validation bug with
square brackets in an observed filename. After the fix, I reran the task on a
fresh checkout with the same upstream revision. Django's timed selection
used SQLite and covered admin, forms, templates and related database modules.
The new browser regression test passed syntax validation. It was outside the
timed suite and was not run in QUnit. The pytest selection excludes one
terminal header test that failed in preflight with the installed Hypothesis
plugin. The exclusion applies to both comparison arms.

## Reproduce the check comparison

From the v0.1 source checkout on macOS arm64, with Git, Python 3.9+ and
[uv](https://docs.astral.sh/uv/) available:

```bash
python3 -B benchmarks/run.py --output ./data/benchmark-v01
```

The output directory must be new. The script clones the tagged revisions
listed in [cases.json](cases.json), verifies their commit hashes, applies the
[frozen patches](patches), and uses Python 3.13.17 and the
[pinned test dependencies](requirements). It runs the approved check once to
capture a receipt, verifies it through the portable CLI, and times two fresh
native reruns on the final files. Use `--case pytest` or `--case django` for
one task. Logs and measurements are written under the output path.

This replay needs network access for upstream source and dependencies. It
compares the same final patches without an LLM or a Codex account, using
external process timings that include CLI startup. [observed.json](observed.json)
contains the original local Codex measurements with session identifiers and
machine paths removed. Timings can vary across machines.

The release preparation rerun completed both cases from fresh checkouts at the
expected package versions. Its estimated reuse savings were 27.81 seconds for
pytest and 22.44 seconds for Django. [Reproduction output](reproduced.json)
