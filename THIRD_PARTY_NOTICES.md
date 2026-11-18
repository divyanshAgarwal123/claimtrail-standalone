# Third-party material and data

ClaimTrail's original code and documentation are MIT licensed. This does not
relicense third-party code or datasets.

- **More Itertools**, revision `ceafee8ce96f4bc1eb74c528bc247c91d648a0bb`,
  https://github.com/more-itertools/more-itertools, MIT. Its source stays in ignored
  local clones. Recorded test output, file hashes and a reproduction runner are
  distributed; the upstream license is preserved in `docs/licenses/more-itertools.txt`.
- **ItsDangerous**, revision `672971d66a2ef9f85151e53283113f33d642dabd`,
  https://github.com/pallets/itsdangerous, BSD-3-Clause. Its source stays in ignored
  local clones. Recorded test output, file hashes and a reproduction runner are
  distributed; the upstream license is preserved in `docs/licenses/itsdangerous.txt`.
- **pytest**, tag `8.4.2`, https://github.com/pytest-dev/pytest, MIT. The
  benchmark distributes a patch against upstream source. See
  `docs/licenses/pytest.txt` for its license.
- **Django**, tag `5.2.1`, https://github.com/django/django, BSD-3-Clause. The
  benchmark distributes a patch against upstream source. See
  `docs/licenses/django.txt` for its license.
- **AI Digest's AI Village dataset** remains governed by its own
  [dataset card and terms](https://huggingface.co/datasets/aidigestorg/ai-village).
  Raw/derived dataset records and annotations are excluded from this delivery.
  The v0.1 handoff benchmarks use public software repositories.

The runtime packages used for local repository testing are not bundled or
relicensed. See the recorded environment and reproduction instructions for their
versions. No credentials, model weights or native tool binaries are distributed.
