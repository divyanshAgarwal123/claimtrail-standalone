"""Recreate the two local timing comparisons from frozen public patches."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from shutil import which
import statistics
import subprocess
import sys
import time

BENCHMARKS = Path(__file__).resolve().parent
ROOT = BENCHMARKS.parent
CASES = json.loads((BENCHMARKS / "cases.json").read_text())


def run(argv, *, cwd):
    subprocess.run(argv, cwd=cwd, check=True)


def timed(argv, *, cwd, env, timeout):
    start = time.monotonic()
    process = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                             text=True, timeout=timeout)
    return process, time.monotonic() - start


def benchmark(name, output, python_version, repetitions, tool):
    case = CASES[name]
    directory = output / name
    directory.mkdir()
    checkout = directory / "repo"
    run(["git", "clone", "--quiet", "--depth", "1", "--branch", case["tag"],
         case["repository"], str(checkout)], cwd=directory)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    if revision != case["revision"]:
        raise ValueError(f"{name} resolved to {revision}, expected {case['revision']}")
    venv = directory / "venv"
    run(["uv", "venv", "--python", python_version, str(venv)], cwd=directory)
    python = venv / "bin/python"
    run(["uv", "pip", "sync", "--python", str(python),
         str(BENCHMARKS / "requirements" / f"{name}.txt")], cwd=directory)
    run(["uv", "pip", "install", "--python", str(python), "--no-deps", "-e", str(checkout)], cwd=directory)
    # Editable installs must see the clean tag for tools that derive a version from Git.
    version = subprocess.check_output(
        [str(python), "-B", "-c", "from importlib.metadata import version; import sys; print(version(sys.argv[1]))", name],
        cwd=directory, text=True).strip()
    if version != case["tag"]:
        raise ValueError(f"{name} installed as {version}, expected {case['tag']}")
    run(["git", "apply", str(BENCHMARKS / "patches" / f"{name}.patch")], cwd=checkout)

    env = {**os.environ, "CLAIMTRAIL_ALLOWED_ROOT": str(checkout), "PWD": str(checkout)}
    policy_env = {
        "PATH": env["PATH"], "PYTHONPATH": str(checkout) if name == "django" else "",
        "VIRTUAL_ENV": "", "NODE_OPTIONS": "", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "TZ": "UTC",
    }
    if name == "pytest":
        policy_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    policy = {
        "check_id": f"{name}.reproduction", "command": [str(python), *case["test_argv"]],
        "scope": case["scope"], "exclude": case["exclude"], "env": policy_env,
        "timeout_seconds": case["timeout_seconds"],
    }
    policy_file = checkout / ".benchmark-policy.json"
    policy_file.write_text(json.dumps(policy, indent=2) + "\n")
    for action in ("check", "handoff"):
        process, elapsed = timed([sys.executable, "-B", str(tool), action, "--policy", str(policy_file)],
                                 cwd=checkout, env=env, timeout=case["timeout_seconds"] + 30)
        (directory / f"{action}.json").write_text(process.stdout)
        (directory / f"{action}.log").write_text(process.stderr)
        process.check_returncode()
        record = json.loads(process.stdout)
        if action == "check":
            capture_overhead = max(0, elapsed - record["execution_seconds"])
        else:
            if record["action"] != "reused_receipt":
                raise ValueError(f"{name} did not reuse its captured receipt: {record['action']}")
            verify_seconds = elapsed

    durations = []
    for attempt in range(1, repetitions + 1):
        process, elapsed = timed(policy["command"], cwd=checkout,
                                 env={**env, **policy_env, "PYTHONDONTWRITEBYTECODE": "1"},
                                 timeout=case["timeout_seconds"] + 10)
        (directory / f"native-{attempt}.log").write_text(process.stdout + process.stderr)
        process.check_returncode()
        durations.append(elapsed)
    baseline = statistics.median(durations)
    return {"case": name, "revision": revision, "package_version": version,
            "native_seconds": durations, "native_median_seconds": baseline,
            "capture_overhead_seconds": capture_overhead, "handoff_seconds": verify_seconds,
            "estimated_savings_seconds": baseline - capture_overhead - verify_seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(CASES) + ("all",), default="all")
    parser.add_argument("--output", type=Path, required=True, help="new directory for checkouts and logs")
    parser.add_argument("--python", default="3.13.17", help="Python version for uv to provision")
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 1 or not all(which(tool) for tool in ("git", "uv")):
        parser.error("supply a positive repetition count and install git and uv")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    run([sys.executable, "-B", str(ROOT / "scripts/build_handoff.py")], cwd=ROOT)
    tool = ROOT / "dist/claimtrail-handoff.pyz"
    chosen = list(CASES) if args.case == "all" else [args.case]
    results = []
    for name in chosen:
        result = benchmark(name, output, args.python, args.repetitions, tool)
        results.append(result)
        (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(f"{name}: fresh suite {result['native_median_seconds']:.2f}s, "
              f"estimated reuse saving {result['estimated_savings_seconds']:.2f}s", flush=True)


if __name__ == "__main__":
    main()
