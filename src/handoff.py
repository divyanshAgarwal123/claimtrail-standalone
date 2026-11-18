"""Run a host-configured check and gate coding-agent handoffs on its receipt."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import platform
import re
import shlex
import shutil
import sys
import time
from pathlib import Path

from cli_paths import allowed_path
from scope_verification import digest, observe, policy, run_check, seal, verify, write_json

STATE_DIR = ".claimtrail"
HOOK_NAME = "ClaimTrail handoff"
VERSION = "0.1"
RUNTIME_ENV = ("PATH", "PYTHONPATH", "VIRTUAL_ENV", "NODE_OPTIONS", "LANG", "LC_ALL", "TZ")


def invocation(action: str, repo: Path, path: Path, pin: str) -> str:
    return shlex.join([sys.executable, "-B", str(Path(sys.argv[0]).resolve()), action,
                       "--repo", str(repo), "--policy", str(path), "--policy-sha256", pin])


def check_configuration(path: Path) -> dict:
    spec = policy(json.loads(path.read_text()))
    for root in spec["scope"]:
        if root.startswith(STATE_DIR + "/") or root == STATE_DIR:
            raise ValueError("keep ClaimTrail state outside the check scope")
    if "." in spec["scope"] and not any(fnmatch.fnmatchcase(STATE_DIR, p) for p in spec["exclude"]):
        raise ValueError(f"exclude {STATE_DIR} when the declared scope includes the whole repository")
    return spec


def local_directory(repo: Path, name: str) -> Path:
    path = repo / name
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f"{path} must be a local directory")
    return path


def local_file(directory: Path, name: str) -> Path:
    path = directory / name
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"{path} must be a regular local file")
    return path


def install_codex(repo: Path, path: Path, spec: dict) -> dict:
    if os.name != "posix":
        raise ValueError("the Codex adapter currently requires macOS or Linux")
    directory = local_directory(repo, ".codex")
    destination = local_file(directory, "hooks.json")
    config = json.loads(destination.read_text()) if destination.exists() else {"hooks": {}}
    if not isinstance(config, dict) or not isinstance(config.setdefault("hooks", {}), dict):
        raise ValueError("expected a Codex hooks object")
    pin = digest(spec)
    for event, action, timeout in (
        ("SessionStart", "codex-start", 10),
        ("Stop", "codex-stop", int(spec["timeout_seconds"]) + 60),
    ):
        groups = config["hooks"].setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"expected a hook group list for {event}")
        retained = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError(f"invalid hook group for {event}")
            handlers = [handler for handler in group["hooks"]
                        if not (isinstance(handler, dict) and handler.get("statusMessage") == HOOK_NAME
                                and isinstance(handler.get("command"), str)
                                and re.search(r"\bcodex-(?:start|stop)\b.*--policy-sha256 ",
                                              handler["command"]))]
            if handlers:
                retained.append({**group, "hooks": handlers})
        retained.append({"hooks": [{"type": "command", "command": invocation(action, repo, path, pin),
                                    "timeout": timeout, "statusMessage": HOOK_NAME}]})
        config["hooks"][event] = retained
    write_json(destination, config)
    return {"hooks": str(destination), "policy_sha256": pin,
            "next": "Review and trust the installed ClaimTrail hooks in Codex."}


def runtime_fingerprint(repo: Path, spec: dict) -> str:
    env = {**os.environ, **spec["env"]}
    executable = spec["command"][0]
    if "/" in executable:
        resolved = repo / executable
    else:
        search = os.pathsep.join(str(repo / part) for part in os.get_exec_path(env))
        found = shutil.which(executable, path=search)
        resolved = Path(found) if found else None
    identity = None
    if resolved is not None and resolved.is_file():
        file = resolved.resolve(strict=True)
        stat = file.stat()
        identity = [str(file), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    return digest({"os": sys.platform, "arch": platform.machine(), "executable": identity,
                   "environment": {key: env.get(key) for key in RUNTIME_ENV}})


def run_gate(repo: Path, spec: dict, capture: bool, event: dict) -> tuple[dict, dict | None]:
    import fcntl

    started = time.monotonic()
    directory = local_directory(repo, STATE_DIR)
    directory.mkdir(mode=0o700, exist_ok=True)
    lock_path = local_file(directory, "gate.lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"ready": False, "action": "held", "result": {"status": "busy",
                    "reason": "Another ClaimTrail check is running in this workspace."}}, None

        receipt_file = local_file(directory, "receipt.json")
        output_file = local_file(directory, "handoff.json")
        runtime = runtime_fingerprint(repo, spec)
        receipt = None
        initial = {"status": "capture_requested", "reason": "The configured check was requested."}
        if not capture:
            try:
                receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else None
                initial = verify(spec, receipt, observe(repo, spec, receipt))
                if initial["status"] == "verified" and receipt.get("handoff_runtime_sha256") != runtime:
                    initial = {**initial, "status": "runtime_mismatch",
                               "reason": "The check runtime fingerprint differs from the saved receipt."}
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                initial = {"status": "invalid", "reason": str(exc)}

        result = initial
        action = "reused_receipt" if initial["status"] == "verified" else "held"
        execution = None
        if capture or initial["status"] in {"missing", "stale", "runtime_mismatch",
                                            "scope_mismatch", "workspace_mismatch"}:
            action = "ran_configured_check"
            receipt = run_check(repo, spec)
            stable_runtime = runtime == runtime_fingerprint(repo, spec)
            receipt = seal({**receipt, "handoff_runtime_sha256": runtime if stable_runtime else None})
            write_json(receipt_file, receipt)
            execution = receipt["execution"]
            result = verify(spec, receipt, observe(repo, spec, receipt))
            if result["status"] == "verified" and not stable_runtime:
                result = {**result, "status": "runtime_changed",
                          "reason": "The check runtime fingerprint changed during capture."}

        if execution and execution["launch_error"]:
            result = {**result, "status": "launch_error", "reason": execution["launch_error"]}
        record = {
            "schema": "claimtrail.handoff.v1", "ready": result["status"] == "verified",
            "action": action, "trigger": event.get("hook_event_name") or ("check" if capture else "handoff"),
            "session_id": event.get("session_id"), "turn_id": event.get("turn_id"),
            "initial": initial, "result": result,
            "receipt_sha256": receipt.get("sha256") if isinstance(receipt, dict) else None,
            "execution_seconds": execution["duration_seconds"] if execution else None,
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
        if capture:
            write_json(local_file(directory, "last-check.json"), record)
        else:
            write_json(output_file, record)
        return record, execution


def hook_event(action: str, repo: Path) -> dict | None:
    event = json.load(sys.stdin)
    expected = "Stop" if action == "codex-stop" else "SessionStart"
    if not isinstance(event, dict) or event.get("hook_event_name") != expected:
        raise ValueError(f"expected a {expected} hook event")
    cwd = Path(event["cwd"]).resolve(strict=True)
    if not cwd.is_relative_to(repo) or event.get("permission_mode") == "plan":
        return None
    return event


def hook_response(record: dict, event: dict) -> dict:
    if record["ready"]:
        return {}
    result = record["result"]
    message = (f"ClaimTrail handoff held ({result['status']}). {result['reason']} "
               f"See {STATE_DIR}/handoff.json if a result was written.")
    response = {"systemMessage": message}
    if not event.get("stop_hook_active"):
        response.update(decision="block", reason=(
            "ClaimTrail has held this handoff. Report the verification status to the user. "
            "Do not claim checks passed. Do not rerun or change files just to clear the hook. "
            f"Status: {result['status']}."))
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"ClaimTrail {VERSION}")
    parser.add_argument("action", choices=("check", "handoff", "install-codex", "codex-start", "codex-stop"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", help=argparse.SUPPRESS)
    args = parser.parse_args()
    is_hook = args.action in {"codex-start", "codex-stop"}
    event = {}
    try:
        if os.name != "posix":
            raise ValueError("the handoff workflow currently requires macOS or Linux")
        # The installed command binds the root, policy and digest. Hook input cannot select them.
        repo = args.repo.resolve(strict=True) if is_hook else allowed_path(args.repo)
        path = allowed_path(args.policy, root=repo)
        if is_hook:
            event = hook_event(args.action, repo)
            if event is None:
                print("{}")
                return 0
        spec = check_configuration(path)
        if args.policy_sha256 is not None and digest(spec) != args.policy_sha256:
            raise ValueError("the selected policy changed; review it and reinstall the hooks")
        if is_hook and not args.policy_sha256:
            raise ValueError("the installed hook must pin the check policy")
        if args.action == "install-codex":
            print(json.dumps(install_codex(repo, path, spec)))
            return 0
        if args.action == "codex-start":
            command = invocation("check", repo, path, digest(spec))
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "ClaimTrail will verify the host-selected check at task completion. "
                f"For the configured full check, run: {command}\n"
                "This approved command writes local receipts under .claimtrail/. "
                "Targeted tests may run separately. Use the configured check to capture reusable evidence.",
            }}))
            return 0

        record, execution = run_gate(repo, spec, args.action == "check", event)
        if is_hook:
            print(json.dumps(hook_response(record, event)))
            return 0
        if args.action == "check" and execution:
            for stream in ("stdout", "stderr"):
                print(execution[stream]["excerpt"], file=sys.stderr, end="")
        print(json.dumps(record))
        return 0 if record["ready"] else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        if is_hook:
            message = f"ClaimTrail hook could not verify this handoff: {exc}"
            print(json.dumps({"systemMessage": message}))
            return 0
        print(json.dumps({"ready": False, "result": {"status": "invalid", "reason": str(exc)}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
