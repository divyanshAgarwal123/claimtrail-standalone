# Scope and freshness results

The included report contains 15 controlled scenarios exercised on each of two
pinned repositories. All 30 cases replay to their expected contract outcomes.
These cases demonstrate how the verifier responds to deliberately constructed
inputs. Independent user benefit and typical agent failure rates remain unmeasured.

The public replay is a path-redacted copy of the controlled November 14, 2026
report. Policies, receipts and observations were resealed after substituting a
placeholder for local paths. Captured output digests refer to the original
streams. All 30 verdicts match the original expectations.
The public fixture SHA-256 is `a4d93198dd1cd058dcba02088d74db13da7f2d2a4285c57e061d61c1beba8a2d`.

## Repositories and environment

| Repository | Pinned revision | Captured unchanged full-suite outcome |
| --- | --- | --- |
| [More Itertools](https://github.com/more-itertools/more-itertools) | `ceafee8ce96f4bc1eb74c528bc247c91d648a0bb` | `unittest`: 936 tests, 5 skipped, exit 0 |
| [ItsDangerous](https://github.com/pallets/itsdangerous) | `672971d66a2ef9f85151e53283113f33d642dabd` | `pytest`: 297 passed, exit 0 |

Captured on macOS 27.2 / arm64 with Python 3.13.17.
The [test environment versions](../examples/verification/environment.txt) are
recorded. ClaimTrail and offline replay require only the Python standard library;
pytest/freezegun are dependencies of the upstream test runs.

## Controlled contract outcomes

Each row was exercised separately in each pinned repository. All source/test
mutations were introduced by the harness and restored. They are not upstream
bugs, contributor patches or examples of spontaneous agent behavior.

| Case per repository | Result |
| --- | --- |
| Unchanged passing full suite | Verified |
| Benign source, test or configuration edit after pass | Stale (three cases) |
| Untracked file added inside scope | Stale |
| Test file deleted after pass | Stale |
| Explicitly excluded bytecode cache changes | Verified for the declared scope |
| README changed outside the declared scope | Verified for the declared scope |
| Functional regression introduced after an old pass | Stale |
| Full suite run on the introduced regression | Failed |
| Passing unrelated/subset check offered for the full policy | Scope/policy mismatch |
| Restore upstream bytes and actually rerun | Verified |
| Command runs tests and then changes a scoped source file | Changed during check |
| No receipt | Missing |
| Passing rerun completed after the captured observation | Later; cannot verify earlier boundary |

Positive controls for excluded/outside paths demonstrate the policy boundary.
They do not establish whole-repository coverage. Even a harmless comment edit
invalidates the old content-bound receipt; that is conservative invalidation,
not evidence that the program is broken. Unit tests additionally exercise timeout,
cross-workspace reuse, malformed/altered records, symlink/path escape, renames,
executable-mode changes and output/source destination guards.

## Comparison with a fresh rerun

On each introduced functional regression, a fresh full-suite rerun failed.
A narrower check passed, and ClaimTrail rejected its receipt for the configured
full-suite policy. The verifier records policy identity, file changes and check
results. The developer chooses which command and files are sufficient.

## Reproduce

Replay the included captures with the Python standard library:

```bash
python3 -S -B -m unittest discover -s tests -v
python3 -B src/verification_report.py examples/verification/recorded/report.json
python3 -B src/review_app.py --verification-report examples/verification/recorded/report.json --port 8768
```

To create new real repository captures, install the recorded test dependencies in
an isolated environment and choose **new** output directories:

```bash
uv venv .tools/verification-venv --python python3
uv pip install --python .tools/verification-venv/bin/python -r examples/verification/environment.txt
python3 -B scripts/run_scope_examples.py --output data/scope-eval/new-run --python .tools/verification-venv/bin/python
```

The runner clones/verifies the exact upstream revisions and refuses to reset a
dirty or mismatched existing clone.

Timings and upstream test counts can vary with Python and platform.
